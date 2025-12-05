# ===============================================
# =============== 切片编排器 ===================
# ===============================================

import cv2
import numpy as np
from typing import List, Tuple, Dict


class SliceOrchestrator:
    """对OCR输入进行切片编排，支持单任务内分片并行"""
    
    def __init__(self, max_slices: int = 6):
        self.max_slices = max_slices
        
    def slice_image(self, image_path: str = None, image_bytes: bytes = None, 
                    image_base64: str = None, image_np: np.ndarray = None) -> List[Dict]:
        """
        对输入图像进行切片
        
        Args:
            image_path: 图像文件路径
            image_bytes: 图像字节数据
            image_base64: 图像base64编码
            image_np: 图像numpy数组
            
        Returns:
            切片列表，每个切片包含：
            - image_np: 切片的numpy数组
            - offset: 切片在原图中的偏移量 (x, y)
        """
        # 加载图像
        image = self._load_image(image_path, image_bytes, image_base64, image_np)
        if image is None:
            return []
        
        # 计算切片方案
        height, width = image.shape[:2]
        slices = self._calculate_slice方案(height, width)
        
        # 生成切片
        image_slices = []
        for (x1, y1, x2, y2) in slices:
            slice_np = image[y1:y2, x1:x2]
            if slice_np.size > 0:
                image_slices.append({
                    'image_np': slice_np,
                    'offset': (x1, y1)
                })
        
        return image_slices
    
    def merge_results(self, slice_results: List[Dict], image_shape: Tuple[int, int]) -> List[Dict]:
        """
        合并切片的OCR结果
        
        Args:
            slice_results: 切片的OCR结果列表
            image_shape: 原图的形状 (height, width)
            
        Returns:
            合并后的OCR结果
        """
        merged_results = []
        
        for slice_res in slice_results:
            if slice_res.get('code') != 100:
                continue
            
            offset = slice_res.get('offset', (0, 0))
            slice_data = slice_res.get('data', [])
            
            for item in slice_data:
                # 调整坐标到原图坐标系
                new_item = item.copy()
                if 'box' in new_item:
                    # box格式: [x1, y1, x2, y2, x3, y3, x4, y4]
                    new_box = [
                        new_item['box'][0] + offset[0],
                        new_item['box'][1] + offset[1],
                        new_item['box'][2] + offset[0],
                        new_item['box'][3] + offset[1],
                        new_item['box'][4] + offset[0],
                        new_item['box'][5] + offset[1],
                        new_item['box'][6] + offset[0],
                        new_item['box'][7] + offset[1],
                    ]
                    new_item['box'] = new_box
                
                merged_results.append(new_item)
        
        return merged_results
    
    def _load_image(self, image_path: str = None, image_bytes: bytes = None, 
                    image_base64: str = None, image_np: np.ndarray = None) -> np.ndarray:
        """加载图像"""
        if image_np is not None:
            return image_np
        
        try:
            if image_path is not None:
                return cv2.imread(image_path)
            
            if image_bytes is not None:
                nparr = np.frombuffer(image_bytes, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image_base64 is not None:
                import base64
                img_data = base64.b64decode(image_base64)
                nparr = np.frombuffer(img_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        except Exception as e:
            from umi_log import logger
            logger.error(f"加载图像失败: {e}")
            return None
        
        return None
    
    def _calculate_slice方案(self, height: int, width: int) -> List[Tuple[int, int, int, int]]:
        """
        计算图像的切片方案
        
        Args:
            height: 图像高度
            width: 图像宽度
            
        Returns:
            切片列表，每个切片包含 (x1, y1, x2, y2)
        """
        # 计算切片大小
        min_slice_size = 512  # 最小切片大小
        
        # 计算水平和垂直方向的切片数
        h_slices = max(1, int(width / min_slice_size))
        v_slices = max(1, int(height / min_slice_size))
        
        # 确保总切片数不超过max_slices
        total_slices = h_slices * v_slices
        while total_slices > self.max_slices:
            if h_slices > v_slices:
                h_slices -= 1
            else:
                v_slices -= 1
            total_slices = h_slices * v_slices
            
            if h_slices == 1 and v_slices == 1:
                break
        
        # 计算每个切片的大小
        slice_width = width // h_slices
        slice_height = height // v_slices
        
        # 生成切片
        slices = []
        for i in range(h_slices):
            for j in range(v_slices):
                x1 = i * slice_width
                y1 = j * slice_height
                x2 = (i + 1) * slice_width if (i + 1) < h_slices else width
                y2 = (j + 1) * slice_height if (j + 1) < v_slices else height
                
                slices.append((x1, y1, x2, y2))
        
        return slices


# 全局切片编排器实例
SliceOrchestratorGlobal = SliceOrchestrator()
