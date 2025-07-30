#!/usr/bin/env python3
"""
虚拟环境设置脚本
用于初始化Java Navigator项目的Python虚拟环境
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

def create_virtual_environment():
    """创建虚拟环境"""
    venv_dir = Path("venv")
    
    if venv_dir.exists():
        print("虚拟环境已存在")
        return str(venv_dir)
    
    print("正在创建虚拟环境...")
    venv.create(venv_dir, with_pip=True)
    print(f"虚拟环境已创建: {venv_dir}")
    
    return str(venv_dir)

def install_requirements(venv_dir):
    """安装依赖包"""
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("未找到requirements.txt文件")
        return
    
    # 确定pip的路径
    if os.name == 'nt':  # Windows
        pip_path = Path(venv_dir) / "Scripts" / "pip.exe"
    else:  # Unix-like
        pip_path = Path(venv_dir) / "bin" / "pip"
    
    print("正在安装依赖包...")
    try:
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("依赖包安装成功")
    except subprocess.CalledProcessError as e:
        print(f"安装依赖包时出错: {e}")
        print(f"错误输出: {e.stderr}")

def print_activation_instructions(venv_dir):
    """打印激活虚拟环境的说明"""
    print("\n" + "="*50)
    print("虚拟环境设置完成！")
    print("="*50)
    
    if os.name == 'nt':  # Windows
        activate_script = Path(venv_dir) / "Scripts" / "activate.bat"
        print(f"Windows激活命令: {activate_script}")
        print("或者使用: venv\\Scripts\\activate")
    else:  # Unix-like
        activate_script = Path(venv_dir) / "bin" / "activate"
        print(f"Linux/Mac激活命令: source {activate_script}")
        print("或者使用: source venv/bin/activate")
    
    print("\n激活后可以运行:")
    print("python java_navigator.py --help")
    print("python demo_usage.py")

def main():
    """主函数"""
    print("Java Navigator - 虚拟环境设置")
    print("="*40)
    
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本")
        sys.exit(1)
    
    # 创建虚拟环境
    venv_dir = create_virtual_environment()
    
    # 安装依赖
    install_requirements(venv_dir)
    
    # 显示激活说明
    print_activation_instructions(venv_dir)

if __name__ == "__main__":
    main()