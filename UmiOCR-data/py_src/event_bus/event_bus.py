#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 事件总线模块
"""

import sys
from PySide6.QtCore import QObject, Signal, Slot


class EventBus(QObject):
    """事件总线类，用于在不同组件之间传递事件"""
    
    # 定义信号
    signal = Signal(str, object)  # 事件名称，事件数据
    
    def __init__(self):
        super().__init__()
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        # 这里可以添加事件处理函数的注册逻辑
        pass
    
    def publish(self, event_name: str, event_data: object = None):
        """发布事件"""
        self.signal.emit(event_name, event_data)
    
    @Slot(str, object)
    def on_event(self, event_name: str, event_data: object = None):
        """事件处理函数"""
        # 这里可以添加事件处理逻辑
        pass