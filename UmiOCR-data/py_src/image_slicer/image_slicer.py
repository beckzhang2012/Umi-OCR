# ===============================================
# =============== 图片切片编排模块 ===============
# ===============================================

"""
图片切片编排模块，支持将大图片自动分割为多个小切片，
实现单任务内的并行处理，最多支持6段同时处理。
"""

import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class SliceStrategy(Enum):
    """切片策略枚举"""
    AUTO = "auto"          # 自动策略（根据图片尺寸智能选择）
    HORIZONTAL = "horizontal"  # 水平切片
    VERTICAL = "vertical"    # 垂直切片
    GRID = "grid"         # 网格切片

@dataclass
class SliceConfig:
    """切片配置"""
    max_slice_count: int = 6          # 最大切片数量
    min_slice_size: Tuple[int, int] = (512, 512)  # 最小切片尺寸
    overlap_ratio: float = 0.1        # 重叠区域比例
    strategy: SliceStrategy = SliceStrategy.AUTO
    enable_slicing: bool = True       # 是否启用切片

@dataclass
class SliceInfo:
    """切片信息"""
    x: int               # 切片左上角X坐标
    y: int               # 切片左上角Y坐标
    width: int           # 切片宽度
    height: int          # 切片高度
    slice_index: int     # 切片索引
    total_slices: int    # 总切片数
    original_width: int  # 原始图片宽度
    original_height: int # 原始图片高度

class ImageSlicer:
    """图片切片器"""
    
    def __init__(self, config: Optional[SliceConfig] = None):
        self.config = config or SliceConfig()
        
    def should_slice(self, image_width: int, image_height: int) -> bool:
        """判断是否需要对图片进行切片"""
        if not self.config.enable_slicing:
            return False
            
        # 如果图片尺寸小于最小切片尺寸，则不需要切片
        if image_width <= self.config.min_slice_size[0] and \
           image_height <= self.config.min_slice_size[1]:
            return False
            
        return True
        
    def calculate_slices(self, image_width: int, image_height: int) -> List[SliceInfo]:
        """计算切片信息"""
        if not self.should_slice(image_width, image_height):
            return [SliceInfo(
                x=0, y=0, 
                width=image_width, height=image_height,
                slice_index=0, total_slices=1,
                original_width=image_width, original_height=image_height
            )]
            
        # 根据策略选择切片方式
        if self.config.strategy == SliceStrategy.AUTO:
            strategy = self._auto_select_strategy(image_width, image_height)
        else:
            strategy = self.config.strategy
            
        if strategy == SliceStrategy.HORIZONTAL:
            return self._calculate_horizontal_slices(image_width, image_height)
        elif strategy == SliceStrategy.VERTICAL:
            return self._calculate_vertical_slices(image_width, image_height)
        elif strategy == SliceStrategy.GRID:
            return self._calculate_grid_slices(image_width, image_height)
        else:
            return self._calculate_horizontal_slices(image_width, image_height)
            
    def _auto_select_strategy(self, width: int, height: int) -> SliceStrategy:
        """自动选择切片策略"""
        aspect_ratio = width / height
        
        # 宽高比差异较大时选择对应方向的切片
        if aspect_ratio > 2.0:
            return SliceStrategy.VERTICAL  # 宽图
        elif aspect_ratio < 0.5:
            return SliceStrategy.HORIZONTAL  # 高图
        else:
            return SliceStrategy.GRID  # 正方形或接近正方形
            
    def _calculate_horizontal_slices(self, width: int, height: int) -> List[SliceInfo]:
        """计算水平切片"""
        slices = []
        
        # 计算需要的切片数量
        slice_count = min(
            self.config.max_slice_count,
            math.ceil(height / self.config.min_slice_size[1])
        )
        
        if slice_count <= 1:
            return [SliceInfo(
                x=0, y=0, 
                width=width, height=height,
                slice_index=0, total_slices=1,
                original_width=width, original_height=height
            )]
            
        # 计算切片高度和重叠区域
        slice_height = height / slice_count
        overlap = int(slice_height * self.config.overlap_ratio)
        
        for i in range(slice_count):
            y = int(i * slice_height - overlap)
            current_slice_height = int(slice_height + 2 * overlap)
            
            # 处理边界情况
            if i == 0:
                y = 0
                current_slice_height = int(slice_height + overlap)
            elif i == slice_count - 1:
                current_slice_height = int(height - y)
                
            # 确保不超出图片范围
            if y + current_slice_height > height:
                current_slice_height = height - y
                
            slices.append(SliceInfo(
                x=0, y=y,
                width=width, height=current_slice_height,
                slice_index=i, total_slices=slice_count,
                original_width=width, original_height=height
            ))
            
        return slices
        
    def _calculate_vertical_slices(self, width: int, height: int) -> List[SliceInfo]:
        """计算垂直切片"""
        slices = []
        
        # 计算需要的切片数量
        slice_count = min(
            self.config.max_slice_count,
            math.ceil(width / self.config.min_slice_size[0])
        )
        
        if slice_count <= 1:
            return [SliceInfo(
                x=0, y=0, 
                width=width, height=height,
                slice_index=0, total_slices=1,
                original_width=width, original_height=height
            )]
            
        # 计算切片宽度和重叠区域
        slice_width = width / slice_count
        overlap = int(slice_width * self.config.overlap_ratio)
        
        for i in range(slice_count):
            x = int(i * slice_width - overlap)
            current_slice_width = int(slice_width + 2 * overlap)
            
            # 处理边界情况
            if i == 0:
                x = 0
                current_slice_width = int(slice_width + overlap)
            elif i == slice_count - 1:
                current_slice_width = int(width - x)
                
            # 确保不超出图片范围
            if x + current_slice_width > width:
                current_slice_width = width - x
                
            slices.append(SliceInfo(
                x=x, y=0,
                width=current_slice_width, height=height,
                slice_index=i, total_slices=slice_count,
                original_width=width, original_height=height
            ))
            
        return slices
        
    def _calculate_grid_slices(self, width: int, height: int) -> List[SliceInfo]:
        """计算网格切片"""
        slices = []
        
        # 计算需要的切片数量（尽可能接近正方形）
        area = width * height
        slice_area = self.config.min_slice_size[0] * self.config.min_slice_size[1]
        slice_count = min(
            self.config.max_slice_count,
            math.ceil(area / slice_area)
        )
        
        if slice_count <= 1:
            return [SliceInfo(
                x=0, y=0, 
                width=width, height=height,
                slice_index=0, total_slices=1,
                original_width=width, original_height=height
            )]
            
        # 计算网格行列数
        cols = math.ceil(math.sqrt(slice_count))
        rows = math.ceil(slice_count / cols)
        
        # 计算切片尺寸和重叠区域
        slice_width = width / cols
        slice_height = height / rows
        overlap_x = int(slice_width * self.config.overlap_ratio)
        overlap_y = int(slice_height * self.config.overlap_ratio)
        
        index = 0
        for row in range(rows):
            for col in range(cols):
                if index >= slice_count:
                    break
                    
                x = int(col * slice_width - overlap_x)
                y = int(row * slice_height - overlap_y)
                current_slice_width = int(slice_width + 2 * overlap_x)
                current_slice_height = int(slice_height + 2 * overlap_y)
                
                # 处理边界情况
                if col == 0:
                    x = 0
                    current_slice_width = int(slice_width + overlap_x)
                elif col == cols - 1:
                    current_slice_width = int(width - x)
                    
                if row == 0:
                    y = 0
                    current_slice_height = int(slice_height + overlap_y)
                elif row == rows - 1:
                    current_slice_height = int(height - y)
                    
                # 确保不超出图片范围
                if x + current_slice_width > width:
                    current_slice_width = width - x
                if y + current_slice_height > height:
                    current_slice_height = height - y
                    
                slices.append(SliceInfo(
                    x=x, y=y,
                    width=current_slice_width, height=current_slice_height,
                    slice_index=index, total_slices=slice_count,
                    original_width=width, original_height=height
                ))
                
                index += 1
                
        return slices
        
    def slice_image(self, image, slice_info: SliceInfo):
        """对图片进行切片"""
        # 这里需要根据实际的图片类型实现切片逻辑
        # 支持 PIL.Image, QImage, numpy.ndarray 等
        
        if hasattr(image, 'crop'):  # PIL.Image
            return image.crop((
                slice_info.x, 
                slice_info.y, 
                slice_info.x + slice_info.width, 
                slice_info.y + slice_info.height
            ))
        elif hasattr(image, 'copy') and hasattr(image, 'rect'):  # QImage
            from PySide2.QtGui import QImage
            rect = image.rect()
            rect.setX(slice_info.x)
            rect.setY(slice_info.y)
            rect.setWidth(slice_info.width)
            rect.setHeight(slice_info.height)
            return image.copy(rect)
        elif hasattr(image, '__getitem__') and isinstance(image, (list, tuple)):  # numpy.ndarray
            return image[
                slice_info.y:slice_info.y + slice_info.height, 
                slice_info.x:slice_info.x + slice_info.width
            ]
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
            
    def merge_results(self, slice_results: List[Dict], slice_infos: List[SliceInfo]) -> Dict:
        """合并切片识别结果"""
        if not slice_results:
            return {"code": 101, "data": ""}
            
        # 假设所有结果都有相同的结构
        merged_result = slice_results[0].copy()
        merged_data = []
        
        for result, slice_info in zip(slice_results, slice_infos):
            if result.get("code") == 100 and "data" in result:
                # 调整坐标到原始图片坐标系
                for item in result["data"]:
                    if "box" in item:
                        # 调整边界框坐标
                        for i in range(0, len(item["box"]), 2):
                            item["box"][i] += slice_info.x
                            item["box"][i+1] += slice_info.y
                    if "x" in item and "y" in item:
                        # 调整点坐标
                        item["x"] += slice_info.x
                        item["y"] += slice_info.y
                    merged_data.append(item)
                    
        merged_result["data"] = merged_data
        
        # 重新计算平均置信度
        if merged_data:
            total_score = sum(item.get("score", 0) for item in merged_data)
            merged_result["score"] = total_score / len(merged_data)
        else:
            merged_result["code"] = 101
            merged_result["data"] = ""
            
        return merged_result

# 全局切片器实例
global_slicer = ImageSlicer()

def get_global_slicer() -> ImageSlicer:
    """获取全局切片器实例"""
    return global_slicer

def set_global_slicer_config(config: SliceConfig):
    """设置全局切片器配置"""
    global_slicer.config = config
