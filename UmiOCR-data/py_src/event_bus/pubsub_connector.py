#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 发布订阅连接器模块
"""

import sys
from PySide6.QtCore import QObject, Signal, Slot

from .pubsub_service import PubSubService


class PubSubConnector(QObject):
    """发布订阅连接器类，用于连接事件总线和发布订阅服务"""
    
    # 定义信号
    signal = Signal(str, object)  # 主题名称，主题数据
    
    def __init__(self):
        super().__init__()
        
        # 连接信号和槽
        self.signal.connect(self._on_signal)
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        # 这里可以添加事件处理函数的注册逻辑
        pass
    
    def publish(self, topic: str, topic_data: object = None):
        """发布主题"""
        self.signal.emit(topic, topic_data)
    
    @Slot(str, object)
    def _on_signal(self, topic: str, topic_data: object = None):
        """处理信号"""
        # 发布主题到发布订阅服务
        PubSubService.publish(topic, topic_data)
    
    def subscribe(self, topic: str, callback: callable):
        """订阅主题"""
        PubSubService.subscribe(topic, callback)
    
    def unsubscribe(self, topic: str, callback: callable):
        """取消订阅主题"""
        PubSubService.unsubscribe(topic, callback)