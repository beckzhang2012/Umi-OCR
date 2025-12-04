#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句柄泄漏测试启动脚本
用于运行句柄泄漏回归测试
"""

import os
import sys
import subprocess
import argparse

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行句柄泄漏回归测试")
    parser.add_argument("--duration", type=int, default=120, help="测试持续时间（秒）")
    parser.add_argument("--threads", type=int, default=3, help="并发线程数")
    parser.add_argument("--tasks-per-thread", type=int, default=100, help="每个线程的任务数")
    parser.add_argument("--files-per-task", type=int, default=10, help="每个任务的文件数")
    parser.add_argument("--file-size", type=int, default=1024, help="每个文件的大小（字节）")
    
    args = parser.parse_args()
    
    # 构建测试命令
    test_script = os.path.join(os.path.dirname(__file__), "tests", "handle_leak_test.py")
    
    if not os.path.exists(test_script):
        print(f"错误：测试脚本不存在: {test_script}")
        sys.exit(1)
    
    # 运行测试
    print("=== 启动句柄泄漏回归测试 ===")
    print(f"测试配置:")
    print(f"  持续时间: {args.duration}秒")
    print(f"  并发线程数: {args.threads}")
    print(f"  每个线程任务数: {args.tasks_per_thread}")
    print(f"  每个任务文件数: {args.files_per_task}")
    print(f"  文件大小: {args.file_size}字节")
    print()
    
    try:
        # 运行测试脚本
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        # 打印测试输出
        print("测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("测试错误:")
            print(result.stderr)
        
        # 检查测试结果
        if result.returncode == 0:
            print("\n=== 测试通过 ===")
            print("句柄管理正常，未发现泄漏问题。")
        else:
            print("\n=== 测试失败 ===")
            print("发现句柄泄漏问题，请检查日志。")
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"运行测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()