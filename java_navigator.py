#!/usr/bin/env python3
"""
Java Navigator - 用于解析Java工程代码生成函数地图的工具

使用方法:
    python java_navigator.py <function_name> <project_dir>

功能:
    - 解析Java工程代码生成函数信息
    - 输出函数调用链路的Mermaid图
    - 显示链路上所有函数的详细信息
"""

import sys
import os
import argparse
import logging
from typing import List, Optional

# Import our modules
from java_parser import JavaParser, FunctionInfo
from call_graph_analyzer import CallGraphAnalyzer, MermaidGenerator, ResultFormatter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr to keep stdout clean for results
    ]
)
logger = logging.getLogger(__name__)

def validate_project_directory(project_dir: str) -> bool:
    """验证项目目录是否有效"""
    if not os.path.exists(project_dir):
        print(f"错误: 项目目录不存在: {project_dir}")
        return False
    
    src_dir = os.path.join(project_dir, "src")
    if not os.path.exists(src_dir):
        print(f"错误: 项目目录下不存在src文件夹: {src_dir}")
        return False
    
    return True

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Java Navigator - 解析Java工程代码生成函数调用关系图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python java_navigator.py getUserById ./test/java-project
    python java_navigator.py UserController.createUser ./test/java-project
    python java_navigator.py "/api/users/{id}" ./test/java-project
        """
    )
    
    parser.add_argument(
        "function_name",
        help="要查找的函数名称、类.方法名或接口路径"
    )
    
    parser.add_argument(
        "project_dir",
        help="Java工程所在的目录路径"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="函数调用链的最大深度 (默认: 10)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细的解析过程信息"
    )
    
    return parser.parse_args()

def main():
    """主函数"""
    # Parse command line arguments
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate project directory
    if not validate_project_directory(args.project_dir):
        sys.exit(1)
    
    try:
        print("正在解析Java工程...")
        
        # Initialize parser and parse project
        parser = JavaParser()
        functions = parser.parse_project(args.project_dir)
        
        if not functions:
            print("错误: 在工程中没有找到任何函数")
            sys.exit(1)
        
        print(f"成功解析到 {len(functions)} 个函数")
        
        # Initialize analyzer
        analyzer = CallGraphAnalyzer(functions)
        
        # Find matching functions
        matching_functions = analyzer.find_function_by_name(args.function_name)
        
        if not matching_functions:
            print(f"错误: 没有找到匹配的函数: {args.function_name}")
            print("\n可用的函数列表:")
            for func_key in sorted(functions.keys()):
                func_info = functions[func_key]
                if func_info.is_rest_endpoint:
                    print(f"  {func_key} (REST: {func_info.http_method} {func_info.endpoint_path})")
                else:
                    print(f"  {func_key}")
            sys.exit(1)
        
        # If multiple matches, use the first one (could be enhanced to let user choose)
        target_function = matching_functions[0]
        
        if len(matching_functions) > 1:
            print(f"找到多个匹配的函数，使用第一个: {target_function}")
            for func in matching_functions[1:]:
                print(f"  其他匹配: {func}")
            print()
        
        print(f"分析函数调用链: {target_function}")
        
        # Get call chain
        call_chain = analyzer.get_call_chain(target_function, args.max_depth)
        
        if not call_chain:
            print(f"错误: 无法获取函数调用链: {target_function}")
            sys.exit(1)
        
        # Generate Mermaid diagram
        mermaid_generator = MermaidGenerator()
        mermaid_diagram = mermaid_generator.generate_mermaid_diagram(call_chain)
        
        # Get all functions in chain
        all_functions = analyzer.get_all_functions_in_chain(call_chain)
        
        # Output results
        print("\n" + "="*60)
        print("函数调用关系图 (Mermaid格式)")
        print("="*60)
        print()
        print("```mermaid")
        print(mermaid_diagram)
        print("```")
        print()
        
        # Output call chain summary
        summary = ResultFormatter.format_call_chain_summary(call_chain)
        print(summary)
        
        # Output detailed function information
        function_details = ResultFormatter.format_function_info(all_functions)
        print(function_details)
        
        print("="*60)
        print("分析完成!")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()