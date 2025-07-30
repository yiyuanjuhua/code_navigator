#!/usr/bin/env python3
"""
Java Navigator 使用演示

展示如何使用优化后的 pjt_navigator 方法
"""

from java_navigator import pjt_navigator
import json

def demo_function_analysis():
    """演示函数分析功能"""
    print("=== Java Navigator Demo ===")
    print()
    
    # 项目路径
    project_path = "./test/java-project"
    
    # 示例1: 通过函数名查找
    print("1. 通过函数名查找:")
    mermaid_str, function_info_json = pjt_navigator("getUserById", project_path)
    
    result = json.loads(function_info_json)
    print(f"   找到函数: {result['target_function']}")
    print(f"   调用链路长度: {result['total_functions']}")
    
    # 显示第一个函数的信息
    if result['functions']:
        func = result['functions'][0]
        print(f"   文件: {func['file_path']}")
        print(f"   行数: {func['start_line']}-{func['end_line']}")
    print()
    
    # 示例2: 通过REST接口路径查找
    print("2. 通过REST接口路径查找:")
    mermaid_str, function_info_json = pjt_navigator("/api/users/{id}", project_path)
    
    result = json.loads(function_info_json)
    print(f"   找到接口: {result['target_function']}")
    
    if result['functions']:
        func = result['functions'][0]
        print(f"   HTTP方法: {func['http_method']}")
        print(f"   接口路径: {func['endpoint_path']}")
        print(f"   调用的函数: {func['called_functions']}")
    print()
    
    # 示例3: 显示完整的Mermaid图表
    print("3. 生成的Mermaid图表:")
    print("```mermaid")
    print(mermaid_str)
    print("```")
    print()
    
    # 示例4: 显示完整的JSON信息
    print("4. 完整的函数信息 (JSON格式):")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demo_function_analysis()