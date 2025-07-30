#!/usr/bin/env python3
"""
Java Navigator - 用于解析Java工程代码生成函数地图的工具

使用方法:
    python java_navigator.py <function_name> <project_dir>
    
    或者在代码中调用:
    mermaid_str, function_info_json = pjt_navigator(start_point, project_dir)

功能:
    - 解析Java工程代码生成函数信息（专注于src/main目录）
    - 输出函数调用链路的Mermaid图
    - 显示链路上所有函数的详细信息（JSON格式）
    - 支持Spring Boot和JAX-RS注解（包括jakarta.ws.rs.Path）
"""

import sys
import os
import json
import argparse
import logging
from typing import List, Optional, Tuple, Dict

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
        logger.error(f"项目目录不存在: {project_dir}")
        return False
    
    # 优先检查src/main/java目录
    src_main_java = os.path.join(project_dir, "src", "main", "java")
    src_dir = os.path.join(project_dir, "src")
    
    if not os.path.exists(src_main_java) and not os.path.exists(src_dir):
        logger.error(f"项目目录下不存在src文件夹或src/main/java文件夹: {project_dir}")
        return False
    
    return True

def pjt_navigator(start_point: str, project_dir: str, max_depth: int = 10) -> Tuple[str, str]:
    """
    对外调用方法：分析Java项目并生成函数调用链路
    
    Args:
        start_point: 起始函数名称、类.方法名或接口路径
        project_dir: Java工程所在的目录路径
        max_depth: 函数调用链的最大深度 (默认: 10)
    
    Returns:
        Tuple[str, str]: (mermaid_str, function_info_json)
        - mermaid_str: Mermaid格式的调用关系图
        - function_info_json: JSON格式的函数信息
    """
    try:
        # 验证项目目录
        if not validate_project_directory(project_dir):
            raise ValueError(f"无效的项目目录: {project_dir}")
        
        logger.info(f"开始解析Java工程: {project_dir}")
        
        # 初始化解析器并解析项目
        parser = JavaParser()
        functions = parser.parse_project(project_dir)
        
        if not functions:
            raise ValueError("在工程中没有找到任何函数")
        
        logger.info(f"成功解析到 {len(functions)} 个函数")
        
        # 初始化分析器
        analyzer = CallGraphAnalyzer(functions)
        
        # 查找匹配的函数
        matching_functions = analyzer.find_function_by_name(start_point)
        
        if not matching_functions:
            available_functions = []
            for func_key, func_info in functions.items():
                if func_info.is_rest_endpoint:
                    available_functions.append({
                        "name": func_key,
                        "type": "REST",
                        "method": func_info.http_method,
                        "path": func_info.endpoint_path
                    })
                else:
                    available_functions.append({
                        "name": func_key,
                        "type": "FUNCTION"
                    })
            
            error_info = {
                "error": f"没有找到匹配的函数: {start_point}",
                "available_functions": available_functions
            }
            return "", json.dumps(error_info, indent=2, ensure_ascii=False)
        
        # 使用第一个匹配的函数
        target_function = matching_functions[0]
        
        if len(matching_functions) > 1:
            logger.warning(f"找到多个匹配的函数，使用第一个: {target_function}")
        
        logger.info(f"分析函数调用链: {target_function}")
        
        # 获取调用链
        call_chain = analyzer.get_call_chain(target_function, max_depth)
        
        if not call_chain:
            error_info = {
                "error": f"无法获取函数调用链: {target_function}"
            }
            return "", json.dumps(error_info, indent=2, ensure_ascii=False)
        
        # 生成Mermaid图表
        mermaid_generator = MermaidGenerator()
        mermaid_diagram = mermaid_generator.generate_mermaid_diagram(call_chain)
        
        # 获取链路中的所有函数
        all_functions = analyzer.get_all_functions_in_chain(call_chain)
        
        # 生成JSON格式的函数信息
        functions_info = []
        for func in all_functions:
            func_info = {
                "name": func.name,
                "class_name": func.class_name,
                "file_path": func.file_path,
                "start_line": func.start_line,
                "end_line": func.end_line,
                "is_public": func.is_public,
                "is_rest_endpoint": func.is_rest_endpoint,
                "endpoint_path": func.endpoint_path,
                "http_method": func.http_method,
                "called_functions": func.called_functions
            }
            functions_info.append(func_info)
        
        # 创建完整的结果对象
        result = {
            "start_point": start_point,
            "target_function": target_function,
            "total_functions": len(all_functions),
            "max_depth": max_depth,
            "functions": functions_info
        }
        
        function_info_json = json.dumps(result, indent=2, ensure_ascii=False)
        
        return mermaid_diagram, function_info_json
        
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        error_info = {
            "error": str(e),
            "start_point": start_point,
            "project_dir": project_dir
        }
        return "", json.dumps(error_info, indent=2, ensure_ascii=False)

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
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="仅输出JSON格式的函数信息"
    )
    
    return parser.parse_args()

def main():
    """命令行主函数"""
    # Parse command line arguments
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 使用pjt_navigator方法
        mermaid_diagram, function_info_json = pjt_navigator(
            args.function_name, 
            args.project_dir, 
            args.max_depth
        )
        
        # 检查是否有错误
        try:
            result = json.loads(function_info_json)
            if "error" in result:
                print(f"错误: {result['error']}")
                if "available_functions" in result:
                    print("\n可用的函数列表:")
                    for func in result["available_functions"]:
                        if func["type"] == "REST":
                            print(f"  {func['name']} (REST: {func['method']} {func['path']})")
                        else:
                            print(f"  {func['name']}")
                sys.exit(1)
        except json.JSONDecodeError:
            pass
        
        if args.json_only:
            # 仅输出JSON
            print(function_info_json)
        else:
            # 输出完整结果
            print("\n" + "="*60)
            print("函数调用关系图 (Mermaid格式)")
            print("="*60)
            print()
            print("```mermaid")
            print(mermaid_diagram)
            print("```")
            print()
            
            print("="*60)
            print("函数信息 (JSON格式)")
            print("="*60)
            print()
            print(function_info_json)
            print()
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