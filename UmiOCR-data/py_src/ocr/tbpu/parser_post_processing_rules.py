# -*- coding: utf-8 -*-
"""
后处理规则解析器 - 集成到TBPU框架
"""

import re
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from .tbpu import Tbpu
from ...tag_pages.PostProcessingRules import PostProcessingRules

class PostProcessingRulesParser(Tbpu):
    """后处理规则解析器"""
    def __init__(self, target):
        super().__init__()
        self.tbpuName = "后处理规则"
        self.target = target  # screenshot_ocr, batch_ocr, batch_doc
        self.rules_manager = PostProcessingRules()

    def run(self, textBlocks, imgInfo):
        """执行后处理规则
        参数:
            textBlocks: list
                OCR识别结果的文本块列表
                每个文本块是一个dict，包含以下键：
                    'text': str - 文本内容
                    'bbox': list - 边界框坐标 [x1, y1, x2, y2]
                    'score': float - 置信度
                    'lines': list - 行信息
                        每个行是一个dict，包含以下键：
                            'text': str - 行文本
                            'bbox': list - 行边界框坐标
                            'score': float - 行置信度
        返回:
            textBlocks: list - 处理后的文本块列表
        """
        # 获取所有文本内容
        full_text = ""
        for block in textBlocks:
            full_text += block['text'] + '\n'

        # 执行后处理规则
        processed_text = self.rules_manager.process_text(self.target, full_text)

        # 更新文本块内容
        # 这里简单地将所有文本合并为一个块，实际应用中可能需要更复杂的处理
        if textBlocks:
            textBlocks[0]['text'] = processed_text.rstrip('\n')
            # 清空其他块
            del textBlocks[1:]

        return textBlocks
