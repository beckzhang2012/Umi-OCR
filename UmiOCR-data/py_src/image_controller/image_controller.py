#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 图像控制器模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from .image_provider import ImageProvider
from .screenshot_controller import ScreenshotController


class ImageController(QObject):
    """图像控制器类，用于处理图像相关的操作"""
    
    # 定义信号
    image_loaded = Signal(QImage)  # 图像加载完成信号
    image_saved = Signal(str)  # 图像保存完成信号
    screenshot_taken = Signal(QImage)  # 截图完成信号
    
    def __init__(self, event_bus=None):
        super().__init__()
        
        self.event_bus = event_bus
        self.image_provider = ImageProvider()
        self.screenshot_controller = ScreenshotController()
        
        # 连接信号和槽
        self._connect_signals()
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _connect_signals(self):
        """连接信号和槽"""
        # 连接图像提供者的信号
        self.image_provider.image_loaded.connect(self.image_loaded)
        self.image_provider.image_saved.connect(self.image_saved)
        
        # 连接截图控制器的信号
        self.screenshot_controller.screenshot_taken.connect(self.screenshot_taken)
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        if self.event_bus:
            # 这里可以添加事件处理函数的注册逻辑
            pass
    
    def load_image(self, image_path: str):
        """加载图像"""
        self.image_provider.load_image(image_path)
    
    def save_image(self, image: QImage, image_path: str):
        """保存图像"""
        self.image_provider.save_image(image, image_path)
    
    def take_screenshot(self):
        """截图"""
        self.screenshot_controller.take_screenshot()
    
    def get_image_provider(self) -> ImageProvider:
        """获取图像提供者"""
        return self.image_provider
    
    def get_screenshot_controller(self) -> ScreenshotController:
        """获取截图控制器"""
        return self.screenshot_controller
    
    def start(self):
        """启动图像控制器"""
        # 这里可以添加启动逻辑
        pass
    
    def stop(self):
        """停止图像控制器"""
        # 这里可以添加停止逻辑
        pass