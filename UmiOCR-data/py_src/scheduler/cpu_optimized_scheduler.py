#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= CPU优化的推理调度器 ============-
# ===============================================

import os
import time
import threading
import multiprocessing
from typing import List, Dict, Any, Optional, Callable

from umi_log import logger


class CPUOptimizedScheduler:
    """CPU优化的推理调度器，支持多进程/多线程混合策略"""
    
    def __init__(self):
        self._thread_count: int = multiprocessing.cpu_count()  # CPU线程数
        self._hybrid_mode: bool = True  # 混合多进程/多线程模式
        
        self._process_pool: Optional[multiprocessing.Pool] = None
        self._thread_pool: Optional[List[threading.Thread]] = None
        
        self._task_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._result_queue: multiprocessing.Queue = multiprocessing.Queue()
        
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()
        
        # 性能统计
        self._total_tasks: int = 0
        self._completed_tasks: int = 0
        self._total_processing_time: float = 0.0
        
        logger.info(f"CPU优化调度器已初始化，线程数: {self._thread_count}, 混合模式: {self._hybrid_mode}")
    
    def start(self):
        """启动调度器"""
        with self._lock:
            if self._running:
                logger.info("CPU优化调度器已在运行")
                return
            
            self._running = True
            
            if self._hybrid_mode:
                # 混合模式：使用多进程池
                self._process_pool = multiprocessing.Pool(processes=self._thread_count)
                logger.info(f"已启动多进程池，进程数: {self._thread_count}")
            else:
                # 纯线程模式：创建线程池
                self._thread_pool = []
                for i in range(self._thread_count):
                    thread = threading.Thread(target=self._thread_worker, daemon=True)
                    thread.start()
                    self._thread_pool.append(thread)
                logger.info(f"已启动线程池，线程数: {self._thread_count}")
    
    def stop(self):
        """停止调度器"""
        with self._lock:
            if not self._running:
                logger.info("CPU优化调度器未在运行")
                return
            
            self._running = False
            
            if self._process_pool:
                self._process_pool.close()
                self._process_pool.join(timeout=5.0)
                self._process_pool = None
                logger.info("多进程池已关闭")
            
            if self._thread_pool:
                # 向任务队列添加终止信号
                for _ in range(self._thread_count):
                    self._task_queue.put(None)
                
                # 等待所有线程结束
                for thread in self._thread_pool:
                    thread.join(timeout=5.0)
                
                self._thread_pool = None
                logger.info("线程池已关闭")
    
    def submit_task(self, task_func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        提交任务到调度器
        
        Args:
            task_func: 任务函数
            *args: 任务函数参数
            **kwargs: 任务函数关键字参数
        
        Returns:
            任务结果
        """
        if not self._running:
            logger.error("调度器未运行，无法提交任务")
            return None
        
        self._total_tasks += 1
        
        if self._hybrid_mode and self._process_pool:
            # 混合模式：使用多进程池异步执行任务
            result = self._process_pool.apply_async(task_func, args, kwargs)
            return result.get()
        
        elif not self._hybrid_mode and self._thread_pool:
            # 纯线程模式：将任务添加到任务队列
            self._task_queue.put((task_func, args, kwargs))
            
            # 从结果队列获取结果
            result = self._result_queue.get()
            return result
        
        else:
            logger.error("调度器未正确初始化")
            return None
    
    def _thread_worker(self):
        """线程工作函数"""
        while self._running:
            try:
                # 从任务队列获取任务
                task = self._task_queue.get(timeout=1.0)
                
                if task is None:
                    # 收到终止信号
                    break
                
                task_func, args, kwargs = task
                
                # 执行任务
                start_time = time.time()
                result = task_func(*args, **kwargs)
                processing_time = time.time() - start_time
                
                # 更新性能统计
                with self._lock:
                    self._completed_tasks += 1
                    self._total_processing_time += processing_time
                
                # 将结果放入结果队列
                self._result_queue.put(result)
            
            except multiprocessing.TimeoutError:
                # 任务队列超时，继续等待
                continue
            
            except Exception as e:
                logger.error(f"线程工作函数发生错误: {e}")
    
    def set_thread_count(self, thread_count: int):
        """
        设置CPU线程数
        
        Args:
            thread_count: CPU线程数
        """
        with self._lock:
            max_threads = multiprocessing.cpu_count()
            if thread_count < 1 or thread_count > max_threads:
                logger.warning(f"CPU线程数必须在1到{max_threads}之间，当前值: {thread_count}")
                return
            
            if self._running:
                logger.warning("调度器正在运行，无法修改线程数")
                return
            
            self._thread_count = thread_count
            logger.info(f"CPU线程数已设置: {self._thread_count}")
    
    def get_thread_count(self) -> int:
        """
        获取CPU线程数
        
        Returns:
            CPU线程数
        """
        with self._lock:
            return self._thread_count
    
    def set_hybrid_mode(self, enabled: bool):
        """
        设置混合模式
        
        Args:
            enabled: 是否启用混合多进程/多线程模式
        """
        with self._lock:
            if self._running:
                logger.warning("调度器正在运行，无法修改混合模式")
                return
            
            self._hybrid_mode = enabled
            logger.info(f"混合模式已{'启用' if enabled else '禁用'}")
    
    def get_hybrid_mode(self) -> bool:
        """
        获取混合模式状态
        
        Returns:
            混合模式是否启用
        """
        with self._lock:
            return self._hybrid_mode
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            性能统计信息字典
        """
        with self._lock:
            average_processing_time = self._total_processing_time / self._completed_tasks if self._completed_tasks > 0 else 0.0
            
            return {
                "total_tasks": self._total_tasks,
                "completed_tasks": self._completed_tasks,
                "pending_tasks": self._total_tasks - self._completed_tasks,
                "total_processing_time": self._total_processing_time,
                "average_processing_time": average_processing_time,
                "throughput": self._completed_tasks / self._total_processing_time if self._total_processing_time > 0 else 0.0,
            }
    
    def reset_performance_stats(self):
        """重置性能统计信息"""
        with self._lock:
            self._total_tasks = 0
            self._completed_tasks = 0
            self._total_processing_time = 0.0
            logger.info("性能统计信息已重置")


# 创建全局CPU优化调度器实例
CPUOptimizedSchedulerGlobal = CPUOptimizedScheduler()
