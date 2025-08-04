import os
import re
import json
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import javalang

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FunctionInfo:
    """Function information structure"""
    name: str
    class_name: str
    file_path: str
    start_line: int
    end_line: int
    called_functions: List[str]
    is_public: bool = False
    is_rest_endpoint: bool = False
    endpoint_path: str = ""
    http_method: str = ""
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

@dataclass
class ClassLinkInfo:
    """Class link information structure for chain analysis"""
    name: str  # Empty for class level info
    class_name: str
    file_path: str
    start_line: int
    end_line: int
    called_functions: List[str]  # Classes used by this class
    is_public: bool = False
    is_rest_endpoint: bool = False
    endpoint_path: str = ""
    http_method: str = ""
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

@dataclass
class ClassInfo:
    """Class information structure"""
    name: str
    file_path: str
    package: str
    functions: List[FunctionInfo]
    imports: List[str]

class JavaParser:
    """Java code parser using javalang for extracting function call relationships"""
    
    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.class_links: Dict[str, ClassLinkInfo] = {}  # 新增：类链路信息
        self.src_main_path: str = ""
        self.package_to_file_map: Dict[str, str] = {}
        
    def parse_project(self, project_path: str) -> Dict[str, FunctionInfo]:
        """Parse entire Java project and extract function information"""
        # Focus on src/main directory as requested
        self.src_main_path = os.path.join(project_path, "src", "main", "java")
        
        if not os.path.exists(self.src_main_path):
            # Fallback to src directory if src/main/java doesn't exist
            self.src_main_path = os.path.join(project_path, "src")
            if not os.path.exists(self.src_main_path):
                raise ValueError(f"Source directory not found: {self.src_main_path}")
            
        logger.info(f"Parsing Java project at: {project_path}")
        logger.info(f"Using source directory: {self.src_main_path}")
        
        # Find all Java files in src/main directory, excluding test/resource directories
        java_files = self._find_java_files(self.src_main_path)
        logger.info(f"Found {len(java_files)} Java files")
        
        # Parse each Java file using javalang
        for java_file in java_files:
            self._parse_java_file_with_javalang(java_file)
            
        # Resolve function calls after all files are parsed
        self._resolve_function_calls()
        
        return self.functions

    def get_class_links(self) -> Dict[str, ClassLinkInfo]:
        """Return all class link information"""
        return self.class_links

    def get_class_links_as_json(self) -> str:
        """Return all class link information as JSON string"""
        class_links_data = {}
        for class_key, class_link_info in self.class_links.items():
            class_links_data[class_key] = class_link_info.to_dict()
        
        return json.dumps(class_links_data, indent=2, ensure_ascii=False)
    
    def _find_java_files(self, directory: str) -> List[str]:
        """Find all Java files in directory recursively, excluding test and resource directories"""
        java_files = []
        exclude_dirs = {'test', 'tests', 'resources', 'resource', 'target', 'build'}
        
        for root, dirs, files in os.walk(directory):
            # Remove excluded directories from traversal
            dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs]
            
            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        return java_files
    
    def _parse_java_file_with_javalang(self, file_path: str) -> None:
        """Parse a single Java file using javalang"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Parsing file: {file_path}")
            
            # Parse using javalang
            try:
                tree = javalang.parse.parse(content)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path} with javalang: {e}")
                return
            
            # Extract package information
            package = tree.package.name if tree.package else ""
            
            # Extract imports
            imports = []
            if tree.imports:
                for import_decl in tree.imports:
                    imports.append(import_decl.path)
            
            # Process each class/interface declaration
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                self._process_class_declaration(node, file_path, package, imports, content)
                
            for path, node in tree.filter(javalang.tree.InterfaceDeclaration):
                self._process_class_declaration(node, file_path, package, imports, content)
                    
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
    
    def _process_class_declaration(self, class_node, file_path: str, package: str, imports: List[str], content: str) -> None:
        """Process a class declaration and extract its methods"""
        class_name = class_node.name
        full_class_name = f"{package}.{class_name}" if package else class_name
        
        # Store package to file mapping
        self.package_to_file_map[full_class_name] = file_path
        
        # Extract class position
        class_start_line = class_node.position.line if class_node.position else 1
        class_end_line = self._find_class_end_line(content, class_start_line)
        
        # Check if class is public
        is_public = any(modifier == 'public' for modifier in class_node.modifiers) if class_node.modifiers else False
        
        # Extract methods from the class
        functions = []
        
        # Get class-level annotations for REST controllers
        class_annotations = self._extract_annotations(class_node.annotations) if class_node.annotations else {}
        class_rest_mapping = class_annotations.get('RequestMapping', '') or class_annotations.get('Path', '')
        
        # Check if class is a REST controller
        is_rest_endpoint = bool(class_rest_mapping) or any(
            annotation in ['RestController', 'Controller', 'Path'] 
            for annotation in class_annotations.keys()
        )
        
        for method_node in class_node.body:
            if isinstance(method_node, javalang.tree.MethodDeclaration):
                func_info = self._process_method_declaration(method_node, class_name, file_path, content, class_rest_mapping)
                if func_info:
                    functions.append(func_info)
        
        # Extract class dependencies (other classes used by this class)
        class_dependencies = self._extract_class_dependencies(class_node, imports)
        
        # Create class info
        class_info = ClassInfo(
            name=class_name,
            file_path=file_path,
            package=package,
            functions=functions,
            imports=imports
        )
        
        self.classes[class_name] = class_info
        
        # Create class link info for chain analysis
        class_link_info = ClassLinkInfo(
            name="",  # Empty as requested for class level info
            class_name=class_name,
            file_path=file_path,
            start_line=class_start_line,
            end_line=class_end_line,
            called_functions=class_dependencies,
            is_public=is_public,
            is_rest_endpoint=is_rest_endpoint,
            endpoint_path=class_rest_mapping,
            http_method="REQUEST" if is_rest_endpoint else ""
        )
        
        self.class_links[class_name] = class_link_info
        
        # Add functions to global function map with deduplication
        for func in functions:
            func_key = f"{class_name}.{func.name}"
            # Check for duplicates (same name, file_path, start_line, end_line)
            if func_key in self.functions:
                existing_func = self.functions[func_key]
                if (existing_func.file_path == func.file_path and 
                    existing_func.start_line == func.start_line and 
                    existing_func.end_line == func.end_line):
                    logger.warning(f"Skipping duplicate function: {func_key} in {func.file_path}:{func.start_line}-{func.end_line}")
                    continue
                else:
                    # Different implementation, use a unique key
                    counter = 1
                    unique_key = f"{func_key}_{counter}"
                    while unique_key in self.functions:
                        counter += 1
                        unique_key = f"{func_key}_{counter}"
                    func_key = unique_key
                    logger.info(f"Found function with same name but different location, using unique key: {func_key}")
            
            self.functions[func_key] = func
    
    def _process_method_declaration(self, method_node, class_name: str, file_path: str, content: str, class_rest_mapping: str = "") -> Optional[FunctionInfo]:
        """Process a method declaration and extract its information"""
        method_name = method_node.name
        
        # Skip constructors
        if method_name == class_name:
            return None
        
        # Get method position
        start_line = method_node.position.line if method_node.position else 1
        end_line = self._find_method_end_line(content, start_line)
        
        # Check if method is public
        is_public = any(modifier == 'public' for modifier in method_node.modifiers) if method_node.modifiers else False
        
        # Extract method annotations for REST endpoints
        method_annotations = self._extract_annotations(method_node.annotations) if method_node.annotations else {}
        
        # Check for REST endpoint annotations (Spring Boot and JAX-RS)
        is_rest_endpoint, endpoint_path, http_method = self._check_rest_endpoint_annotations(method_annotations, class_rest_mapping)
        
        # Extract function calls within this method
        called_functions = self._extract_function_calls_from_method(method_node)
        
        return FunctionInfo(
            name=method_name,
            class_name=class_name,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            called_functions=called_functions,
            is_public=is_public,
            is_rest_endpoint=is_rest_endpoint,
            endpoint_path=endpoint_path,
            http_method=http_method
        )
    
    def _extract_annotations(self, annotations) -> Dict[str, str]:
        """Extract annotations from javalang annotation nodes"""
        annotation_dict = {}
        if not annotations:
            return annotation_dict
            
        for annotation in annotations:
            annotation_name = annotation.name
            
            # Handle different annotation types
            if hasattr(annotation, 'element') and annotation.element:
                if isinstance(annotation.element, javalang.tree.Literal):
                    annotation_dict[annotation_name] = annotation.element.value.strip('"\'')
                elif hasattr(annotation.element, 'value'):
                    annotation_dict[annotation_name] = annotation.element.value
            else:
                annotation_dict[annotation_name] = ""
                
        return annotation_dict
    
    def _check_rest_endpoint_annotations(self, annotations: Dict[str, str], class_rest_mapping: str = "") -> Tuple[bool, str, str]:
        """Check if method has REST endpoint annotations (Spring Boot + JAX-RS)"""
        spring_boot_mappings = {
            'GetMapping': 'GET',
            'PostMapping': 'POST',
            'PutMapping': 'PUT',
            'DeleteMapping': 'DELETE',
            'PatchMapping': 'PATCH',
            'RequestMapping': 'REQUEST'
        }
        
        # JAX-RS annotations (including jakarta.ws.rs.Path)
        jaxrs_mappings = {
            'GET': 'GET',
            'POST': 'POST',
            'PUT': 'PUT',
            'DELETE': 'DELETE',
            'PATCH': 'PATCH'
        }
        
        endpoint_path = ""
        http_method = ""
        
        # Check Spring Boot annotations
        for annotation_name, method in spring_boot_mappings.items():
            if annotation_name in annotations:
                endpoint_path = annotations[annotation_name]
                http_method = method
                break
        
        # Check JAX-RS annotations
        if not http_method:
            for annotation_name, method in jaxrs_mappings.items():
                if annotation_name in annotations:
                    http_method = method
                    break
        
        # Check for @Path annotation (JAX-RS)
        if 'Path' in annotations:
            if not endpoint_path:
                endpoint_path = annotations['Path']
            if not http_method:
                http_method = 'REQUEST'  # Default for @Path
        
        # Combine class and method paths
        if class_rest_mapping and endpoint_path:
            endpoint_path = f"{class_rest_mapping.rstrip('/')}/{endpoint_path.lstrip('/')}"
        elif class_rest_mapping and not endpoint_path:
            endpoint_path = class_rest_mapping
        
        return bool(http_method), endpoint_path, http_method
    
    def _find_method_end_line(self, content: str, start_line: int) -> int:
        """Find the end line of a method by counting braces"""
        lines = content.split('\n')
        if start_line > len(lines):
            return start_line
        
        brace_count = 0
        found_opening_brace = False
        
        for i in range(start_line - 1, len(lines)):
            line = lines[i]
            
            # Count braces
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening_brace = True
                elif char == '}':
                    brace_count -= 1
                    
            # If we found opening brace and braces are balanced, we found the end
            if found_opening_brace and brace_count == 0:
                return i + 1
        
        return start_line + 10  # Fallback
    
    def _find_class_end_line(self, content: str, start_line: int) -> int:
        """Find the end line of a class by counting braces"""
        lines = content.split('\n')
        if start_line > len(lines):
            return start_line
        
        brace_count = 0
        found_opening_brace = False
        
        for i in range(start_line - 1, len(lines)):
            line = lines[i]
            
            # Count braces
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening_brace = True
                elif char == '}':
                    brace_count -= 1
                    
            # If we found opening brace and braces are balanced, we found the end
            if found_opening_brace and brace_count == 0:
                return i + 1
        
        return len(lines)  # End of file if not found
    
    def _extract_function_calls_from_method(self, method_node) -> List[str]:
        """Extract function calls from method node using javalang AST"""
        calls = []
        
        # Traverse the AST to find method invocations
        for path, node in method_node.filter(javalang.tree.MethodInvocation):
            if hasattr(node, 'member') and hasattr(node, 'qualifier'):
                if node.qualifier:
                    # Object method call: object.method()
                    qualifier_name = self._get_node_name(node.qualifier)
                    if qualifier_name and qualifier_name not in ['this', 'super']:
                        call = f"{qualifier_name}.{node.member}"
                        calls.append(call)
                else:
                    # Direct method call: method()
                    calls.append(node.member)
        
        # Remove duplicates and filter out common keywords
        filtered_calls = []
        keywords_to_skip = {
            'equals', 'toString', 'hashCode', 'clone', 'finalize',
            'getClass', 'notify', 'notifyAll', 'wait'
        }
        
        for call in set(calls):
            if '.' in call:
                obj_name, method_name = call.split('.', 1)
                if (method_name not in keywords_to_skip and 
                    len(method_name) > 1 and
                    not method_name.startswith('get') and
                    not method_name.startswith('set') and
                    not method_name.startswith('is')):
                    filtered_calls.append(call)
            elif call not in keywords_to_skip:
                filtered_calls.append(call)
                
        return filtered_calls
    
    def _get_node_name(self, node) -> Optional[str]:
        """Get the name from an AST node"""
        if hasattr(node, 'member'):
            return node.member
        elif hasattr(node, 'name'):
            return node.name
        elif isinstance(node, str):
            return node
        return None
    
    def _resolve_function_calls(self) -> None:
        """Resolve function calls to actual function references"""
        for func_key, func_info in self.functions.items():
            resolved_calls = []
            
            for call in func_info.called_functions:
                resolved_call = self._resolve_single_call(call, func_info)
                if resolved_call:
                    resolved_calls.append(resolved_call)
                    
            func_info.called_functions = resolved_calls
    
    def _resolve_single_call(self, call: str, calling_func: FunctionInfo) -> Optional[str]:
        """Resolve a single function call to actual function reference"""
        # Direct function call within same class
        same_class_key = f"{calling_func.class_name}.{call}"
        if same_class_key in self.functions:
            return same_class_key
            
        # Method call on field/variable (simplified resolution)
        if '.' in call:
            obj_name, method_name = call.split('.', 1)
            
            # Look for method in all classes
            for class_name, class_info in self.classes.items():
                potential_key = f"{class_name}.{method_name}"
                if potential_key in self.functions:
                    return potential_key
        
        # Direct method name lookup across all classes
        for func_key in self.functions.keys():
            if func_key.endswith(f".{call}"):
                return func_key
                
        return None
    
    def _extract_class_dependencies(self, class_node, imports: List[str]) -> List[str]:
        """Extract class dependencies from class node"""
        dependencies = set()
        
        # Extract from field declarations (instance variables)
        for field_node in class_node.body:
            if isinstance(field_node, javalang.tree.FieldDeclaration):
                if field_node.type:
                    class_type = self._extract_type_name(field_node.type)
                    if class_type and self._is_custom_class(class_type, imports):
                        dependencies.add(class_type)
        
        # Extract from method parameters and return types
        for method_node in class_node.body:
            if isinstance(method_node, javalang.tree.MethodDeclaration):
                # Method return type
                if method_node.return_type:
                    return_type = self._extract_type_name(method_node.return_type)
                    if return_type and self._is_custom_class(return_type, imports):
                        dependencies.add(return_type)
                
                # Method parameters
                if method_node.parameters:
                    for param in method_node.parameters:
                        param_type = self._extract_type_name(param.type)
                        if param_type and self._is_custom_class(param_type, imports):
                            dependencies.add(param_type)
        
        # Extract from extends and implements
        if hasattr(class_node, 'extends') and class_node.extends:
            extends_type = self._extract_type_name(class_node.extends)
            if extends_type and self._is_custom_class(extends_type, imports):
                dependencies.add(extends_type)
        
        if hasattr(class_node, 'implements') and class_node.implements:
            for impl in class_node.implements:
                impl_type = self._extract_type_name(impl)
                if impl_type and self._is_custom_class(impl_type, imports):
                    dependencies.add(impl_type)
        
        return list(dependencies)
    
    def _extract_type_name(self, type_node) -> Optional[str]:
        """Extract type name from type node"""
        if hasattr(type_node, 'name'):
            return type_node.name
        elif hasattr(type_node, 'element') and hasattr(type_node.element, 'name'):
            # For array types like String[]
            return type_node.element.name
        elif hasattr(type_node, 'arguments') and type_node.arguments:
            # For generic types like List<String>
            if hasattr(type_node, 'name'):
                return type_node.name
        elif isinstance(type_node, str):
            return type_node
        return None
    
    def _is_custom_class(self, class_name: str, imports: List[str]) -> bool:
        """Check if a class name represents a custom (non-built-in) class"""
        # Skip primitive types and common Java built-in types
        builtin_types = {
            'int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short',
            'String', 'Object', 'Integer', 'Long', 'Double', 'Float', 'Boolean',
            'Character', 'Byte', 'Short', 'List', 'Map', 'Set', 'Collection',
            'ArrayList', 'HashMap', 'HashSet', 'LinkedList', 'TreeMap', 'TreeSet',
            'Date', 'Calendar', 'UUID', 'BigDecimal', 'BigInteger'
        }
        
        if class_name in builtin_types:
            return False
        
        # If it's a single word and not in imports, likely a local class
        if '.' not in class_name:
            return True
        
        # If it's in imports, it's likely custom
        for import_path in imports:
            if import_path.endswith(f".{class_name}") or import_path.endswith(f".*"):
                return True
        
        return False
    
    def get_functions_as_json(self) -> str:
        """Return all functions information as JSON string"""
        functions_data = {}
        for func_key, func_info in self.functions.items():
            functions_data[func_key] = func_info.to_dict()
        
        return json.dumps(functions_data, indent=2, ensure_ascii=False)