# ===============================================
# =============== 性能监测模块 ===============
# ===============================================

"""
吞吐监测模块：记录每批次的处理耗时、线程等待时间、显存/内存峰值，并在UI展示。
"""

import threading
import time
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from imports.umi_log import logger

class MetricType(Enum):
    """性能指标类型枚举"""
    PROCESSING_TIME = "processing_time"      # 处理时间
    WAITING_TIME = "waiting_time"           # 等待时间
    MEMORY_PEAK = "memory_peak"             # 内存峰值
    GPU_MEMORY_PEAK = "gpu_memory_peak"     # GPU显存峰值
    THREAD_UTILIZATION = "thread_utilization"  # 线程利用率
    TASK_THROUGHPUT = "task_throughput"     # 任务吞吐量
    ERROR_RATE = "error_rate"               # 错误率

@dataclass
class PerformanceMetric:
    """性能指标数据"""
    metric_type: MetricType        # 指标类型
    value: float                   # 指标值
    unit: str                      # 单位
    timestamp: float               # 时间戳
    task_id: Optional[str] = None  # 关联任务ID
    batch_id: Optional[str] = None  # 关联批次ID
    metadata: Optional[Dict[str, Any]] = None  # 元数据

@dataclass
class BatchInfo:
    """批次信息"""
    batch_id: str                  # 批次ID
    task_count: int                # 任务数量
    start_time: float              # 开始时间
    end_time: Optional[float] = None  # 结束时间
    metrics: List[PerformanceMetric] = None  # 性能指标
    status: str = "running"        # 状态
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = []

@dataclass
class MonitorConfig:
    """监测器配置"""
    enable_monitoring: bool = True          # 是否启用监测
    sampling_interval: float = 0.1          # 采样间隔（秒）
    max_history_size: int = 1000            # 历史数据最大数量
    enable_gpu_monitoring: bool = False     # 是否启用GPU监测
    enable_real_time_reporting: bool = True  # 是否启用实时报告
    report_interval: float = 1.0            # 报告间隔（秒）

class PerformanceMonitor:
    """性能监测器"""
    
    _instance: Optional['PerformanceMonitor'] = None
    _lock: threading.Lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'PerformanceMonitor':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = PerformanceMonitor()
        return cls._instance
    
    def __init__(self):
        self.config = MonitorConfig()
        self._batches: Dict[str, BatchInfo] = {}
        self._metrics_history: List[PerformanceMetric] = []
        self._batch_counter: int = 0
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor: bool = False
        self._current_batch_id: Optional[str] = None
        
        # 系统资源监测
        self._memory_peak = 0
        self._gpu_memory_peak = 0
        
        # 尝试导入GPU监测模块
        self._gpu_available = False
        try:
            import pynvml
            pynvml.nvmlInit()
            self._gpu_available = True
            self._pynvml = pynvml
        except ImportError:
            logger.warning("pynvml 未安装，GPU监测不可用")
        except Exception as e:
            logger.warning(f"GPU初始化失败: {e}")
        
        # 启动监测线程
        self._start_monitor_thread()
    
    def _start_monitor_thread(self):
        """启动监测线程"""
        if not self.config.enable_monitoring:
            return
            
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_loop(self):
        """监测循环"""
        while not self._stop_monitor:
            start_time = time.time()
            
            # 采集系统资源数据
            self._collect_system_metrics()
            
            # 检查是否需要报告
            if self.config.enable_real_time_reporting:
                self._report_metrics()
            
            # 控制采样间隔
            elapsed = time.time() - start_time
            sleep_time = max(0, self.config.sampling_interval - elapsed)
            time.sleep(sleep_time)
    
    def _collect_system_metrics(self):
        """采集系统资源指标"""
        try:
            # 内存使用情况
            memory_info = psutil.virtual_memory()
            memory_used = memory_info.used / (1024 * 1024)  # MB
            
            with self._lock:
                if memory_used > self._memory_peak:
                    self._memory_peak = memory_used
            
            # GPU内存使用情况
            if self._gpu_available and self.config.enable_gpu_monitoring:
                try:
                    handle = self._pynvml.nvmlDeviceGetHandleByIndex(0)
                    mem_info = self._pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_memory_used = mem_info.used / (1024 * 1024)  # MB
                    
                    with self._lock:
                        if gpu_memory_used > self._gpu_memory_peak:
                            self._gpu_memory_peak = gpu_memory_used
                except Exception as e:
                    logger.debug(f"GPU内存采集失败: {e}")
        except Exception as e:
            logger.debug(f"系统指标采集失败: {e}")
    
    def _report_metrics(self):
        """报告性能指标"""
        try:
            # 这里可以实现实时报告机制，比如通过PubSubService发布
            # 或者发送到UI界面
            pass
        except Exception as e:
            logger.debug(f"指标报告失败: {e}")
    
    def start_batch(self, task_count: int) -> str:
        """开始一个新的批次"""
        if not self.config.enable_monitoring:
            return ""
            
        with self._lock:
            self._batch_counter += 1
            batch_id = f"batch_{self._batch_counter:08d}"
            
            batch_info = BatchInfo(
                batch_id=batch_id,
                task_count=task_count,
                start_time=time.time()
            )
            
            self._batches[batch_id] = batch_info
            self._current_batch_id = batch_id
            
            # 重置峰值统计
            self._memory_peak = 0
            self._gpu_memory_peak = 0
            
            logger.debug(f"批次 {batch_id} 已开始，包含 {task_count} 个任务")
            
            return batch_id
    
    def end_batch(self, batch_id: str):
        """结束一个批次"""
        if not self.config.enable_monitoring:
            return
            
        with self._lock:
            if batch_id not in self._batches:
                return
            
            batch_info = self._batches[batch_id]
            batch_info.end_time = time.time()
            batch_info.status = "completed"
            
            # 记录批次级指标
            processing_time = batch_info.end_time - batch_info.start_time
            task_count = int(batch_info.task_count)
            throughput = task_count / processing_time if processing_time > 0 else 0
            
            # 添加批次指标
            batch_info.metrics.extend([
                PerformanceMetric(
                    metric_type=MetricType.PROCESSING_TIME,
                    value=processing_time,
                    unit="秒",
                    timestamp=time.time(),
                    batch_id=batch_id,
                    metadata={"task_count": batch_info.task_count}
                ),
                PerformanceMetric(
                    metric_type=MetricType.TASK_THROUGHPUT,
                    value=throughput,
                    unit="任务/秒",
                    timestamp=time.time(),
                    batch_id=batch_id
                ),
                PerformanceMetric(
                    metric_type=MetricType.MEMORY_PEAK,
                    value=self._memory_peak,
                    unit="MB",
                    timestamp=time.time(),
                    batch_id=batch_id
                )
            ])
            
            # 如果GPU可用，添加GPU指标
            if self._gpu_available:
                batch_info.metrics.append(
                    PerformanceMetric(
                        metric_type=MetricType.GPU_MEMORY_PEAK,
                        value=self._gpu_memory_peak,
                        unit="MB",
                        timestamp=time.time(),
                        batch_id=batch_id
                    )
                )
            
            # 保存到历史记录
            self._metrics_history.extend(batch_info.metrics)
            
            # 限制历史记录大小
            if len(self._metrics_history) > self.config.max_history_size:
                self._metrics_history = self._metrics_history[-self.config.max_history_size:]
            
            logger.info(
                f"批次 {batch_id} 已完成: {processing_time:.2f}秒, "
                f"吞吐量: {throughput:.2f}任务/秒, "
                f"内存峰值: {self._memory_peak:.2f}MB"
            )
            
            # 如果是当前批次，清除当前批次ID
            if self._current_batch_id == batch_id:
                self._current_batch_id = None
    
    def record_task_metric(
        self, 
        task_id: str, 
        metric_type: MetricType, 
        value: float, 
        unit: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录任务级指标"""
        if not self.config.enable_monitoring:
            return
            
        with self._lock:
            metric = PerformanceMetric(
                metric_type=metric_type,
                value=value,
                unit=unit,
                timestamp=time.time(),
                task_id=task_id,
                batch_id=self._current_batch_id,
                metadata=metadata
            )
            
            self._metrics_history.append(metric)
            
            # 限制历史记录大小
            if len(self._metrics_history) > self.config.max_history_size:
                self._metrics_history.pop(0)
    
    def get_batch_metrics(self, batch_id: str) -> Optional[List[PerformanceMetric]]:
        """获取批次的性能指标"""
        with self._lock:
            batch_info = self._batches.get(batch_id)
            return batch_info.metrics if batch_info else None
    
    def get_recent_metrics(self, count: int = 100) -> List[PerformanceMetric]:
        """获取最近的性能指标"""
        with self._lock:
            return self._metrics_history[-count:]
    
    def get_batch_info(self, batch_id: str) -> Optional[BatchInfo]:
        """获取批次信息"""
        with self._lock:
            return self._batches.get(batch_id)
    
    def get_all_batches(self) -> List[BatchInfo]:
        """获取所有批次信息"""
        with self._lock:
            return list(self._batches.values())
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            if not self._metrics_history:
                return {"error": "暂无性能数据"}
            
            summary = {
                "total_batches": len(self._batches),
                "total_metrics": len(self._metrics_history),
                "current_memory_peak": self._memory_peak,
                "current_gpu_memory_peak": self._gpu_memory_peak if self._gpu_available else 0,
                "recent_metrics": []
            }
            
            # 添加最近的指标
            recent_metrics = self._metrics_history[-10:]
            for metric in recent_metrics:
                summary["recent_metrics"].append({
                    "type": metric.metric_type.value,
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp
                })
            
            return summary
    
    def export_metrics(self, file_path: str) -> bool:
        """导出性能指标到文件"""
        try:
            with self._lock:
                data = {
                    "batches": [],
                    "metrics": []
                }
                
                # 导出批次信息
                for batch_info in self._batches.values():
                    batch_data = {
                        "batch_id": batch_info.batch_id,
                        "task_count": batch_info.task_count,
                        "start_time": batch_info.start_time,
                        "end_time": batch_info.end_time,
                        "status": batch_info.status,
                        "metrics": []
                    }
                    
                    for metric in batch_info.metrics:
                        batch_data["metrics"].append({
                            "type": metric.metric_type.value,
                            "value": metric.value,
                            "unit": metric.unit,
                            "timestamp": metric.timestamp
                        })
                    
                    data["batches"].append(batch_data)
                
                # 导出所有指标
                for metric in self._metrics_history:
                    data["metrics"].append({
                        "type": metric.metric_type.value,
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": metric.timestamp,
                        "task_id": metric.task_id,
                        "batch_id": metric.batch_id
                    })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"性能指标已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出性能指标失败: {e}")
            return False
    
    def clear_history(self):
        """清除历史数据"""
        with self._lock:
            self._batches.clear()
            self._metrics_history.clear()
            self._memory_peak = 0
            self._gpu_memory_peak = 0
            logger.info("性能监测历史数据已清除")
    
    def shutdown(self):
        """关闭监测器"""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join()
            
        # 清理GPU资源
        if self._gpu_available:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass

# 全局性能监测器实例
global_performance_monitor = PerformanceMonitor.get_instance()

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监测器实例"""
    return global_performance_monitor

def set_monitor_config(config: MonitorConfig):
    """设置监测器配置"""
    global_performance_monitor.config = config
