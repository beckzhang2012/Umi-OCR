#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动保存OCR结果到审阅看板模块
监听OCR完成事件并自动保存到审阅看板
"""

from umi_log import logger
from .event_bus.pubsub_service import PubSubService
from .review_data_manager import get_data_manager

class AutoSaveReview:
    """自动保存OCR结果到审阅看板"""
    
    def __init__(self):
        self.data_manager = get_data_manager()
        self._setup_listeners()
        logger.info("自动保存OCR结果到审阅看板模块已初始化")
    
    def _setup_listeners(self):
        """设置事件监听器"""
        # 监听截图OCR完成事件
        PubSubService.subscribe("<<ScreenshotOcrEnd>>", self._on_screenshot_ocr_end)
        
        # 监听批量OCR完成事件
        PubSubService.subscribe("<<BatchOcrEnd>>", self._on_batch_ocr_end)
        
        # 监听文档OCR完成事件
        PubSubService.subscribe("<<BatchDocEnd>>", self._on_batch_doc_end)
    
    def _on_screenshot_ocr_end(self, results):
        """截图OCR完成事件处理"""
        if not results:
            return
        
        for res in results:
            if res.get("code") == 100:  # 识别成功
                self._save_ocr_result(res, "screenshot")
    
    def _on_batch_ocr_end(self, results):
        """批量OCR完成事件处理"""
        if not results:
            return
        
        for res in results:
            if res.get("code") == 100:  # 识别成功
                self._save_ocr_result(res, "batch_ocr")
    
    def _on_batch_doc_end(self, results):
        """文档OCR完成事件处理"""
        if not results:
            return
        
        for res in results:
            if res.get("code") == 100:  # 识别成功
                self._save_ocr_result(res, "batch_doc")
    
    def _save_ocr_result(self, res, source_type):
        """保存OCR结果到审阅看板"""
        try:
            # 提取识别文本
            data = res.get("data", [])
            if not data:
                return
            
            # 拼接完整文本
            full_text = "\n".join([item.get("text", "") for item in data])
            
            # 生成文本摘要（前200字符）
            text_summary = full_text[:200] + ("..." if len(full_text) > 200 else "")
            
            # 获取置信度
            confidence = res.get("score", 0.0)
            
            # 获取来源路径
            source_path = res.get("path", "") or f"{source_type}_ocr"
            
            # 添加到审阅看板
            record_id = self.data_manager.add_record(
                source_path=source_path,
                text_summary=text_summary,
                confidence=confidence,
                full_text=full_text
            )
            
            logger.info(f"OCR结果已自动保存到审阅看板: {record_id}")
            
        except Exception as e:
            logger.error(f"自动保存OCR结果到审阅看板失败: {e}")

# 全局实例
_auto_save_review = None

def init_auto_save_review():
    """初始化自动保存模块"""
    global _auto_save_review
    if _auto_save_review is None:
        _auto_save_review = AutoSaveReview()
    return _auto_save_review

if __name__ == "__main__":
    # 测试代码
    init_auto_save_review()
    
    # 模拟OCR完成事件
    test_result = {
        "code": 100,
        "data": [
            {"text": "这是测试文本第一行", "score": 0.95},
            {"text": "这是测试文本第二行", "score": 0.98}
        ],
        "score": 0.965,
        "path": "test/image.jpg"
    }
    
    # 发布测试事件
    PubSubService.publish("<<ScreenshotOcrEnd>>", [test_result])
    
    print("测试完成，检查审阅看板数据是否已保存")