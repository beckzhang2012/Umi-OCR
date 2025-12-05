import os
import tempfile
from typing import Optional
from umi_log import logger
from PySide2.QtGui import QImage, QPainter, QPixmap

class ThumbnailGenerator:
    """缩略图生成器"""
    
    def __init__(self):
        self.thumbnail_size = (120, 90)  # 默认缩略图尺寸
        self.temp_dir = tempfile.TemporaryDirectory(prefix="umi_thumbnail_")
        
    def generate_thumbnail(self, image_path: str) -> str:
        """从图片文件路径生成缩略图
        
        Args:
            image_path: 原图文件路径
            
        Returns:
            缩略图文件路径，如果生成失败则返回原图路径
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"原图不存在: {image_path}")
                return image_path
            
            # 加载图片
            image = QImage(image_path)
            if image.isNull():
                logger.warning(f"无法加载图片: {image_path}")
                return image_path
            
            # 生成缩略图
            thumbnail = image.scaled(
                self.thumbnail_size[0],
                self.thumbnail_size[1],
                aspectRatioMode=1,  # 保持比例
                transformMode=1       # 平滑转换
            )
            
            # 保存缩略图到临时目录
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            thumbnail_path = os.path.join(
                self.temp_dir.name,
                f"{name}_thumbnail{ext}"
            )
            
            if thumbnail.save(thumbnail_path):
                logger.debug(f"缩略图已生成: {thumbnail_path}")
                return thumbnail_path
            else:
                logger.warning(f"无法保存缩略图: {thumbnail_path}")
                return image_path
                
        except Exception as e:
            logger.error(f"生成缩略图失败: {str(e)}")
            return image_path

# 单例模式
thumbnail_generator = ThumbnailGenerator()