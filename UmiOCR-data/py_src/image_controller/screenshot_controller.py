#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 截图控制器模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QRect, QTimer
from PySide6.QtGui import QImage, QPixmap, QGuiApplication, QScreen


class _ScreenshotControllerClass(QObject):
    """截图控制器类"""
    
    # 定义信号
    screenshot_taken = Signal(QImage)  # 截图完成信号
    screenshot_error = Signal(str)  # 截图错误信号
    
    def __init__(self):
        super().__init__()
        
        self.screenshot_timer = QTimer()
        self.screenshot_timer.setSingleShot(True)
        self.screenshot_timer.timeout.connect(self._take_screenshot)
    
    def take_screenshot(self, delay: int = 0):
        """截图"""
        if delay > 0:
            # 延迟截图
            self.screenshot_timer.start(delay)
        else:
            # 立即截图
            self._take_screenshot()
    
    def _take_screenshot(self):
        """执行截图"""
        try:
            # 获取当前屏幕
            screen = QGuiApplication.primaryScreen()
            
            if screen is None:
                raise Exception("Failed to get primary screen")
            
            # 截取整个屏幕
            screenshot = screen.grabWindow(0)
            
            if screenshot.isNull():
                raise Exception("Failed to take screenshot")
            
            # 转换为 QImage
            image = screenshot.toImage()
            
            # 发送截图完成信号
            self.screenshot_taken.emit(image)
        
        except Exception as e:
            # 发送截图错误信号
            self.screenshot_error.emit(str(e))
    
    def take_screenshot_of_region(self, region: QRect):
        """截取指定区域的屏幕"""
        try:
            # 获取当前屏幕
            screen = QGuiApplication.primaryScreen()
            
            if screen is None:
                raise Exception("Failed to get primary screen")
            
            # 截取指定区域
            screenshot = screen.grabWindow(0, region.x(), region.y(), region.width(), region.height())
            
            if screenshot.isNull():
                raise Exception("Failed to take screenshot of region")
            
            # 转换为 QImage
            image = screenshot.toImage()
            
            # 发送截图完成信号
            self.screenshot_taken.emit(image)
        
        except Exception as e:
            # 发送截图错误信号
            self.screenshot_error.emit(str(e))
    
    def get_screen_size(self) -> QRect:
        """获取屏幕大小"""
        try:
            # 获取当前屏幕
            screen = QGuiApplication.primaryScreen()
            
            if screen is None:
                raise Exception("Failed to get primary screen")
            
            # 获取屏幕大小
            return screen.geometry()
        
        except Exception as e:
            # 发送截图错误信号
            self.screenshot_error.emit(str(e))
            return QRect(0, 0, 0, 0)


# 全局截图控制器实例
ScreenshotController = _ScreenshotControllerClass()