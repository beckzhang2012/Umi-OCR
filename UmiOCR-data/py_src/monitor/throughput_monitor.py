# ===============================================
# =============== 吞吐监测器 ===================
# ===============================================

import time
import psutil
import threading
from typing import Dict, List, Any, Callable
from PySide2.QtCore import QMutex, QObject, Signal


class ThroughputMonitor(QObject):
    """吞吐监测器，用于记录处理耗时、线程等待时间、显存/内存峰值等信息"""
    
    # 信号：当有新的监测数据时发射
    new_monitor_data = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        # 监测配置
        self._monitor_enabled = True
        self._monitor_interval = 0.5  # 秒
        
        # 记录的监测数据
        self._monitor_data: List[Dict[str, Any]] = []
        
        # 任务级监测数据
        self._current_task_id = None
        self._current_task_start_time = None
        self._current_task_thread_wait_times: List[float] = []
        
        # 系统资源监测
        self._memory_peak = 0.0  # GB
        self._cpu_peak = 0.0  # 百分比
        
        # 锁
        self._data_mutex = QMutex()
        
        # 系统资源监测线程
        self._resource_monitor_thread = None
        self._resource_monitor_thread_running = False
        
        # 启动系统资源监测线程
        self._start_resource_monitor_thread()
    
    def start_task_monitoring(self, task_id: str):
        """
        开始任务监测
        
        Args:
            task_id: 任务ID
        """
        self._data_mutex.lock()
        
        # 停止之前的任务监测
        if self._current_task_id is not None:
            self._stop_task_monitoring_internal()
        
        # 开始新的任务监测
        self._current_task_id = task_id
        self._current_task_start_time = time.time()
        self._current_task_thread_wait_times.clear()
        
        # 重置资源峰值
        self._memory_peak = 0.0
        self._cpu_peak = 0.0
        
        self._data_mutex.unlock()
    
    def stop_task_monitoring(self):
        """
        停止任务监测
        """
        self._data_mutex.lock()
        
        if self._current_task_id is not None:
            self._stop_task_monitoring_internal()
        
        self._data_mutex.unlock()
    
    def record_thread_wait_time(self, wait_time: float):
        """
        记录线程等待时间
        
        Args:
            wait_time: 线程等待时间 (秒)
        """
        self._data_mutex.lock()
        
        if self._current_task_id is not None:
            self._current_task_thread_wait_times.append(wait_time)
        
        self._data_mutex.unlock()
    
    def get_monitor_data(self) -> List[Dict[str, Any]]:
        """
        获取所有监测数据
        
        Returns:
            监测数据列表
        """
        self._data_mutex.lock()
        data = self._monitor_data.copy()
        self._data_mutex.unlock()
        return data
    
    def get_task_monitor_data(self, task_id: str) -> Dict[str, Any]:
        """
        获取指定任务的监测数据
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务的监测数据，如果不存在则返回空字典
        """
        self._data_mutex.lock()
        
        for data in self._monitor_data:
            if data['task_id'] == task_id:
                self._data_mutex.unlock()
                return data.copy()
        
        self._data_mutex.unlock()
        return {}
    
    def get_recent_monitor_data(self, max_count: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的监测数据
        
        Args:
            max_count: 最大返回数量
            
        Returns:
            最近的监测数据列表
        """
        self._data_mutex.lock()
        data = self._monitor_data[-max_count:].copy()
        self._data_mutex.unlock()
        return data
    
    def get_peak_resources(self) -> Dict[str, float]:
        """
        获取资源峰值
        
        Returns:
            资源峰值字典
        """
        self._data_mutex.lock()
        stats = {
            'memory_peak': self._memory_peak,
            'cpu_peak': self._cpu_peak,
        }
        self._data_mutex.unlock()
        return stats
    
    def clear_monitor_data(self):
        """
        清空监测数据
        """
        self._data_mutex.lock()
        self._monitor_data.clear()
        self._data_mutex.unlock()
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取监测器配置
        
        Returns:
            配置字典
        """
        return {
            'monitor_enabled': self._monitor_enabled,
            'monitor_interval': self._monitor_interval,
        }
    
    def set_config(self, config: Dict[str, Any]):
        """
        设置监测器配置
        
        Args:
            config: 配置字典
        """
        self._data_mutex.lock()
        
        if 'monitor_enabled' in config:
            self._monitor_enabled = config['monitor_enabled']
        
        if 'monitor_interval' in config:
            self._monitor_interval = config['monitor_interval']
        
        self._data_mutex.unlock()
    
    def _stop_task_monitoring_internal(self):
        """
        停止任务监测的内部方法
        """
        if self._current_task_id is None or self._current_task_start_time is None:
            return
        
        # 计算任务总耗时
        total_processing_time = time.time() - self._current_task_start_time
        
        # 计算平均线程等待时间
        if self._current_task_thread_wait_times:
            avg_thread_wait_time = sum(self._current_task_thread_wait_times) / len(self._current_task_thread_wait_times)
        else:
            avg_thread_wait_time = 0.0
        
        # 获取资源峰值
        memory_peak = self._memory_peak
        cpu_peak = self._cpu_peak
        
        # 创建任务监测数据
        task_monitor_data = {
            'task_id': self._current_task_id,
            'start_time': self._current_task_start_time,
            'end_time': time.time(),
            'total_processing_time': total_processing_time,
            'avg_thread_wait_time': avg_thread_wait_time,
            'memory_peak': memory_peak,
            'cpu_peak': cpu_peak,
        }
        
        # 添加到监测数据列表
        self._monitor_data.append(task_monitor_data)
        
        # 发射新数据信号
        self.new_monitor_data.emit(task_monitor_data)
        
        # 重置任务监测变量
        self._current_task_id = None
        self._current_task_start_time = None
        self._current_task_thread_wait_times.clear()
    
    def _start_resource_monitor_thread(self):
        """
        启动系统资源监测线程
        """
        if self._resource_monitor_thread_running:
            return
        
        self._resource_monitor_thread_running = True
        self._resource_monitor_thread = threading.Thread(target=self._resource_monitor_thread_func)
        self._resource_monitor_thread.daemon = True
        self._resource_monitor_thread.start()
    
    def update_peak_resources(self, memory_peak=None, cpu_peak=None):
        """
        更新资源使用峰值
        
        Args:
            memory_peak: 内存使用峰值（GB）
            cpu_peak: CPU使用峰值（%）
        """
        self._data_mutex.lock()
        if memory_peak is not None:
            self._memory_peak = max(self._memory_peak, memory_peak)
        
        if cpu_peak is not None:
            self._cpu_peak = max(self._cpu_peak, cpu_peak)
        self._data_mutex.unlock()

    def _resource_monitor_thread_func(self):
        """
        系统资源监测线程函数
        """
        while self._resource_monitor_thread_running:
            if not self._monitor_enabled:
                time.sleep(self._monitor_interval)
                continue
            
            try:
                # 获取当前进程的资源使用情况
                process = psutil.Process()
                
                # 获取内存使用情况 (GB)
                memory_info = process.memory_info()
                memory_usage = memory_info.rss / (1024 * 1024 * 1024)  # 转换为GB
                
                # 获取CPU使用情况 (百分比)
                cpu_usage = process.cpu_percent(interval=0.1) / psutil.cpu_count()  # 平均到每个CPU核心
                
                # 更新资源峰值
                self.update_peak_resources(memory_peak=memory_usage, cpu_peak=cpu_usage)
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                from umi_log import logger
                logger.error(f"资源监测失败: {e}")
                time.sleep(self._monitor_interval)


# 全局吞吐监测器实例
ThroughputMonitorGlobal = ThroughputMonitor()
