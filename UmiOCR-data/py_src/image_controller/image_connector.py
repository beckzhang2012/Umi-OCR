#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 图像连接器模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from .image_controller import ImageController


class ImageConnector(QObject):
    """图像连接器类，用于连接图像控制器和其他模块"""
    
    # 定义信号
    image_loaded = Signal(QImage)  # 图像加载完成信号
    image_saved = Signal(str)  # 图像保存完成信号
    screenshot_taken = Signal(QImage)  # 截图完成信号
    image_error = Signal(str)  # 图像错误信号
    
    def __init__(self, event_bus=None):
        super().__init__()
        
        self.event_bus = event_bus
        self.image_controller = ImageController(event_bus)
        
        # 连接信号和槽
        self._connect_signals()
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _connect_signals(self):
        """连接信号和槽"""
        # 连接图像控制器的信号
        self.image_controller.image_loaded.connect(self.image_loaded)
        self.image_controller.image_saved.connect(self.image_saved)
        self.image_controller.screenshot_taken.connect(self.screenshot_taken)
        
        # 连接图像提供者的错误信号
        self.image_controller.get_image_provider().image_error.connect(self.image_error)
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        if self.event_bus:
            # 这里可以添加事件处理函数的注册逻辑
            pass
    
    @Slot(str)
    def load_image(self, image_path: str):
        """加载图像"""
        self.image_controller.load_image(image_path)
    
    @Slot(QImage, str)
    def save_image(self, image: QImage, image_path: str):
        """保存图像"""
        self.image_controller.save_image(image, image_path)
    
    @Slot()
    def take_screenshot(self):
        """截图"""
        self.image_controller.take_screenshot()
    
    def get_image_controller(self) -> ImageController:
        """获取图像控制器"""
        return self.image_controller
    
    def start(self):
        """启动图像连接器"""
        self.image_controller.start()
    
    def stop(self):
        """停止图像连接器"""
        self.image_controller.stop()