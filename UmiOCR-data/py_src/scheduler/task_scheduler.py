# ===============================================
# =============== 任务调度器 ===============
# ===============================================

"""
重新设计的任务调度策略，优先把大图与小图拆分到不同线程池，减少阻塞，并提供动态调参入口。
"""

import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import time
from PySide2.QtCore import QThreadPool, QRunnable
from imports.umi_log import logger

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1     # 低优先级（小图）
    MEDIUM = 2  # 中优先级（中图）
    HIGH = 3    # 高优先级（大图）
    CRITICAL = 4  # 紧急优先级

class TaskType(Enum):
    """任务类型枚举"""
    OCR_SMALL = "ocr_small"    # 小图OCR任务
    OCR_MEDIUM = "ocr_medium"  # 中图OCR任务
    OCR_LARGE = "ocr_large"    # 大图OCR任务
    PREPROCESS = "preprocess"  # 预处理任务
    POSTPROCESS = "postprocess"  # 后处理任务

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str               # 任务唯一标识
    task_type: TaskType        # 任务类型
    priority: TaskPriority     # 任务优先级
    task_func: Callable        # 任务函数
    args: tuple                # 位置参数
    kwargs: dict               # 关键字参数
    image_size: Optional[tuple] = None  # 图片尺寸 (width, height)
    created_time: float = None  # 创建时间
    start_time: Optional[float] = None  # 开始时间
    end_time: Optional[float] = None  # 结束时间
    is_completed: bool = False  # 是否完成
    result: Any = None          # 任务结果
    error: Optional[Exception] = None  # 错误信息

@dataclass
class SchedulerConfig:
    """调度器配置"""
    # 图片尺寸阈值（像素）
    small_image_threshold: int = 1024 * 1024  # 1MP 以下为小图
    medium_image_threshold: int = 4 * 1024 * 1024  # 4MP 以下为中图
    
    # 线程池配置
    small_thread_pool_size: int = 4    # 小图线程池大小
    medium_thread_pool_size: int = 3   # 中图线程池大小
    large_thread_pool_size: int = 2    # 大图线程池大小
    
    # 任务队列大小限制
    max_queue_size: int = 1000
    
    # 调度策略
    enable_priority_scheduling: bool = True  # 启用优先级调度
    enable_size_based_scheduling: bool = True  # 启用基于尺寸的调度
    enable_dynamic_thread_pool: bool = True  # 启用动态线程池调整
    
    # 动态调整参数
    load_monitor_interval: float = 5.0  # 负载监控间隔（秒）
    high_load_threshold: float = 0.8    # 高负载阈值
    low_load_threshold: float = 0.3     # 低负载阈值
    thread_pool_adjust_step: int = 1    # 线程池调整步长

class TaskRunnable(QRunnable):
    """任务可运行对象"""
    
    def __init__(self, task_info: TaskInfo, completion_callback: Optional[Callable] = None):
        super().__init__()
        self.task_info = task_info
        self.completion_callback = completion_callback
        self._lock = threading.Lock()
    
    def run(self):
        """执行任务"""
        with self._lock:
            self.task_info.start_time = time.time()
        
        try:
            # 执行任务
            result = self.task_info.task_func(*self.task_info.args, **self.task_info.kwargs)
            
            with self._lock:
                self.task_info.result = result
                self.task_info.is_completed = True
                self.task_info.end_time = time.time()
            
            # 执行完成回调
            if self.completion_callback:
                self.completion_callback(self.task_info)
                
        except Exception as e:
            with self._lock:
                self.task_info.error = e
                self.task_info.is_completed = True
                self.task_info.end_time = time.time()
            
            logger.error(f"任务 {self.task_info.task_id} 执行失败: {e}", exc_info=True)
            
            # 执行完成回调（即使出错）
            if self.completion_callback:
                self.completion_callback(self.task_info)

class TaskScheduler:
    """任务调度器"""
    
    _instance: Optional['TaskScheduler'] = None
    _lock: threading.Lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'TaskScheduler':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = TaskScheduler()
        return cls._instance
    
    def __init__(self):
        self.config = SchedulerConfig()
        self._thread_pools: Dict[TaskType, QThreadPool] = {}
        self._task_queues: Dict[TaskPriority, List[TaskInfo]] = {}
        self._task_id_counter: int = 0
        self._lock = threading.Lock()
        self._load_monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor: bool = False
        
        # 初始化线程池
        self._init_thread_pools()
        
        # 初始化任务队列
        for priority in TaskPriority:
            self._task_queues[priority] = []
            
        # 启动负载监控线程
        self._start_load_monitor()
    
    def _init_thread_pools(self):
        """初始化线程池"""
        # 小图线程池
        self._thread_pools[TaskType.OCR_SMALL] = QThreadPool()
        self._thread_pools[TaskType.OCR_SMALL].setMaxThreadCount(
            self.config.small_thread_pool_size
        )
        
        # 中图线程池
        self._thread_pools[TaskType.OCR_MEDIUM] = QThreadPool()
        self._thread_pools[TaskType.OCR_MEDIUM].setMaxThreadCount(
            self.config.medium_thread_pool_size
        )
        
        # 大图线程池
        self._thread_pools[TaskType.OCR_LARGE] = QThreadPool()
        self._thread_pools[TaskType.OCR_LARGE].setMaxThreadCount(
            self.config.large_thread_pool_size
        )
        
        # 预处理线程池
        self._thread_pools[TaskType.PREPROCESS] = QThreadPool()
        self._thread_pools[TaskType.PREPROCESS].setMaxThreadCount(2)
        
        # 后处理线程池
        self._thread_pools[TaskType.POSTPROCESS] = QThreadPool()
        self._thread_pools[TaskType.POSTPROCESS].setMaxThreadCount(2)
    
    def _start_load_monitor(self):
        """启动负载监控线程"""
        if not self.config.enable_dynamic_thread_pool:
            return
            
        self._stop_monitor = False
        self._load_monitor_thread = threading.Thread(
            target=self._load_monitor_loop, 
            daemon=True
        )
        self._load_monitor_thread.start()
    
    def _load_monitor_loop(self):
        """负载监控循环"""
        while not self._stop_monitor:
            time.sleep(self.config.load_monitor_interval)
            self._adjust_thread_pool_sizes()
    
    def _adjust_thread_pool_sizes(self):
        """动态调整线程池大小"""
        with self._lock:
            for task_type, thread_pool in self._thread_pools.items():
                active_count = thread_pool.activeThreadCount()
                max_count = thread_pool.maxThreadCount()
                load = active_count / max_count if max_count > 0 else 0
                
                # 根据负载调整线程池大小
                if load > self.config.high_load_threshold:
                    # 高负载，增加线程数
                    new_size = max_count + self.config.thread_pool_adjust_step
                    thread_pool.setMaxThreadCount(new_size)
                    logger.debug(
                        f"{task_type.value} 线程池负载过高 ({load:.2f})，调整大小: {max_count} -> {new_size}"
                    )
                elif load < self.config.low_load_threshold and max_count > 1:
                    # 低负载，减少线程数
                    new_size = max_count - self.config.thread_pool_adjust_step
                    thread_pool.setMaxThreadCount(new_size)
                    logger.debug(
                        f"{task_type.value} 线程池负载过低 ({load:.2f})，调整大小: {max_count} -> {new_size}"
                    )
    
    def _determine_task_type(self, image_size: Optional[tuple]) -> TaskType:
        """根据图片尺寸确定任务类型"""
        if not image_size or not self.config.enable_size_based_scheduling:
            return TaskType.OCR_MEDIUM
            
        width, height = image_size
        pixels = width * height
        
        if pixels < self.config.small_image_threshold:
            return TaskType.OCR_SMALL
        elif pixels < self.config.medium_image_threshold:
            return TaskType.OCR_MEDIUM
        else:
            return TaskType.OCR_LARGE
    
    def _determine_priority(self, task_type: TaskType) -> TaskPriority:
        """根据任务类型确定优先级"""
        if not self.config.enable_priority_scheduling:
            return TaskPriority.MEDIUM
            
        priority_map = {
            TaskType.OCR_SMALL: TaskPriority.LOW,
            TaskType.OCR_MEDIUM: TaskPriority.MEDIUM,
            TaskType.OCR_LARGE: TaskPriority.HIGH,
            TaskType.PREPROCESS: TaskPriority.MEDIUM,
            TaskType.POSTPROCESS: TaskPriority.MEDIUM
        }
        return priority_map.get(task_type, TaskPriority.MEDIUM)
    
    def submit_task(
        self, 
        task_func: Callable, 
        *args, 
        image_size: Optional[tuple] = None,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        completion_callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """提交任务"""
        with self._lock:
            # 生成任务ID
            self._task_id_counter += 1
            task_id = f"task_{self._task_id_counter:08d}"
            
            # 确定任务类型
            if not task_type:
                task_type = self._determine_task_type(image_size)
            
            # 确定优先级
            if not priority:
                priority = self._determine_priority(task_type)
            
            # 创建任务信息
            task_info = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                priority=priority,
                task_func=task_func,
                args=args,
                kwargs=kwargs,
                image_size=image_size,
                created_time=time.time()
            )
            
            # 检查队列大小
            total_tasks = sum(len(queue) for queue in self._task_queues.values())
            if total_tasks >= self.config.max_queue_size:
                raise Exception(f"任务队列已满（{total_tasks}/{self.config.max_queue_size}）")
            
            # 添加到任务队列
            self._task_queues[priority].append(task_info)
            
            # 调度任务
            self._schedule_task(task_info, completion_callback)
            
            logger.debug(f"任务 {task_id} 已提交，类型: {task_type.value}，优先级: {priority.name}")
            
            return task_id
    
    def _schedule_task(self, task_info: TaskInfo, completion_callback: Optional[Callable] = None):
        """调度任务到相应的线程池"""
        thread_pool = self._thread_pools.get(task_info.task_type)
        
        if not thread_pool:
            # 如果没有对应的线程池，使用中图线程池作为默认
            thread_pool = self._thread_pools[TaskType.OCR_MEDIUM]
        
        # 创建可运行对象
        runnable = TaskRunnable(task_info, completion_callback)
        
        # 启动任务
        thread_pool.start(runnable)
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self._lock:
            for priority_queue in self._task_queues.values():
                for task_info in priority_queue:
                    if task_info.task_id == task_id:
                        return task_info
        return None
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        with self._lock:
            stats = {
                "thread_pools": {},
                "task_queues": {},
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0
            }
            
            # 线程池统计
            for task_type, thread_pool in self._thread_pools.items():
                stats["thread_pools"][task_type.value] = {
                    "active_threads": thread_pool.activeThreadCount(),
                    "max_threads": thread_pool.maxThreadCount(),
                    "pending_tasks": thread_pool.activeThreadCount()  # 注意：QThreadPool API 限制
                }
            
            # 任务队列统计
            total_completed = 0
            total_pending = 0
            
            for priority, queue in self._task_queues.items():
                completed = sum(1 for task in queue if task.is_completed)
                pending = len(queue) - completed
                
                stats["task_queues"][priority.name] = {
                    "total": len(queue),
                    "completed": completed,
                    "pending": pending
                }
                
                total_completed += completed
                total_pending += pending
            
            stats["total_tasks"] = total_completed + total_pending
            stats["completed_tasks"] = total_completed
            stats["pending_tasks"] = total_pending
            
            return stats
    
    def update_config(self, new_config: SchedulerConfig):
        """更新配置"""
        with self._lock:
            self.config = new_config
            
            # 更新线程池大小
            self._thread_pools[TaskType.OCR_SMALL].setMaxThreadCount(
                self.config.small_thread_pool_size
            )
            self._thread_pools[TaskType.OCR_MEDIUM].setMaxThreadCount(
                self.config.medium_thread_pool_size
            )
            self._thread_pools[TaskType.OCR_LARGE].setMaxThreadCount(
                self.config.large_thread_pool_size
            )
    
    def shutdown(self):
        """关闭调度器"""
        self._stop_monitor = True
        if self._load_monitor_thread:
            self._load_monitor_thread.join()
            
        # 等待所有线程池完成
        for thread_pool in self._thread_pools.values():
            thread_pool.waitForDone()

# 全局任务调度器实例
global_task_scheduler = TaskScheduler.get_instance()

def get_task_scheduler() -> TaskScheduler:
    """获取全局任务调度器实例"""
    return global_task_scheduler

def set_scheduler_config(config: SchedulerConfig):
    """设置调度器配置"""
    global_task_scheduler.update_config(config)
