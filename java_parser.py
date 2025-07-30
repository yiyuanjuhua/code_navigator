import os
import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

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

@dataclass
class ClassInfo:
    """Class information structure"""
    name: str
    file_path: str
    package: str
    functions: List[FunctionInfo]
    imports: List[str]

class JavaParser:
    """Java code parser for extracting function call relationships"""
    
    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.src_path: str = ""
        
    def parse_project(self, project_path: str) -> Dict[str, FunctionInfo]:
        """Parse entire Java project and extract function information"""
        self.src_path = os.path.join(project_path, "src")
        
        if not os.path.exists(self.src_path):
            raise ValueError(f"Source directory not found: {self.src_path}")
            
        logger.info(f"Parsing Java project at: {project_path}")
        
        # Find all Java files in src directory
        java_files = self._find_java_files(self.src_path)
        logger.info(f"Found {len(java_files)} Java files")
        
        # Parse each Java file
        for java_file in java_files:
            self._parse_java_file(java_file)
            
        # Resolve function calls after all files are parsed
        self._resolve_function_calls()
        
        return self.functions
    
    def _find_java_files(self, directory: str) -> List[str]:
        """Find all Java files in directory recursively"""
        java_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        return java_files
    
    def _parse_java_file(self, file_path: str) -> None:
        """Parse a single Java file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Parsing file: {file_path}")
            
            # Extract package and imports
            package = self._extract_package(content)
            imports = self._extract_imports(content)
            
            # Extract class information
            class_info = self._extract_class_info(content, file_path, package, imports)
            
            if class_info:
                self.classes[class_info.name] = class_info
                
                # Add functions to global function map
                for func in class_info.functions:
                    func_key = f"{class_info.name}.{func.name}"
                    self.functions[func_key] = func
                    
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
    
    def _extract_package(self, content: str) -> str:
        """Extract package declaration from Java content"""
        package_match = re.search(r'package\s+([\w.]+)\s*;', content)
        return package_match.group(1) if package_match else ""
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Java content"""
        import_pattern = r'import\s+([\w.*]+)\s*;'
        imports = re.findall(import_pattern, content)
        return imports
    
    def _extract_class_info(self, content: str, file_path: str, package: str, imports: List[str]) -> Optional[ClassInfo]:
        """Extract class information and its methods"""
        # Find class declaration
        class_pattern = r'(?:public\s+)?(?:final\s+)?class\s+(\w+)'
        class_match = re.search(class_pattern, content)
        
        if not class_match:
            return None
            
        class_name = class_match.group(1)
        
        # Extract functions from class
        functions = self._extract_functions(content, class_name, file_path)
        
        return ClassInfo(
            name=class_name,
            file_path=file_path,
            package=package,
            functions=functions,
            imports=imports
        )
    
    def _extract_functions(self, content: str, class_name: str, file_path: str) -> List[FunctionInfo]:
        """Extract function information from class content"""
        functions = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for method declaration
            if self._is_method_declaration(line):
                func_info = self._parse_method(lines, i, class_name, file_path)
                if func_info:
                    functions.append(func_info)
                    # Move to the line after this method ends
                    i = func_info.end_line
                else:
                    i += 1
            else:
                i += 1
                
        return functions
    
    def _is_method_declaration(self, line: str) -> bool:
        """Check if line contains a method declaration"""
        stripped = line.strip()
        
        # Skip class-level annotations
        class_annotations = ['@RestController', '@RequestMapping', '@Service', 
                           '@Repository', '@Component', '@Controller', '@Autowired']
        for annotation in class_annotations:
            if stripped.startswith(annotation):
                return False
        
        # Check for method-level annotations (like @GetMapping, @PostMapping, etc.)
        if stripped.startswith('@'):
            return True
            
        # Check for method declaration patterns  
        method_patterns = [
            r'(public|private|protected)\s+.*?\w+\s*\(',  # public/private/protected methods
            r'static\s+.*?\w+\s*\(',  # static methods
        ]
        
        for pattern in method_patterns:
            if re.search(pattern, stripped):
                # Make sure it's not a class declaration
                if 'class' not in stripped:
                    return True
        return False
    
    def _parse_method(self, lines: List[str], start_idx: int, class_name: str, file_path: str) -> Optional[FunctionInfo]:
        """Parse method details starting from given line index"""
        method_lines = []
        i = start_idx
        
        # Find the method signature line by collecting annotations and method declaration
        method_signature_start = i
        
        # Collect annotations first
        while i < len(lines) and lines[i].strip().startswith('@'):
            method_lines.append(lines[i])
            i += 1
        
        # Look for the actual method declaration line
        if i >= len(lines):
            return None
            
        # The current line should be the method signature
        signature_line = lines[i]
        method_lines.append(signature_line)
        
        # Find opening brace (could be on same line or next line)
        brace_count = 0
        found_opening_brace = False
        
        # Check if opening brace is on the signature line
        if '{' in signature_line:
            brace_count = signature_line.count('{') - signature_line.count('}')
            found_opening_brace = True
            i += 1
        else:
            # Look for opening brace on next lines
            i += 1
            while i < len(lines) and not found_opening_brace:
                line = lines[i]
                method_lines.append(line)
                if '{' in line:
                    brace_count = line.count('{') - line.count('}')
                    found_opening_brace = True
                    i += 1
                    break
                i += 1
        
        if not found_opening_brace:
            return None
            
        # Now collect method body until braces balance
        while i < len(lines) and brace_count > 0:
            line = lines[i]
            method_lines.append(line)
            
            # Count braces in this line
            brace_count += line.count('{') - line.count('}')
            i += 1
        
        if not method_lines:
            return None
            
        method_content = '\n'.join(method_lines)
        
        # Extract method name
        method_name = self._extract_method_name(method_content)
        if not method_name:
            return None
            
        # Skip constructor methods (same name as class)
        if method_name == class_name:
            return None
            
        # Check if it's a REST endpoint
        is_rest_endpoint, endpoint_path, http_method = self._check_rest_endpoint(method_content)
        
        # Extract function calls within this method
        called_functions = self._extract_function_calls(method_content)
        
        # Check if method is public
        is_public = 'public' in method_content
        
        return FunctionInfo(
            name=method_name,
            class_name=class_name,
            file_path=file_path,
            start_line=start_idx + 1,  # 1-based line numbers
            end_line=i,  # i is already the line after the method
            called_functions=called_functions,
            is_public=is_public,
            is_rest_endpoint=is_rest_endpoint,
            endpoint_path=endpoint_path,
            http_method=http_method
        )
    
    def _extract_method_name(self, method_content: str) -> Optional[str]:
        """Extract method name from method content"""
        # Pattern to match method declaration
        patterns = [
            r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(',
            r'(\w+)\s*\(',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, method_content)
            if match:
                method_name = match.group(1)
                # Skip constructors and common keywords
                if method_name not in ['if', 'while', 'for', 'switch', 'catch']:
                    return method_name
        
        return None
    
    def _check_rest_endpoint(self, method_content: str) -> Tuple[bool, str, str]:
        """Check if method is a REST endpoint and extract mapping info"""
        mapping_patterns = {
            'GET': r'@GetMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'POST': r'@PostMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'PUT': r'@PutMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'DELETE': r'@DeleteMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'REQUEST': r'@RequestMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)'
        }
        
        for http_method, pattern in mapping_patterns.items():
            match = re.search(pattern, method_content)
            if match:
                path = match.group(1) if match.group(1) else ""
                return True, path, http_method
                
        return False, "", ""
    
    def _extract_function_calls(self, method_content: str) -> List[str]:
        """Extract function calls from method content"""
        calls = []
        
        # Remove annotations and comments
        cleaned_content = re.sub(r'@\w+.*?\n', '', method_content)
        cleaned_content = re.sub(r'//.*?\n', '', cleaned_content)
        cleaned_content = re.sub(r'/\*.*?\*/', '', cleaned_content, flags=re.DOTALL)
        
        # Pattern to match method calls (more precise)
        call_patterns = [
            r'(\w+)\.(\w+)\s*\(',  # object.method()
        ]
        
        for pattern in call_patterns:
            matches = re.findall(pattern, cleaned_content)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    obj_name, method_name = match
                    # Skip common Java keywords and operators
                    if obj_name not in ['if', 'while', 'for', 'switch', 'return', 'new', 'this', 'super']:
                        calls.append(f"{obj_name}.{method_name}")
        
        # Filter out common keywords and control structures
        filtered_calls = []
        keywords_to_skip = {
            'if', 'while', 'for', 'switch', 'try', 'catch', 'finally',
            'return', 'throw', 'new', 'this', 'super', 'class', 'import',
            'package', 'public', 'private', 'protected', 'static', 'final',
            'void', 'String', 'Long', 'Integer', 'Boolean', 'get', 'set'
        }
        
        for call in calls:
            obj_name, method_name = call.split('.', 1)
            if (method_name not in keywords_to_skip and 
                obj_name not in keywords_to_skip and 
                len(method_name) > 1 and
                not method_name.startswith('get') and
                not method_name.startswith('set')):
                filtered_calls.append(call)
                
        return list(set(filtered_calls))  # Remove duplicates
    
    def _resolve_function_calls(self) -> None:
        """Resolve function calls to actual function references"""
        for func_key, func_info in self.functions.items():
            resolved_calls = []
            
            for call in func_info.called_functions:
                # Try to resolve the call to an actual function
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
            
            # Look for field type in class and try to resolve
            for class_name, class_info in self.classes.items():
                potential_key = f"{class_name}.{method_name}"
                if potential_key in self.functions:
                    return potential_key
        
        # Direct method name lookup across all classes
        for func_key in self.functions.keys():
            if func_key.endswith(f".{call}"):
                return func_key
                
        return None