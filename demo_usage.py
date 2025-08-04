#!/usr/bin/env python3
"""
Java Navigator 使用演示

展示如何使用优化后的 pjt_navigator 方法和类信息提取功能
"""

from java_navigator import pjt_navigator
from java_parser import JavaParser
from call_graph_analyzer import ClassAnalyzer
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

def demo_class_analysis():
    """演示类信息分析功能"""
    print("\n=== 类信息分析演示 ===")
    print()
    
    # 项目路径
    project_path = "./test/java-project"
    
    # 解析项目
    print("1. 解析Java项目...")
    parser = JavaParser()
    functions = parser.parse_project(project_path)
    classes = parser.classes
    
    print(f"   找到 {len(classes)} 个类")
    print(f"   找到 {len(functions)} 个方法")
    print()
    
    # 创建类分析器
    class_analyzer = ClassAnalyzer(classes)
    
    # 示例1: 显示类信息摘要
    print("2. 类信息摘要:")
    summary = class_analyzer.format_class_summary()
    print(summary)
    
    # 示例2: 获取符合用户要求格式的类信息
    print("3. 用户要求格式的类信息:")
    export_data = class_analyzer.get_all_classes_for_export()
    
    if export_data:
        # 显示第一个类的示例
        print("   第一个类的示例:")
        print(json.dumps(export_data[0], indent=2, ensure_ascii=False))
        print()
    
    # 示例3: 查找REST控制器
    print("4. REST控制器类:")
    rest_controllers = class_analyzer.find_rest_controllers()
    
    if rest_controllers:
        for i, controller in enumerate(rest_controllers, 1):
            print(f"   {i}. {controller['class_name']}")
            print(f"      端点: {controller['http_method']} {controller['endpoint_path']}")
            print(f"      文件: {controller['file_path']}")
            print()
    else:
        print("   未找到REST控制器类")
    
    # 示例4: 保存类信息到文件
    print("5. 保存类信息到文件:")
    output_file = "class_analysis_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"   类信息已保存到: {output_file}")
    print(f"   总共导出了 {len(export_data)} 个类的信息")

def main():
    """主函数"""
    print("Java 代码分析工具演示")
    print("=" * 50)
    
    # 演示函数分析功能
    demo_function_analysis()
    
    # 演示类分析功能
    demo_class_analysis()
    
    print("\n演示完成!")

if __name__ == "__main__":
    main()