# ===============================================
# =============== 内存池与纹理缓存 ===============
# ===============================================

import numpy as np
import cv2
from typing import Dict, List, Tuple
from PySide2.QtCore import QMutex


class MemoryPool:
    """可复用的内存池，用于管理GPU/CPU buffer"""
    
    def __init__(self):
        self._cpu_pool: Dict[Tuple[int, int, int], List[np.ndarray]] = {}
        self._gpu_pool: Dict[Tuple[int, int, int], List[cv2.cuda.GpuMat]] = {}
        self._mutex = QMutex()
        
        # 统计信息
        self._total_allocations = 0
        self._total_reuses = 0
    
    def get_cpu_buffer(self, shape: Tuple[int, int, int], dtype: np.dtype = np.uint8) -> np.ndarray:
        """
        从内存池获取CPU buffer
        
        Args:
            shape: buffer的形状 (height, width, channels)
            dtype: buffer的数据类型
            
        Returns:
            CPU buffer
        """
        self._mutex.lock()
        
        key = (shape[0], shape[1], shape[2])
        
        if key in self._cpu_pool and len(self._cpu_pool[key]) > 0:
            # 从池子里复用
            buffer = self._cpu_pool[key].pop()
            self._total_reuses += 1
            self._mutex.unlock()
            return buffer
        else:
            # 新分配
            buffer = np.zeros(shape, dtype=dtype)
            self._total_allocations += 1
            self._mutex.unlock()
            return buffer
    
    def get_gpu_buffer(self, shape: Tuple[int, int, int], dtype: int = cv2.CV_8UC3) -> cv2.cuda.GpuMat:
        """
        从内存池获取GPU buffer
        
        Args:
            shape: buffer的形状 (height, width, channels)
            dtype: buffer的数据类型 (OpenCV类型)
            
        Returns:
            GPU buffer (GpuMat)
        """
        self._mutex.lock()
        
        key = (shape[0], shape[1], shape[2])
        
        if key in self._gpu_pool and len(self._gpu_pool[key]) > 0:
            # 从池子里复用
            buffer = self._gpu_pool[key].pop()
            self._total_reuses += 1
            self._mutex.unlock()
            return buffer
        else:
            # 新分配
            try:
                buffer = cv2.cuda.GpuMat(shape[0], shape[1], dtype)
            except Exception as e:
                from umi_log import logger
                logger.error(f"分配GPU buffer失败: {e}")
                raise
            
            self._total_allocations += 1
            self._mutex.unlock()
            return buffer
    
    def release_cpu_buffer(self, buffer: np.ndarray):
        """
        将CPU buffer释放回内存池
        
        Args:
            buffer: 要释放的CPU buffer
        """
        if buffer is None:
            return
        
        self._mutex.lock()
        
        shape = buffer.shape
        if len(shape) != 3:
            # 只管理3D数组 (height, width, channels)
            self._mutex.unlock()
            return
        
        key = (shape[0], shape[1], shape[2])
        
        if key not in self._cpu_pool:
            self._cpu_pool[key] = []
        
        # 清空buffer内容
        buffer.fill(0)
        
        self._cpu_pool[key].append(buffer)
        self._mutex.unlock()
    
    def release_gpu_buffer(self, buffer: cv2.cuda.GpuMat):
        """
        将GPU buffer释放回内存池
        
        Args:
            buffer: 要释放的GPU buffer (GpuMat)
        """
        if buffer is None:
            return
        
        self._mutex.lock()
        
        try:
            height, width = buffer.size()
            dtype = buffer.type()
            
            # 确定通道数
            if dtype == cv2.CV_8UC1:
                channels = 1
            elif dtype == cv2.CV_8UC3:
                channels = 3
            else:
                # 只管理常见的通道数
                self._mutex.unlock()
                return
            
            key = (height, width, channels)
            
            if key not in self._gpu_pool:
                self._gpu_pool[key] = []
            
            # 清空buffer内容
            buffer.setTo(cv2.cuda.GpuMat(height, width, dtype, (0, 0, 0)))
            
            self._gpu_pool[key].append(buffer)
            
        except Exception as e:
            from umi_log import logger
            logger.error(f"释放GPU buffer失败: {e}")
        
        self._mutex.unlock()
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取内存池的统计信息
        
        Returns:
            统计信息字典
        """
        self._mutex.lock()
        
        stats = {
            'total_allocations': self._total_allocations,
            'total_reuses': self._total_reuses,
            'cpu_pool_size': sum(len(buffers) for buffers in self._cpu_pool.values()),
            'gpu_pool_size': sum(len(buffers) for buffers in self._gpu_pool.values()),
        }
        
        # 计算复用率
        if self._total_allocations + self._total_reuses > 0:
            stats['reuse_rate'] = self._total_reuses / (self._total_allocations + self._total_reuses)
        else:
            stats['reuse_rate'] = 0.0
        
        self._mutex.unlock()
        return stats
    
    def clear(self):
        """清空内存池"""
        self._mutex.lock()
        
        self._cpu_pool.clear()
        self._gpu_pool.clear()
        
        # 重置统计信息
        self._total_allocations = 0
        self._total_reuses = 0
        
        self._mutex.unlock()


class TextureCache:
    """纹理缓存，用于加速图像的GPU处理"""
    
    def __init__(self, max_cache_size: int = 10):
        self._max_cache_size = max_cache_size
        self._cache: Dict[str, cv2.cuda.GpuMat] = {}
        self._usage_order: List[str] = []
        self._mutex = QMutex()
    
    def get_texture(self, key: str, image_np: np.ndarray = None) -> cv2.cuda.GpuMat:
        """
        从缓存获取纹理，如果不存在则创建
        
        Args:
            key: 纹理的唯一标识符
            image_np: 原始图像的numpy数组 (当缓存中不存在时使用)
            
        Returns:
            纹理的GPU Mat
        """
        self._mutex.lock()
        
        if key in self._cache:
            # 缓存命中
            texture = self._cache[key]
            
            # 更新使用顺序
            self._usage_order.remove(key)
            self._usage_order.append(key)
            
            self._mutex.unlock()
            return texture
        else:
            # 缓存未命中，创建新纹理
            if image_np is None:
                self._mutex.unlock()
                return None
            
            try:
                texture = cv2.cuda.GpuMat()
                texture.upload(image_np)
            except Exception as e:
                from umi_log import logger
                logger.error(f"创建纹理失败: {e}")
                self._mutex.unlock()
                return None
            
            # 检查缓存是否已满
            if len(self._cache) >= self._max_cache_size:
                # 移除最久未使用的纹理
                oldest_key = self._usage_order.pop(0)
                del self._cache[oldest_key]
            
            # 添加到缓存
            self._cache[key] = texture
            self._usage_order.append(key)
            
            self._mutex.unlock()
            return texture
    
    def release_texture(self, key: str):
        """
        从缓存中释放纹理
        
        Args:
            key: 纹理的唯一标识符
        """
        self._mutex.lock()
        
        if key in self._cache:
            del self._cache[key]
            if key in self._usage_order:
                self._usage_order.remove(key)
        
        self._mutex.unlock()
    
    def clear(self):
        """清空缓存"""
        self._mutex.lock()
        
        self._cache.clear()
        self._usage_order.clear()
        
        self._mutex.unlock()
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存的统计信息
        
        Returns:
            统计信息字典
        """
        self._mutex.lock()
        
        stats = {
            'cache_size': len(self._cache),
            'max_cache_size': self._max_cache_size,
        }
        
        self._mutex.unlock()
        return stats


# 全局内存池和纹理缓存实例
MemoryPoolGlobal = MemoryPool()
TextureCacheGlobal = TextureCache()
