# ===============================================
# =============== OCR 推理流水线优化 ===============
# ===============================================

import os
import time
import threading
from collections import deque
from typing import Dict, List, Tuple, Optional
import numpy as np

from umi_log import logger
from .config import get_config


class MemoryPool:
    """可复用的内存池与纹理缓存管理"""
    
    def __init__(self, max_buffers: int = None, buffer_size: int = None):
        """初始化内存池
        
        Args:
            max_buffers: 最大缓存的buffer数量
            buffer_size: 每个buffer的大小（字节）
        """
        config = get_config()
        self.max_buffers = max_buffers or config.MEMORY_POOL_MAX_BUFFERS
        self.buffer_size = buffer_size or config.MEMORY_POOL_BUFFER_SIZE
        self.free_buffers = deque()
        self.used_buffers = set()
        self.mutex = threading.Lock()
        
    def acquire(self, size: int = None) -> Optional[np.ndarray]:
        """获取一个内存buffer
        
        Args:
            size: 需要的buffer大小（字节）
            
        Returns:
            内存buffer，如果没有可用buffer且达到最大数量则返回None
        """
        with self.mutex:
            # 如果指定了size且大于默认buffer_size，则创建新的
            if size and size > self.buffer_size:
                buffer = np.zeros(size, dtype=np.uint8)
                self.used_buffers.add(buffer)
                return buffer
            
            # 尝试从空闲队列获取
            if self.free_buffers:
                buffer = self.free_buffers.popleft()
                self.used_buffers.add(buffer)
                return buffer
            
            # 如果没达到最大数量，创建新的
            if len(self.used_buffers) < self.max_buffers:
                buffer = np.zeros(self.buffer_size, dtype=np.uint8)
                self.used_buffers.add(buffer)
                return buffer
            
            return None
    
    def release(self, buffer: np.ndarray) -> None:
        """释放一个内存buffer回池
        
        Args:
            buffer: 要释放的buffer
        """
        with self.mutex:
            if buffer in self.used_buffers:
                self.used_buffers.remove(buffer)
                # 重置buffer内容
                buffer.fill(0)
                self.free_buffers.append(buffer)
    
    def clear(self) -> None:
        """清空内存池"""
        with self.mutex:
            self.free_buffers.clear()
            self.used_buffers.clear()


class TextureCache:
    """纹理缓存管理"""
    
    def __init__(self, max_cache_size: int = None):
        """初始化纹理缓存
        
        Args:
            max_cache_size: 最大缓存的纹理数量
        """
        config = get_config()
        self.max_cache_size = max_cache_size or config.TEXTURE_CACHE_MAX_SIZE
        self.cache = dict()  # key: image hash, value: (texture, timestamp)
        self.mutex = threading.Lock()
    
    def get(self, image_hash: str) -> Optional[object]:
        """获取缓存的纹理
        
        Args:
            image_hash: 图片的哈希值
            
        Returns:
            缓存的纹理对象，如果不存在则返回None
        """
        with self.mutex:
            if image_hash in self.cache:
                texture, _ = self.cache[image_hash]
                # 更新时间戳
                self.cache[image_hash] = (texture, time.time())
                return texture
            return None
    
    def put(self, image_hash: str, texture: object) -> None:
        """添加纹理到缓存
        
        Args:
            image_hash: 图片的哈希值
            texture: 纹理对象
        """
        with self.mutex:
            # 如果缓存已满，移除最旧的
            if len(self.cache) >= self.max_cache_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
            
            self.cache[image_hash] = (texture, time.time())
    
    def clear(self) -> None:
        """清空纹理缓存"""
        with self.mutex:
            self.cache.clear()


class InputSlicer:
    """输入切片编排器，将大图片分割为多个区域并行处理"""
    
    def __init__(self, max_segments: int = None):
        """初始化切片编排器
        
        Args:
            max_segments: 最大同时处理的段数
        """
        config = get_config()
        self.max_segments = max_segments or config.INPUT_SLICER_MAX_SEGMENTS
    
    def slice_image(self, image_path: str) -> List[Dict]:
        """将图片分割为多个处理区域
        
        Args:
            image_path: 图片路径
            
        Returns:
            区域列表，每个区域包含路径和坐标信息
        """
        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            img.close()
            
            config = get_config()
            
            # 根据图片尺寸决定分割策略
            if width * height < config.INPUT_SLICER_MIN_AREA:  # 小于阈值，不分割
                return [{"path": image_path, "coords": None}]
            
            # 计算最佳分割段数（最多max_segments）
            area = width * height
            segments = min(self.max_segments, max(2, int(area / (512 * 512)) + 1))
            
            # 按高度均匀分割
            slice_height = height // segments
            regions = []
            
            for i in range(segments):
                y_start = i * slice_height
                y_end = (i + 1) * slice_height if i < segments - 1 else height
                
                regions.append({
                    "path": image_path,
                    "coords": (0, y_start, width, y_end),
                    "segment_index": i,
                    "total_segments": segments
                })
            
            return regions
            
        except Exception as e:
            logger.error(f"图片分割失败: {image_path}, error: {e}")
            return [{"path": image_path, "coords": None}]
    
    def merge_results(self, segment_results: List[Dict]) -> Dict:
        """合并多个区域的识别结果
        
        Args:
            segment_results: 各区域的识别结果
            
        Returns:
            合并后的结果
        """
        if not segment_results:
            return {"code": 101, "data": ""}
        
        # 检查是否所有结果都成功
        all_success = all(res.get("code") == 100 for res in segment_results)
        if not all_success:
            return {"code": 101, "data": "部分区域识别失败"}
        
        # 合并文本块
        merged_data = []
        for res in segment_results:
            if res.get("data"):
                # 调整坐标（如果有分割坐标）
                coords = res.get("segment_coords")
                if coords:
                    y_offset = coords[1]  # y_start
                    for block in res["data"]:
                        # 调整文本块的坐标
                        adjusted_block = block.copy()
                        if "box" in adjusted_block:
                            adjusted_block["box"] = [
                                [x, y + y_offset] for x, y in adjusted_block["box"]
                            ]
                        merged_data.append(adjusted_block)
                else:
                    merged_data.extend(res["data"])
        
        # 计算平均置信度
        if merged_data:
            total_score = sum(block.get("score", 0) for block in merged_data)
            avg_score = total_score / len(merged_data)
        else:
            avg_score = 0
        
        return {
            "code": 100,
            "data": merged_data,
            "score": avg_score,
            "segmented": True,
            "total_segments": len(segment_results)
        }


class TaskScheduler:
    """任务调度器，优化任务分配策略"""
    
    def __init__(self, small_image_threshold: int = None):
        """初始化任务调度器
        
        Args:
            small_image_threshold: 小图片的像素阈值（小于此值的图片视为小图片）
        """
        config = get_config()
        self.small_image_threshold = small_image_threshold or config.TASK_SCHEDULER_SMALL_IMAGE_THRESHOLD
        self.large_image_queue = deque()
        self.small_image_queue = deque()
        self.mutex = threading.Lock()
        self.condition = threading.Condition(self.mutex)
    
    def add_task(self, task: Dict) -> None:
        """添加任务到相应的队列
        
        Args:
            task: 任务信息字典
        """
        with self.mutex:
            # 估算图片大小（根据路径或已有的尺寸信息）
            image_size = self._estimate_image_size(task)
            
            if image_size and image_size > self.small_image_threshold:
                self.large_image_queue.append(task)
                logger.debug(f"添加大图片任务: {task.get('path', 'unknown')}, size: {image_size}")
            else:
                self.small_image_queue.append(task)
                logger.debug(f"添加小图片任务: {task.get('path', 'unknown')}, size: {image_size}")
            
            self.condition.notify()
    
    def get_task(self, prefer_small: bool = False) -> Optional[Dict]:
        """获取下一个任务
        
        Args:
            prefer_small: 是否优先获取小图片任务
            
        Returns:
            任务字典，如果没有任务则返回None
        """
        with self.mutex:
            while True:
                # 优先处理小图片以减少阻塞
                if prefer_small and self.small_image_queue:
                    return self.small_image_queue.popleft()
                
                # 均衡处理
                if self.large_image_queue and self.small_image_queue:
                    # 交替获取
                    return self.small_image_queue.popleft() if time.time() % 2 < 1 else self.large_image_queue.popleft()
                
                # 获取非空队列的任务
                if self.small_image_queue:
                    return self.small_image_queue.popleft()
                if self.large_image_queue:
                    return self.large_image_queue.popleft()
                
                # 没有任务，等待
                self.condition.wait()
    
    def _estimate_image_size(self, task: Dict) -> Optional[int]:
        """估算图片大小（像素数）
        
        Args:
            task: 任务信息字典
            
        Returns:
            图片大小（像素数），如果无法估算则返回None
        """
        # 如果任务中已有尺寸信息
        if "width" in task and "height" in task:
            return task["width"] * task["height"]
        
        # 尝试从路径获取图片尺寸
        path = task.get("path")
        if path and os.path.exists(path):
            try:
                from PIL import Image
                with Image.open(path) as img:
                    return img.width * img.height
            except Exception:
                pass
        
        return None
    
    def clear(self) -> None:
        """清空所有任务队列"""
        with self.mutex:
            self.large_image_queue.clear()
            self.small_image_queue.clear()


class ThroughputMonitor:
    """吞吐监测器，记录和分析OCR处理性能"""
    
    def __init__(self):
        """初始化吞吐监测器"""
        self.config = get_config()
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "total_processing_time": 0.0,
            "total_waiting_time": 0.0,
            "peak_memory": 0.0,  # MB
            "peak_vram": 0.0,    # MB
            "batch_metrics": []  # 每批次的详细信息
        }
        self.mutex = threading.Lock()
        self.start_time = time.time()
    
    def record_batch(self, batch_size: int, processing_time: float, 
                    waiting_time: float, memory_usage: float, 
                    vram_usage: float = 0.0) -> None:
        """记录一批次的处理信息
        
        Args:
            batch_size: 批次大小
            processing_time: 处理时间（秒）
            waiting_time: 等待时间（秒）
            memory_usage: 内存使用量（MB）
            vram_usage: 显存使用量（MB，可选）
        """
        with self.mutex:
            self.metrics["total_tasks"] += batch_size
            self.metrics["completed_tasks"] += batch_size
            self.metrics["total_processing_time"] += processing_time
            self.metrics["total_waiting_time"] += waiting_time
            
            # 更新峰值内存
            if memory_usage > self.metrics["peak_memory"]:
                self.metrics["peak_memory"] = memory_usage
            
            # 更新峰值显存
            if vram_usage > self.metrics["peak_vram"]:
                self.metrics["peak_vram"] = vram_usage
            
            # 记录批次详细信息
            batch_metric = {
                "timestamp": time.time(),
                "batch_size": batch_size,
                "processing_time": processing_time,
                "waiting_time": waiting_time,
                "memory_usage": memory_usage,
                "vram_usage": vram_usage,
                "throughput": batch_size / processing_time if processing_time > 0 else 0
            }
            self.metrics["batch_metrics"].append(batch_metric)
            
            # 保留最近配置数量的批次数据
            max_batches = self.config.THROUGHPUT_MONITOR_MAX_BATCHES
            if len(self.metrics["batch_metrics"]) > max_batches:
                self.metrics["batch_metrics"] = self.metrics["batch_metrics"][-max_batches:]
    
    def get_metrics(self) -> Dict:
        """获取当前性能指标
        
        Returns:
            性能指标字典
        """
        with self.mutex:
            metrics = self.metrics.copy()
            
            # 计算平均指标
            if metrics["completed_tasks"] > 0:
                metrics["avg_processing_time"] = metrics["total_processing_time"] / metrics["completed_tasks"]
                metrics["avg_waiting_time"] = metrics["total_waiting_time"] / metrics["completed_tasks"]
            else:
                metrics["avg_processing_time"] = 0.0
                metrics["avg_waiting_time"] = 0.0
            
            # 计算总体吞吐率
            elapsed_time = time.time() - self.start_time
            metrics["overall_throughput"] = metrics["completed_tasks"] / elapsed_time if elapsed_time > 0 else 0
            
            return metrics
    
    def reset(self) -> None:
        """重置监测器"""
        with self.mutex:
            self.metrics = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "total_processing_time": 0.0,
                "total_waiting_time": 0.0,
                "peak_memory": 0.0,
                "peak_vram": 0.0,
                "batch_metrics": []
            }
            self.start_time = time.time()


# 全局优化组件实例
global_memory_pool = MemoryPool()
global_texture_cache = TextureCache()
global_task_scheduler = TaskScheduler()
global_throughput_monitor = ThroughputMonitor()


def get_memory_pool() -> MemoryPool:
    """获取全局内存池实例"""
    return global_memory_pool


def get_texture_cache() -> TextureCache:
    """获取全局纹理缓存实例"""
    return global_texture_cache


def get_task_scheduler() -> TaskScheduler:
    """获取全局任务调度器实例"""
    return global_task_scheduler


def get_throughput_monitor() -> ThroughputMonitor:
    """获取全局吞吐监测器实例"""
    return global_throughput_monitor


def optimize_ocr_pipeline():
    """初始化OCR推理流水线优化"""
    logger.info("OCR推理流水线优化模块已初始化")
    logger.info(f"内存池配置: max_buffers={global_memory_pool.max_buffers}, buffer_size={global_memory_pool.buffer_size}")
    logger.info(f"纹理缓存配置: max_cache_size={global_texture_cache.max_cache_size}")
    logger.info(f"任务调度器配置: small_image_threshold={global_task_scheduler.small_image_threshold}")
