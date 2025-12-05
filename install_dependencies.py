#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= 依赖项安装脚本 ==================
# ===============================================

import os
import sys
import subprocess


def install_dependency(package_name):
    """
    安装单个依赖项
    
    Args:
        package_name: 依赖项名称
    
    Returns:
        是否安装成功
    """
    print(f"正在安装依赖项: {package_name}")
    
    try:
        # 使用pip安装依赖项
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"依赖项 {package_name} 安装成功")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"依赖项 {package_name} 安装失败")
        print(f"错误输出: {e.stderr}")
        return False


def main():
    """主函数"""
    print("=== Umi-OCR 依赖项安装脚本 ===")
    
    # 检查pip是否可用
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
    
    except subprocess.CalledProcessError:
        print("错误: pip不可用，请先安装pip")
        return
    
    # 定义必要的依赖项
    dependencies = [
        "psutil",  # 系统资源监控
        "pynvml",  # NVIDIA GPU监控
        "PySide2",  # UI框架
        "requests",  # HTTP请求
        "Pillow",  # 图像处理
    ]
    
    # 安装所有依赖项
    success_count = 0
    
    for package in dependencies:
        if install_dependency(package):
            success_count += 1
    
    print(f"\n=== 安装完成 ===")
    print(f"成功安装: {success_count}/{len(dependencies)} 个依赖项")
    
    if success_count == len(dependencies):
        print("所有依赖项都已成功安装")
    else:
        print("部分依赖项安装失败，请检查错误信息并手动安装")


if __name__ == "__main__":
    main()
