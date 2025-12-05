# ===============================================
# =============== OCR 推理流水线优化 ===============
# ===============================================

"""OCR推理流水线优化模块

该模块提供了一系列优化组件，旨在提高OCR处理的吞吐率和资源利用率：
- MemoryPool: 可复用的内存池与纹理缓存管理
- TextureCache: 纹理缓存管理
- InputSlicer: 输入切片编排器，将大图片分割为多个区域并行处理
- TaskScheduler: 任务调度器，优化任务分配策略
- ThroughputMonitor: 吞吐监测器，记录和分析OCR处理性能

所有组件都支持通过配置系统进行动态调参。
"""

from .config import OptimizationConfig, get_config, update_config
from .ocr_optimization import (
    MemoryPool,
    TextureCache,
    InputSlicer,
    TaskScheduler,
    ThroughputMonitor,
    get_memory_pool,
    get_texture_cache,
    get_task_scheduler,
    get_throughput_monitor,
    optimize_ocr_pipeline
)

__all__ = [
    # 配置相关
    'OptimizationConfig',
    'get_config',
    'update_config',
    
    # 优化组件类
    'MemoryPool',
    'TextureCache',
    'InputSlicer',
    'TaskScheduler',
    'ThroughputMonitor',
    
    # 全局实例获取函数
    'get_memory_pool',
    'get_texture_cache',
    'get_task_scheduler',
    'get_throughput_monitor',
    
    # 初始化函数
    'optimize_ocr_pipeline'
]

# 模块版本信息
__version__ = '1.0.0'
__author__ = 'Umi-OCR Team'
__description__ = 'OCR推理流水线优化模块'

# 默认初始化优化模块
optimize_ocr_pipeline()
