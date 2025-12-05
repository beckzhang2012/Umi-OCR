# ===============================================
# =============== 优化的任务调度器 ===============
# ===============================================

import time
import threading
from typing import Dict, List, Callable, Any, Tuple
from PySide2.QtCore import QThreadPool, QRunnable, QMutex


class OptimizedTaskScheduler:
    """优化的任务调度器，支持大图小图分线程池处理和动态调参"""
    
    def __init__(self):
        # 线程池配置
        self._small_image_thread_pool = QThreadPool()
        self._large_image_thread_pool = QThreadPool()
        
        # 默认配置
        self._small_image_threshold = 1024 * 1024  # 1MP (1024x1024)
        self._small_image_max_threads = 8
        self._large_image_max_threads = 4
        
        # 动态调参配置
        self._dynamic_tuning_enabled = True
        self._tuning_interval = 30  # 秒
        
        # 任务队列
        self._small_image_queue: List[Tuple[Callable, List[Any], Dict[str, Any], Callable]] = []
        self._large_image_queue: List[Tuple[Callable, List[Any], Dict[str, Any], Callable]] = []
        
        # 锁
        self._queue_mutex = QMutex()
        
        # 统计信息
        self._task_stats = {
            'small_image': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'avg_processing_time': 0.0,
            },
            'large_image': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'avg_processing_time': 0.0,
            },
        }
        
        # 动态调参线程
        self._tuning_thread = None
        self._tuning_thread_running = False
        
        # 初始化线程池
        self._update_thread_pools()
        
        # 启动动态调参线程
        self._start_tuning_thread()
    
    def add_task(self, task_func: Callable, args: List[Any] = None, 
                  kwargs: Dict[str, Any] = None, callback: Callable = None,
                  image_size: int = 0):
        """
        添加任务到调度器
        
        Args:
            task_func: 任务函数
            args: 任务函数的位置参数
            kwargs: 任务函数的关键字参数
            callback: 任务完成后的回调函数
            image_size: 图像大小 (像素数)
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        
        self._queue_mutex.lock()
        
        if image_size <= self._small_image_threshold:
            # 小图任务
            self._small_image_queue.append((task_func, args, kwargs, callback))
            self._task_stats['small_image']['total_tasks'] += 1
            
            # 启动任务
            self._start_small_image_tasks()
        else:
            # 大图任务
            self._large_image_queue.append((task_func, args, kwargs, callback))
            self._task_stats['large_image']['total_tasks'] += 1
            
            # 启动任务
            self._start_large_image_tasks()
        
        self._queue_mutex.unlock()
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取调度器配置
        
        Returns:
            配置字典
        """
        return {
            'small_image_threshold': self._small_image_threshold,
            'small_image_max_threads': self._small_image_max_threads,
            'large_image_max_threads': self._large_image_max_threads,
            'dynamic_tuning_enabled': self._dynamic_tuning_enabled,
            'tuning_interval': self._tuning_interval,
        }
    
    def set_config(self, config: Dict[str, Any]):
        """
        设置调度器配置
        
        Args:
            config: 配置字典
        """
        self._queue_mutex.lock()
        
        if 'small_image_threshold' in config:
            self._small_image_threshold = config['small_image_threshold']
        
        if 'small_image_max_threads' in config:
            self._small_image_max_threads = config['small_image_max_threads']
        
        if 'large_image_max_threads' in config:
            self._large_image_max_threads = config['large_image_max_threads']
        
        if 'dynamic_tuning_enabled' in config:
            self._dynamic_tuning_enabled = config['dynamic_tuning_enabled']
        
        if 'tuning_interval' in config:
            self._tuning_interval = config['tuning_interval']
        
        # 更新线程池
        self._update_thread_pools()
        
        self._queue_mutex.unlock()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取调度器的统计信息
        
        Returns:
            统计信息字典
        """
        self._queue_mutex.lock()
        
        # 计算队列长度
        small_queue_length = len(self._small_image_queue)
        large_queue_length = len(self._large_image_queue)
        
        # 计算线程池状态
        small_pool_stats = {
            'active_threads': self._small_image_thread_pool.activeThreadCount(),
            'max_threads': self._small_image_thread_pool.maxThreadCount(),
        }
        
        large_pool_stats = {
            'active_threads': self._large_image_thread_pool.activeThreadCount(),
            'max_threads': self._large_image_thread_pool.maxThreadCount(),
        }
        
        stats = {
            'task_stats': self._task_stats.copy(),
            'queue_lengths': {
                'small_image': small_queue_length,
                'large_image': large_queue_length,
            },
            'thread_pool_stats': {
                'small_image': small_pool_stats,
                'large_image': large_pool_stats,
            },
        }
        
        self._queue_mutex.unlock()
        return stats
    
    def clear(self):
        """
        清空调度器
        """
        self._queue_mutex.lock()
        
        # 清空任务队列
        self._small_image_queue.clear()
        self._large_image_queue.clear()
        
        # 重置统计信息
        self._task_stats = {
            'small_image': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'avg_processing_time': 0.0,
            },
            'large_image': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'avg_processing_time': 0.0,
            },
        }
        
        self._queue_mutex.unlock()
    
    def _update_thread_pools(self):
        """更新线程池配置"""
        self._small_image_thread_pool.setMaxThreadCount(self._small_image_max_threads)
        self._large_image_thread_pool.setMaxThreadCount(self._large_image_max_threads)
    
    def _start_small_image_tasks(self):
        """
        启动小图任务
        """
        while True:
            self._queue_mutex.lock()
            
            # 检查是否有任务且线程池有空闲线程
            if len(self._small_image_queue) > 0 and \
               self._small_image_thread_pool.activeThreadCount() < self._small_image_thread_pool.maxThreadCount():
                
                # 获取任务
                task_func, args, kwargs, callback = self._small_image_queue.pop(0)
                
                self._queue_mutex.unlock()
                
                # 启动任务
                runnable = OptimizedRunnable(task_func, args, kwargs, callback, \
                                                'small_image', self._task_completed_callback)
                self._small_image_thread_pool.start(runnable)
            else:
                self._queue_mutex.unlock()
                break
    
    def _start_large_image_tasks(self):
        """
        启动大图任务
        """
        while True:
            self._queue_mutex.lock()
            
            # 检查是否有任务且线程池有空闲线程
            if len(self._large_image_queue) > 0 and \
               self._large_image_thread_pool.activeThreadCount() < self._large_image_thread_pool.maxThreadCount():
                
                # 获取任务
                task_func, args, kwargs, callback = self._large_image_queue.pop(0)
                
                self._queue_mutex.unlock()
                
                # 启动任务
                runnable = OptimizedRunnable(task_func, args, kwargs, callback, \
                                                'large_image', self._task_completed_callback)
                self._large_image_thread_pool.start(runnable)
            else:
                self._queue_mutex.unlock()
                break
    
    def _task_completed_callback(self, task_type: str, processing_time: float):
        """
        任务完成后的回调函数
        
        Args:
            task_type: 任务类型 ('small_image' 或 'large_image')
            processing_time: 任务处理时间 (秒)
        """
        self._queue_mutex.lock()
        
        # 更新统计信息
        self._task_stats[task_type]['completed_tasks'] += 1
        
        # 更新平均处理时间
        current_avg = self._task_stats[task_type]['avg_processing_time']
        total_completed = self._task_stats[task_type]['completed_tasks']
        new_avg = (current_avg * (total_completed - 1) + processing_time) / total_completed
        self._task_stats[task_type]['avg_processing_time'] = new_avg
        
        self._queue_mutex.unlock()
    
    def _start_tuning_thread(self):
        """
        启动动态调参线程
        """
        if self._tuning_thread_running:
            return
        
        self._tuning_thread_running = True
        self._tuning_thread = threading.Thread(target=self._tuning_thread_func)
        self._tuning_thread.daemon = True
        self._tuning_thread.start()
    
    def _tuning_thread_func(self):
        """
        动态调参线程函数
        """
        while self._tuning_thread_running:
            time.sleep(self._tuning_interval)
            
            if not self._dynamic_tuning_enabled:
                continue
            
            self._queue_mutex.lock()
            
            # 获取统计信息
            stats = self.get_stats()
            
            # 动态调参逻辑
            # 这里只是一个简单的例子，实际应该根据具体情况调整
            
            # 小图线程池调参
            small_queue_length = stats['queue_lengths']['small_image']
            small_active_threads = stats['thread_pool_stats']['small_image']['active_threads']
            small_max_threads = stats['thread_pool_stats']['small_image']['max_threads']
            
            if small_queue_length > small_active_threads and small_max_threads < 16:
                # 队列过长且线程池未达上限，增加线程数
                self._small_image_max_threads += 1
            elif small_queue_length == 0 and small_active_threads == 0 and small_max_threads > 4:
                # 队列空且无活跃线程，减少线程数
                self._small_image_max_threads -= 1
            
            # 大图线程池调参
            large_queue_length = stats['queue_lengths']['large_image']
            large_active_threads = stats['thread_pool_stats']['large_image']['active_threads']
            large_max_threads = stats['thread_pool_stats']['large_image']['max_threads']
            
            if large_queue_length > large_active_threads and large_max_threads < 8:
                # 队列过长且线程池未达上限，增加线程数
                self._large_image_max_threads += 1
            elif large_queue_length == 0 and large_active_threads == 0 and large_max_threads > 2:
                # 队列空且无活跃线程，减少线程数
                self._large_image_max_threads -= 1
            
            # 更新线程池
            self._update_thread_pools()
            
            self._queue_mutex.unlock()


class OptimizedRunnable(QRunnable):
    """优化的Runnable，用于包装任务函数并记录处理时间"""
    
    def __init__(self, task_func: Callable, args: List[Any], kwargs: Dict[str, Any], 
                 callback: Callable, task_type: str, completed_callback: Callable):
        super().__init__()
        self._task_func = task_func
        self._args = args
        self._kwargs = kwargs
        self._callback = callback
        self._task_type = task_type
        self._completed_callback = completed_callback
    
    def run(self):
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行任务
            result = self._task_func(*self._args, **self._kwargs)
            
            # 记录结束时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 调用任务完成回调
            if self._completed_callback:
                self._completed_callback(self._task_type, processing_time)
            
            # 调用用户提供的回调
            if self._callback:
                self._callback(result)
                
        except Exception as e:
            from umi_log import logger
            logger.error(f"任务执行失败: {e}", exc_info=True, stack_info=True)
            
            # 调用用户提供的回调（传递错误）
            if self._callback:
                self._callback({'code': 900, 'data': f'任务执行失败: {e}'})


# 全局优化任务调度器实例
OptimizedTaskSchedulerGlobal = OptimizedTaskScheduler()
