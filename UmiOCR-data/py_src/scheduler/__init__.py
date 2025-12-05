# ===============================================
# =============== 任务调度器模块 ===============
# ===============================================

"""
任务调度器模块，提供智能任务调度策略，支持基于图片尺寸的线程池分配和优先级调度。
"""

from .task_scheduler import (
    TaskScheduler,
    SchedulerConfig,
    TaskType,
    TaskPriority,
    TaskInfo,
    get_task_scheduler,
    set_scheduler_config,
    global_task_scheduler
)

__all__ = [
    'TaskScheduler',
    'SchedulerConfig',
    'TaskType',
    'TaskPriority',
    'TaskInfo',
    'get_task_scheduler',
    'set_scheduler_config',
    'global_task_scheduler'
]

__version__ = '1.0.0'
