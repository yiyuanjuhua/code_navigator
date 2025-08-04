#!/usr/bin/env python3
"""
测试类信息提取功能
"""

import os
import json
from java_parser import JavaParser
from typing import List, Dict

def test_class_extraction(project_path: str):
    """测试类信息提取功能"""
    print("正在解析Java项目...")
    parser = JavaParser()
    
    try:
        # 解析项目
        functions = parser.parse_project(project_path)
        
        # 获取类信息
        classes = parser.get_classes_as_list()
        
        print(f"解析完成:")
        print(f"- 找到 {len(classes)} 个类")
        print(f"- 找到 {len(functions)} 个方法")
        print()
        
        # 显示类信息摘要
        print("=== 类信息摘要 ===")
        for i, class_info in enumerate(classes, 1):
            print(f"{i}. 类名: {class_info.class_name}")
            print(f"   文件: {class_info.file_path}")
            print(f"   行数: {class_info.start_line}-{class_info.end_line}")
            print(f"   公有: {'是' if class_info.is_public else '否'}")
            print(f"   REST端点: {'是' if class_info.is_rest_endpoint else '否'}")
            if class_info.is_rest_endpoint:
                print(f"   端点路径: {class_info.endpoint_path}")
                print(f"   HTTP方法: {class_info.http_method}")
            print(f"   包含方法数: {len(class_info.functions)}")
            print(f"   调用函数数: {len(class_info.called_functions)}")
            print()
        
        # 输出JSON格式的类信息
        print("=== JSON格式的类信息 ===")
        classes_json = parser.get_classes_as_json()
        
        # 保存到文件
        output_file = "class_extraction_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(classes_json)
        
        print(f"类信息已保存到: {output_file}")
        
        # 显示第一个类的示例
        if classes:
            print("\n=== 第一个类的详细信息示例 ===")
            first_class = classes[0]
            example_dict = first_class.to_dict()
            print(json.dumps(example_dict, indent=2, ensure_ascii=False))
        
        return classes
        
    except Exception as e:
        print(f"解析失败: {e}")
        return []

def main():
    """主函数"""
    print("类信息提取测试工具")
    print("=" * 40)
    
    # 获取项目路径
    project_path = input("请输入Java项目路径 (留空使用当前目录): ").strip()
    if not project_path:
        project_path = "."
    
    if not os.path.exists(project_path):
        print(f"错误: 路径不存在 {project_path}")
        return
    
    # 测试类信息提取
    classes = test_class_extraction(project_path)
    
    if classes:
        print(f"\n✅ 成功提取了 {len(classes)} 个类的信息")
    else:
        print("\n❌ 未找到任何类或解析失败")

if __name__ == "__main__":
    main()