#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 图像提供者模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QImageReader, QImageWriter


class ImageProvider(QObject):
    """图像提供者类，用于加载和保存图像"""
    
    # 定义信号
    image_loaded = Signal(QImage)  # 图像加载完成信号
    image_saved = Signal(str)  # 图像保存完成信号
    image_error = Signal(str)  # 图像错误信号
    
    def __init__(self):
        super().__init__()
    
    def load_image(self, image_path: str):
        """加载图像"""
        try:
            # 检查图像文件是否存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # 加载图像
            image_reader = QImageReader(image_path)
            image = image_reader.read()
            
            if image.isNull():
                raise Exception(f"Failed to load image: {image_reader.errorString()}")
            
            # 发送图像加载完成信号
            self.image_loaded.emit(image)
        
        except Exception as e:
            # 发送图像错误信号
            self.image_error.emit(str(e))
    
    def save_image(self, image: QImage, image_path: str):
        """保存图像"""
        try:
            # 检查图像是否为空
            if image.isNull():
                raise Exception("Failed to save image: Image is null")
            
            # 确保保存目录存在
            save_dir = os.path.dirname(image_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 保存图像
            image_writer = QImageWriter(image_path)
            if not image_writer.write(image):
                raise Exception(f"Failed to save image: {image_writer.errorString()}")
            
            # 发送图像保存完成信号
            self.image_saved.emit(image_path)
        
        except Exception as e:
            # 发送图像错误信号
            self.image_error.emit(str(e))
    
    def get_image_size(self, image_path: str) -> tuple:
        """获取图像大小"""
        try:
            # 检查图像文件是否存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # 获取图像大小
            image_reader = QImageReader(image_path)
            size = image_reader.size()
            
            if size.isValid():
                return (size.width(), size.height())
            else:
                raise Exception(f"Failed to get image size: {image_reader.errorString()}")
        
        except Exception as e:
            # 发送图像错误信号
            self.image_error.emit(str(e))
            return (0, 0)
    
    def get_supported_formats(self) -> list:
        """获取支持的图像格式"""
        return QImageReader.supportedImageFormats()
    
    def get_supported_write_formats(self) -> list:
        """获取支持的图像写入格式"""
        return QImageWriter.supportedImageFormats()