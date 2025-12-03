# -*- coding: utf-8 -*- 
""" 
测试新添加的导出格式：HTML、Markdown表格、Excel 
"""

import os
import sys
import json
import tempfile
from unittest.mock import Mock

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src'))

from ocr.output import Output
from ocr.output.tools import getDataText


def create_test_result():
    """创建测试用的OCR结果数据"""
    return {
        "fileName": "test_image.png",
        "dir": tempfile.gettempdir(),
        "path": os.path.join(tempfile.gettempdir(), "test_image.png"),
        "code": 100,
        "score": 0.95,
        "time": 1.23,
        "data": [
            {
                "text": "这是第一行文字",
                "score": 0.98,
                "box": [[0, 0], [100, 0], [100, 20], [0, 20]],
                "end": "\n"
            },
            {
                "text": "这是第二行文字",
                "score": 0.92,
                "box": [[0, 20], [100, 20], [100, 40], [0, 40]],
                "end": "\n"
            },
            {
                "text": "表格内容：",
                "score": 0.96,
                "box": [[0, 40], [100, 40], [100, 60], [0, 60]],
                "end": "\n"
            },
            {
                "text": "姓名\t年龄\t性别",
                "score": 0.94,
                "box": [[0, 60], [100, 60], [100, 80], [0, 80]],
                "end": "\n"
            },
            {
                "text": "张三\t25\t男",
                "score": 0.93,
                "box": [[0, 80], [100, 80], [100, 100], [0, 100]],
                "end": "\n"
            },
            {
                "text": "李四\t30\t女",
                "score": 0.95,
                "box": [[0, 100], [100, 100], [100, 120], [0, 120]],
                "end": "\n"
            }
        ]
    }


def test_output_formats():
    """测试各种导出格式"""
    test_result = create_test_result()
    output_dir = tempfile.gettempdir()
    output_file_name = "test_export"
    
    # 测试配置
    output_argd = {
        "outputDir": output_dir,
        "outputDirType": "specify",
        "outputFileName": output_file_name,
        "startDatetime": "2023-01-01 12:00:00",
        "ignoreBlank": True,
        "includeImage": False,
        "includeConfidence": True,
        "formatStyle": "default",
        "exportFields": ["fileName", "text", "score"]
    }
    
    # 测试所有导出格式
    test_formats = [
        "html",
        "mdTable", 
        "excel",
        "txt",
        "md",
        "csv",
        "jsonl"
    ]
    
    print(f"开始测试导出格式，输出目录：{output_dir}")
    print("=" * 50)
    
    for format_type in test_formats:
        try:
            if format_type not in Output:
                print(f"❌ 格式 {format_type} 未找到")
                continue
                
            # 创建输出器
            outputter = Output[format_type](output_argd)
            
            # 输出测试结果
            outputter.print(test_result)
            
            # 结束输出
            outputter.onEnd()
            
            # 检查文件是否生成
            output_files = outputter.getOutputFiles() if hasattr(outputter, 'getOutputFiles') else []
            if not output_files:
                # 尝试自动检测输出文件
                ext = outputter.ext if hasattr(outputter, 'ext') else format_type
                output_file = os.path.join(output_dir, f"{output_file_name}.{ext}")
                if os.path.exists(output_file):
                    output_files = [output_file]
            
            if output_files:
                print(f"✅ 格式 {format_type} 测试成功")
                for file_path in output_files:
                    file_size = os.path.getsize(file_path)
                    print(f"   - 生成文件: {file_path} ({file_size} bytes)")
            else:
                print(f"❌ 格式 {format_type} 测试失败：未生成输出文件")
                
        except Exception as e:
            print(f"❌ 格式 {format_type} 测试失败：{str(e)}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 50)
    print("测试完成！")


if __name__ == "__main__":
    test_output_formats()
