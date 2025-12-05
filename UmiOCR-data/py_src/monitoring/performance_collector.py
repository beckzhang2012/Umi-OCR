# =============================================
# =============== 性能指标收集器 ===============
# =============================================

import time
import threading
import psutil
from PySide2.QtCore import QObject, QTimer, QMutex

from ..event_bus.pubsub_service import PubSubService
from umi_log import logger


def get_gpu_info():
    """获取GPU信息（简化版本）"""
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpus = []
        
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            gpus.append({
                'name': pynvml.nvmlDeviceGetName(handle).decode('utf-8'),
                'memory_total': info.total,
                'memory_used': info.used,
                'memory_free': info.free,
                'gpu_utilization': utilization.gpu,
                'memory_utilization': utilization.memory
            })
        
        pynvml.nvmlShutdown()
        return gpus
    except ImportError:
        logger.warning("pynvml模块未安装，无法获取GPU信息")
        return []
    except Exception as e:
        logger.error(f"获取GPU信息失败: {e}")
        return []


class PerformanceCollector(QObject):
    def __init__(self, interval=1):
        super().__init__()
        
        self._interval = interval  # 收集间隔（秒）
        self._running = False
        self._thread = None
        self._mutex = QMutex()
        
        # GPU信息缓存
        self._gpu_info = []
        self._last_gpu_check = 0
        
        logger.info("性能指标收集器初始化完成")
    
    def start(self):
        """启动性能收集"""
        self._mutex.lock()
        try:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._collect_loop, daemon=True)
                self._thread.start()
                logger.info("性能指标收集器已启动")
        finally:
            self._mutex.unlock()
    
    def stop(self):
        """停止性能收集"""
        self._mutex.lock()
        try:
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("性能指标收集器已停止")
        finally:
            self._mutex.unlock()
    
    def is_running(self):
        """检查收集器是否正在运行"""
        self._mutex.lock()
        try:
            return self._running
        finally:
            self._mutex.unlock()
    
    def _collect_loop(self):
        """收集循环"""
        while self.is_running():
            try:
                self._collect_and_publish()
                time.sleep(self._interval)
            except Exception as e:
                logger.error(f"性能收集循环异常: {e}")
                time.sleep(self._interval)
    
    def _collect_and_publish(self):
        """收集性能指标并发布"""
        metrics = self._collect_metrics()
        
        if metrics:
            PubSubService.publish("<<PerformanceMetrics>>", metrics)
    
    def _collect_metrics(self):
        """收集性能指标"""
        metrics = {}
        
        # CPU使用率
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            metrics['cpu_usage'] = cpu_usage
        except Exception as e:
            logger.error(f"获取CPU使用率失败: {e}")
        
        # 内存使用率
        try:
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.percent
            metrics['memory_total'] = memory.total
            metrics['memory_used'] = memory.used
            metrics['memory_available'] = memory.available
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
        
        # GPU信息（每10秒检查一次）
        try:
            now = time.time()
            if now - self._last_gpu_check > 10:
                self._gpu_info = get_gpu_info()
                self._last_gpu_check = now
            
            if self._gpu_info:
                # 使用第一个GPU的数据
                gpu = self._gpu_info[0]
                metrics['gpu_usage'] = gpu['gpu_utilization']
                metrics['gpu_memory_usage'] = gpu['memory_utilization']
                metrics['gpu_memory_total'] = gpu['memory_total']
                metrics['gpu_memory_used'] = gpu['memory_used']
        except Exception as e:
            logger.error(f"获取GPU信息失败: {e}")
        
        # 磁盘IO
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics['disk_read_bytes'] = disk_io.read_bytes
                metrics['disk_write_bytes'] = disk_io.write_bytes
        except Exception as e:
            logger.error(f"获取磁盘IO信息失败: {e}")
        
        # 网络IO
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                metrics['net_sent_bytes'] = net_io.bytes_sent
                metrics['net_recv_bytes'] = net_io.bytes_recv
        except Exception as e:
            logger.error(f"获取网络IO信息失败: {e}")
        
        # 进程信息
        try:
            process = psutil.Process()
            metrics['process_cpu_usage'] = process.cpu_percent()
            metrics['process_memory_usage'] = process.memory_percent()
            metrics['process_memory_rss'] = process.memory_info().rss
        except Exception as e:
            logger.error(f"获取进程信息失败: {e}")
        
        return metrics
    
    def get_current_metrics(self):
        """获取当前性能指标"""
        return self._collect_metrics()
    
    def get_gpu_info(self):
        """获取GPU信息"""
        return self._gpu_info.copy()


# 全局性能收集器实例
_performance_collector = None


def get_performance_collector():
    """获取全局性能收集器实例"""
    global _performance_collector
    if _performance_collector is None:
        _performance_collector = PerformanceCollector()
    return _performance_collector


def start_performance_collection():
    """启动性能收集"""
    collector = get_performance_collector()
    collector.start()


def stop_performance_collection():
    """停止性能收集"""
    collector = get_performance_collector()
    collector.stop()