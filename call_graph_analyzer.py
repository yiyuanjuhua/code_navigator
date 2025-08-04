from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from java_parser import FunctionInfo, JavaParser
import logging

logger = logging.getLogger(__name__)

@dataclass
class CallChain:
    """Function call chain information"""
    function: FunctionInfo
    children: List['CallChain']
    depth: int = 0

class CallGraphAnalyzer:
    """Analyze function call relationships and generate call graphs"""
    
    def __init__(self, functions: Dict[str, FunctionInfo]):
        self.functions = functions
        self.call_graph: Dict[str, List[str]] = {}
        self._build_call_graph()
    
    def _build_call_graph(self) -> None:
        """Build the call graph from function information"""
        for func_key, func_info in self.functions.items():
            self.call_graph[func_key] = func_info.called_functions.copy()
    
    def find_function_by_name(self, function_name: str) -> List[str]:
        """Find function keys that match the given function name"""
        matching_functions = []
        
        # Exact match first
        if function_name in self.functions:
            matching_functions.append(function_name)
        
        # Check for class.method format
        for func_key in self.functions.keys():
            if func_key.endswith(f".{function_name}"):
                matching_functions.append(func_key)
        
        # Check for REST endpoint path match
        for func_key, func_info in self.functions.items():
            if func_info.is_rest_endpoint and function_name in func_info.endpoint_path:
                matching_functions.append(func_key)
        
        return matching_functions
    
    def get_call_chain(self, function_key: str, max_depth: int = 10) -> Optional[CallChain]:
        """Get the complete call chain starting from the given function"""
        if function_key not in self.functions:
            return None
        
        visited = set()
        return self._build_call_chain(function_key, visited, 0, max_depth)
    
    def _build_call_chain(self, function_key: str, visited: Set[str], depth: int, max_depth: int) -> CallChain:
        """Recursively build call chain"""
        func_info = self.functions[function_key]
        chain = CallChain(function=func_info, children=[], depth=depth)
        
        if depth >= max_depth or function_key in visited:
            return chain
        
        visited.add(function_key)
        
        # Get called functions
        called_functions = self.call_graph.get(function_key, [])
        
        for called_func in called_functions:
            if called_func in self.functions:
                child_chain = self._build_call_chain(called_func, visited.copy(), depth + 1, max_depth)
                chain.children.append(child_chain)
        
        return chain
    
    def get_all_functions_in_chain(self, call_chain: CallChain) -> List[FunctionInfo]:
        """Get all functions in the call chain as a flat list"""
        # 使用字典来去重，以函数的唯一标识作为key
        unique_functions = {}
        self._collect_unique_functions(call_chain, unique_functions)
        return list(unique_functions.values())
    
    def _collect_unique_functions(self, call_chain: CallChain, unique_functions: Dict[str, FunctionInfo]) -> None:
        """递归收集唯一的函数，避免重复"""
        # 创建函数的唯一标识：类名.方法名@文件路径:起始行号
        func_key = f"{call_chain.function.class_name}.{call_chain.function.name}@{call_chain.function.file_path}:{call_chain.function.start_line}"
        
        # 如果还没有收集过这个函数，则添加
        if func_key not in unique_functions:
            unique_functions[func_key] = call_chain.function
        
        # 递归处理子调用链
        for child in call_chain.children:
            self._collect_unique_functions(child, unique_functions)

class MermaidGenerator:
    """Generate Mermaid diagrams for function call chains"""
    
    def __init__(self):
        self.node_counter = 0
        self.node_map: Dict[str, str] = {}
    
    def generate_mermaid_diagram(self, call_chain: CallChain) -> str:
        """Generate Mermaid flowchart diagram from call chain"""
        self.node_counter = 0
        self.node_map = {}
        
        mermaid_lines = ["graph TD"]
        
        # First pass: collect all nodes
        self._collect_all_nodes(call_chain)
        
        # Add node definitions
        for func_key, node_def in self.node_map.items():
            mermaid_lines.append(f"    {node_def}")
        
        # Second pass: generate edges
        self._generate_mermaid_edges(call_chain, mermaid_lines)
        
        return "\n".join(mermaid_lines)
    
    def _collect_all_nodes(self, chain: CallChain) -> None:
        """Collect all nodes in the call chain"""
        self._get_or_create_node(chain.function)
        
        for child in chain.children:
            self._collect_all_nodes(child)
    
    def _generate_mermaid_edges(self, chain: CallChain, mermaid_lines: List[str]) -> None:
        """Generate edges for the Mermaid diagram"""
        current_node_id = self._get_node_id(chain.function)
        
        for child in chain.children:
            child_node_id = self._get_node_id(child.function)
            mermaid_lines.append(f"    {current_node_id} --> {child_node_id}")
            
            # Recursively process children
            self._generate_mermaid_edges(child, mermaid_lines)
    
    def _get_node_id(self, func_info: FunctionInfo) -> str:
        """Get the node ID for a function"""
        func_key = f"{func_info.class_name}.{func_info.name}"
        if func_key in self.node_map:
            return self.node_map[func_key].split('[')[0]
        return "unknown"
    
    def _generate_mermaid_nodes(self, chain: CallChain, mermaid_lines: List[str]) -> str:
        """Generate Mermaid nodes and edges recursively"""
        # Create node for current function
        current_node = self._get_or_create_node(chain.function)
        
        # Create nodes for children and connect them
        for child in chain.children:
            child_node = self._get_or_create_node(child.function)
            
            # Add edge from current to child
            mermaid_lines.append(f"    {current_node} --> {child_node}")
            
            # Recursively process children
            self._generate_mermaid_nodes(child, mermaid_lines)
        
        return current_node
    
    def _get_or_create_node(self, func_info: FunctionInfo) -> str:
        """Get or create a Mermaid node for the function"""
        func_key = f"{func_info.class_name}.{func_info.name}"
        
        if func_key not in self.node_map:
            node_id = f"node{self.node_counter}"
            self.node_counter += 1
            
            # Create node label
            label = self._create_node_label(func_info)
            self.node_map[func_key] = f'{node_id}["{label}"]'
        
        return self.node_map[func_key].split('[')[0]  # Return just the node ID
    
    def _create_node_label(self, func_info: FunctionInfo) -> str:
        """Create a readable label for the function node"""
        label_parts = []
        
        # Add REST endpoint info if applicable
        if func_info.is_rest_endpoint:
            endpoint_info = f"{func_info.http_method} {func_info.endpoint_path}"
            label_parts.append(endpoint_info)
        
        # Add class and method name
        class_method = f"{func_info.class_name}.{func_info.name}"
        label_parts.append(class_method)
        
        # Add line numbers
        line_info = f"L{func_info.start_line}-{func_info.end_line}"
        label_parts.append(line_info)
        
        # Join label parts and clean up special characters for Mermaid
        label = "\\n".join(label_parts)
        # Remove any problematic character sequences that might appear in Mermaid output
        label = label.replace("\\nL", "\\n")
        return label

class ResultFormatter:
    """Format analysis results for output"""
    
    @staticmethod
    def format_function_info(functions: List[FunctionInfo]) -> str:
        """Format function information as readable text"""
        output_lines = []
        
        output_lines.append("=== Function Information ===")
        output_lines.append("")
        
        for i, func in enumerate(functions, 1):
            output_lines.append(f"{i}. {func.class_name}.{func.name}")
            
            if func.is_rest_endpoint:
                output_lines.append(f"   REST Endpoint: {func.http_method} {func.endpoint_path}")
            
            output_lines.append(f"   File: {func.file_path}")
            output_lines.append(f"   Lines: {func.start_line}-{func.end_line}")
            output_lines.append(f"   Public: {'Yes' if func.is_public else 'No'}")
            
            if func.called_functions:
                output_lines.append(f"   Calls: {', '.join(func.called_functions)}")
            else:
                output_lines.append("   Calls: None")
            
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    @staticmethod
    def format_call_chain_summary(call_chain: CallChain) -> str:
        """Format call chain summary"""
        analyzer = CallGraphAnalyzer({})
        all_functions = analyzer.get_all_functions_in_chain(call_chain)
        
        output_lines = []
        output_lines.append("=== Call Chain Summary ===")
        output_lines.append(f"Total functions in chain: {len(all_functions)}")
        output_lines.append(f"Starting function: {call_chain.function.class_name}.{call_chain.function.name}")
        
        if call_chain.function.is_rest_endpoint:
            output_lines.append(f"REST Endpoint: {call_chain.function.http_method} {call_chain.function.endpoint_path}")
        
        output_lines.append("")
        
        return "\n".join(output_lines)

class ClassAnalyzer:
    """分析类之间的关系和依赖"""
    
    def __init__(self, classes: Dict[str, 'ClassInfo']):
        from java_parser import ClassInfo
        self.classes = classes
        self.class_dependencies: Dict[str, List[str]] = {}
        self._build_class_dependencies()
    
    def _build_class_dependencies(self) -> None:
        """构建类之间的依赖关系"""
        for class_name, class_info in self.classes.items():
            dependencies = set()
            
            # 通过import语句获取依赖
            for import_stmt in class_info.imports:
                # 提取类名
                if '.' in import_stmt:
                    imported_class = import_stmt.split('.')[-1]
                    dependencies.add(imported_class)
            
            # 通过调用的函数获取依赖
            for called_func in class_info.called_functions:
                if '.' in called_func:
                    called_class = called_func.split('.')[0]
                    if called_class != class_name and called_class in self.classes:
                        dependencies.add(called_class)
            
            self.class_dependencies[class_name] = list(dependencies)
    
    def get_class_info_for_export(self, class_name: str) -> Dict:
        """获取用于导出的类信息，符合用户要求的格式"""
        if class_name not in self.classes:
            return None
        
        class_info = self.classes[class_name]
        
        return {
            "name": "",  # 保持为空，因为是class而非函数
            "class_name": class_info.class_name,
            "file_path": class_info.file_path,
            "start_line": class_info.start_line,
            "end_line": class_info.end_line,
            "is_public": class_info.is_public,
            "is_rest_endpoint": class_info.is_rest_endpoint,
            "endpoint_path": class_info.endpoint_path,
            "http_method": class_info.http_method,
            "called_functions": class_info.called_functions
        }
    
    def get_all_classes_for_export(self) -> List[Dict]:
        """获取所有类的导出格式信息"""
        result = []
        for class_name in self.classes.keys():
            class_data = self.get_class_info_for_export(class_name)
            if class_data:
                result.append(class_data)
        return result
    
    def find_rest_controllers(self) -> List[Dict]:
        """查找所有REST控制器类"""
        rest_controllers = []
        for class_name, class_info in self.classes.items():
            if class_info.is_rest_endpoint:
                rest_controllers.append(self.get_class_info_for_export(class_name))
        return rest_controllers
    
    def get_class_dependencies(self, class_name: str) -> List[str]:
        """获取指定类的依赖"""
        return self.class_dependencies.get(class_name, [])
    
    def format_class_summary(self) -> str:
        """格式化类信息摘要"""
        output_lines = []
        output_lines.append("=== 类信息摘要 ===")
        output_lines.append("")
        
        total_classes = len(self.classes)
        rest_controllers = len([c for c in self.classes.values() if c.is_rest_endpoint])
        public_classes = len([c for c in self.classes.values() if c.is_public])
        
        output_lines.append(f"总类数: {total_classes}")
        output_lines.append(f"REST控制器: {rest_controllers}")
        output_lines.append(f"公有类: {public_classes}")
        output_lines.append("")
        
        for i, (class_name, class_info) in enumerate(self.classes.items(), 1):
            output_lines.append(f"{i}. {class_info.class_name}")
            output_lines.append(f"   文件: {class_info.file_path}")
            output_lines.append(f"   行数: {class_info.start_line}-{class_info.end_line}")
            output_lines.append(f"   公有: {'是' if class_info.is_public else '否'}")
            
            if class_info.is_rest_endpoint:
                output_lines.append(f"   REST端点: {class_info.http_method} {class_info.endpoint_path}")
            
            output_lines.append(f"   方法数: {len(class_info.functions)}")
            
            dependencies = self.get_class_dependencies(class_name)
            if dependencies:
                output_lines.append(f"   依赖: {', '.join(dependencies)}")
            
            output_lines.append("")
        
        return "\n".join(output_lines)