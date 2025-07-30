#!/usr/bin/env python3
"""
Content Extractor - 用于提取函数代码内容的工具

主要功能:
    - 从pjt_navigator返回的function_info_json中提取函数代码内容
    - 将Java代码进行适当的转义以便存储在JSON中
"""

import json
import os
import logging
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def escape_java_code(code: str) -> str:
    """
    将Java代码进行转义，以便安全地存储在JSON中
    
    Args:
        code: 原始Java代码字符串
        
    Returns:
        str: 转义后的Java代码字符串
    """
    if not code:
        return ""
    
    escaped_code = code.replace("\\", "\\\\")   # 反斜杠转义
    escaped_code = escaped_code.replace("\"", "\\\"")   # 双引号转义
    escaped_code = escaped_code.replace("/", "\\/")     # 斜杠转义（防止与正则冲突）
    escaped_code = escaped_code.replace("\n", "\\n")    # 换行符转义
    escaped_code = escaped_code.replace("\t", "\\t")    # 制表符转义
    escaped_code = escaped_code.replace("\r", "\\r")    # 回车符转义
    
    return escaped_code


def read_code_lines(file_path: str, start_line: int, end_line: int) -> Optional[str]:
    """
    从文件中读取指定行范围的代码
    
    Args:
        file_path: 文件路径
        start_line: 开始行号（从1开始）
        end_line: 结束行号（包含）
        
    Returns:
        Optional[str]: 代码内容，如果文件不存在或读取失败则返回None
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 检查行号范围是否有效
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            logger.error(f"无效的行号范围: {start_line}-{end_line}，文件总行数: {len(lines)}")
            return None
            
        # 提取指定范围的行（注意：列表索引从0开始，行号从1开始）
        selected_lines = lines[start_line-1:end_line]
        
        # 合并行并返回
        return ''.join(selected_lines)
        
    except Exception as e:
        logger.error(f"读取文件时发生错误 {file_path}: {e}")
        return None


def java_extract(function_info_json: str) -> str:
    """
    从pjt_navigator返回的function_info_json中提取Java函数代码内容
    
    Args:
        function_info_json: pjt_navigator方法返回的第二个结果（字符串格式的JSON）
        
    Returns:
        str: 包含函数名称和代码内容的JSON字符串
    """
    try:
        # 1. 将str格式的function_info_json读取成dict
        function_info = json.loads(function_info_json)
        
        # 检查是否包含错误信息
        if "error" in function_info:
            logger.error(f"输入的function_info_json包含错误: {function_info['error']}")
            return json.dumps({"error": function_info["error"]}, indent=2, ensure_ascii=False)
        
        # 2. 提取其中的functions列表
        if "functions" not in function_info:
            error_msg = "function_info_json中没有找到functions字段"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, indent=2, ensure_ascii=False)
            
        functions_list = function_info["functions"]
        
        if not functions_list:
            error_msg = "functions列表为空"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, indent=2, ensure_ascii=False)
        
        # 3. 遍历functions列表，提取代码内容
        result_functions = []
        
        for func in functions_list:
            try:
                # 获取函数信息
                function_name = func.get("name", "")
                class_name = func.get("class_name", "")
                file_path = func.get("file_path", "")
                start_line = func.get("start_line", 0)
                end_line = func.get("end_line", 0)
                
                # 构造完整的函数名称
                if class_name:
                    full_function_name = f"{class_name}.{function_name}"
                else:
                    full_function_name = function_name
                
                logger.info(f"处理函数: {full_function_name}")
                
                # 检查必要的字段
                if not file_path or start_line <= 0 or end_line <= 0:
                    logger.warning(f"函数 {full_function_name} 缺少必要的位置信息，跳过")
                    continue
                
                # 读取代码内容
                code_content = read_code_lines(file_path, start_line, end_line)
                
                if code_content is None:
                    logger.warning(f"无法读取函数 {full_function_name} 的代码内容，跳过")
                    continue
                
                # 转义Java代码
                escaped_code = escape_java_code(code_content)
                
                # 添加到结果中
                result_functions.append({
                    "function_name": full_function_name,
                    "code_contents": escaped_code
                })
                
                logger.info(f"成功提取函数 {full_function_name} 的代码内容")
                
            except Exception as e:
                logger.error(f"处理函数时发生错误: {e}")
                continue
        
        # 4. 返回JSON格式的结果
        if not result_functions:
            error_msg = "没有成功提取到任何函数的代码内容"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, indent=2, ensure_ascii=False)
        
        logger.info(f"成功提取了 {len(result_functions)} 个函数的代码内容")
        
        # 返回结果JSON
        return json.dumps(result_functions, indent=2, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        error_msg = f"解析function_info_json时发生错误: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"提取代码内容时发生错误: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, indent=2, ensure_ascii=False)


def main():
    """
    测试主函数
    """
    import sys
    from java_navigator import pjt_navigator
    
    if len(sys.argv) < 3:
        print("使用方法: python content_extractor.py <function_name> <project_dir>")
        print("示例: python content_extractor.py getUserById ./test/java-project")
        sys.exit(1)
    
    function_name = sys.argv[1]
    project_dir = sys.argv[2]
    
    print(f"分析函数: {function_name}")
    print(f"项目目录: {project_dir}")
    print("="*60)
    
    # 先调用pjt_navigator获取函数信息
    mermaid_str, function_info_json = pjt_navigator(function_name, project_dir)
    
    if not function_info_json:
        print("pjt_navigator没有返回函数信息")
        sys.exit(1)
    
    # 提取代码内容
    result = java_extract(function_info_json)
    
    print("代码提取结果:")
    print("="*60)
    print(result)


if __name__ == "__main__":
    main()