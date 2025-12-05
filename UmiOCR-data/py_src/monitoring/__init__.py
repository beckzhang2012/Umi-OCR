"""
性能监测模块

提供实时性能监测功能，包括：
- 处理时间统计
- 内存和显存使用监测
- 线程利用率统计
- 任务吞吐量计算
- 错误率统计
"""

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetric,
    BatchInfo,
    MonitorConfig,
    MetricType,
    get_performance_monitor,
    set_monitor_config,
    global_performance_monitor
)

__all__ = [
    'PerformanceMonitor',
    'PerformanceMetric',
    'BatchInfo',
    'MonitorConfig',
    'MetricType',
    'get_performance_monitor',
    'set_monitor_config',
    'global_performance_monitor'
]

__version__ = '1.0.0'
