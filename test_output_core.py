# -*- coding: utf-8 -*- 
""" 
测试输出器核心功能，不依赖项目导入结构 
"""

import os
import sys
import tempfile
import json
from unittest.mock import Mock

# 添加输出器目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src', 'ocr', 'output'))


# 模拟Output基类
class MockOutput:
    def __init__(self, argd):
        self.argd = argd
        self.ext = "txt"
        self.files = []
        
    def openOutputFile(self, fileName=None, ext=None):
        """模拟打开输出文件"""
        if fileName is None:
            fileName = self.argd["outputFileName"]
        if ext is None:
            ext = self.ext
            
        outputDir = self.argd["outputDir"]
        filePath = os.path.join(outputDir, f"{fileName}.{ext}")
        self.files.append(filePath)
        return open(filePath, 'w', encoding='utf-8')


# 模拟工具函数
def mock_getDataText(data):
    """模拟获取文本数据"""
    text_parts = []
    for tb in data:
        text_parts.append(tb["text"])
        if tb.get("end"):
            text_parts.append(tb["end"])
    return ''.join(text_parts)


# 创建测试结果
def create_test_result():
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


# 测试HTML输出器
try:
    # 临时替换依赖
    from output_html import OutputHTML
    OutputHTML.__bases__ = (MockOutput,)
    
    print("测试HTML输出器...")
    argd = {
        "outputDir": tempfile.gettempdir(),
        "outputFileName": "test_html",
        "ignoreBlank": True,
        "includeImage": False,
        "includeConfidence": True
    }
    
    outputter = OutputHTML(argd)
    outputter.getDataText = mock_getDataText
    
    # 测试输出
    result = create_test_result()
    outputter.print(result)
    outputter.onEnd()
    
    print(f"✅ HTML输出器测试成功，生成文件: {outputter.files[0]}")
except Exception as e:
    print(f"❌ HTML输出器测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# 测试Markdown表格输出器
try:
    from output_md_table import OutputMDTable
    OutputMDTable.__bases__ = (MockOutput,)
    
    print("测试Markdown表格输出器...")
    argd = {
        "outputDir": tempfile.gettempdir(),
        "outputFileName": "test_md_table",
        "ignoreBlank": True
    }
    
    outputter = OutputMDTable(argd)
    outputter.getDataText = mock_getDataText
    
    # 测试输出
    result = create_test_result()
    outputter.print(result)
    outputter.onEnd()
    
    print(f"✅ Markdown表格输出器测试成功，生成文件: {outputter.files[0]}")
except Exception as e:
    print(f"❌ Markdown表格输出器测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# 测试Excel输出器
try:
    from output_excel import OutputExcel
    OutputExcel.__bases__ = (MockOutput,)
    
    print("测试Excel输出器...")
    argd = {
        "outputDir": tempfile.gettempdir(),
        "outputFileName": "test_excel",
        "ignoreBlank": True,
        "includeConfidence": True
    }
    
    outputter = OutputExcel(argd)
    outputter.getDataText = mock_getDataText
    
    # 测试输出
    result = create_test_result()
    outputter.print(result)
    outputter.onEnd()
    
    print(f"✅ Excel输出器测试成功，生成文件: {outputter.files[0]}")
except Exception as e:
    print(f"❌ Excel输出器测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("所有测试完成！")
