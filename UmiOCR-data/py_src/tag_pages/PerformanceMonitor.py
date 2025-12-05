# ============================================
# =============== 性能监控页面 ===============
# ============================================

from PySide2.QtCore import QObject, Slot, Signal, QTimer, QThread
from PySide2.QtGui import QColor
import psutil
import time
import json
import os
from datetime import datetime, timedelta
from ..event_bus.pubsub_service import PubSubService
from umi_log import logger
from ..optimization.hardware_scheduler import HardwareScheduler, BackendType


class PerformanceMonitor(QObject):
    """性能监控器"""
    
    # 信号：发送性能数据
    performanceDataUpdated = Signal(dict)
    
    # 信号：发送告警信息
    alertTriggered = Signal(dict)
    
    def __init__(self, ctrlKey, connector):
        super().__init__()
        self.ctrlKey = ctrlKey
        self.connector = connector
        
        self._is_monitoring = False
        self._monitoring_thread = None
        self._performance_data = []
        self._alert_configs = {
            'cpu_usage': {'threshold': 80, 'enabled': True, 'alerted': False},
            'gpu_usage': {'threshold': 85, 'enabled': True, 'alerted': False},
            'memory_usage': {'threshold': 85, 'enabled': True, 'alerted': False},
            'disk_usage': {'threshold': 90, 'enabled': True, 'alerted': False},
            'task_failure_rate': {'threshold': 10, 'enabled': True, 'alerted': False}
        }
        self._task_stats = {
            'total_tasks': 0,
            'failed_tasks': 0,
            'success_tasks': 0,
            'start_time': time.time()
        }
        
        # 订阅任务相关事件
        PubSubService.subscribeGroup("PerformanceMonitor", self.onTaskStarted, "TaskStarted")
        PubSubService.subscribeGroup("PerformanceMonitor", self.onTaskCompleted, "TaskCompleted")
        PubSubService.subscribeGroup("PerformanceMonitor", self.onTaskFailed, "TaskFailed")
    
    def start_monitoring(self):
        """开始监控"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_thread = QThread()
        self._monitor_worker = PerformanceMonitorWorker()
        self._monitor_worker.moveToThread(self._monitoring_thread)
        self._monitor_worker.performanceData.connect(self._process_performance_data)
        self._monitoring_thread.started.connect(self._monitor_worker.start)
        self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitor_worker:
            self._monitor_worker.stop()
        if self._monitoring_thread:
            self._monitoring_thread.quit()
            self._monitoring_thread.wait()
    
    @Slot(int, result=list)
    def get_performance_data(self, time_range=3600):
        """获取性能数据"""
        end_time = time.time()
        start_time = end_time - time_range
        return [data for data in self._performance_data if data['timestamp'] >= start_time]
    
    @Slot(str, int, str, result=bool)
    def export_data(self, file_path, time_range=3600, format='json'):
        """导出性能数据"""
        try:
            data = self.get_performance_data(time_range)
            if format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format == 'csv':
                self._export_csv(data, file_path)
            else:
                logger.error(f"不支持的格式: {format}")
                return False
            return True
        except Exception as e:
            logger.error(f"导出性能数据失败: {e}", exc_info=True)
            return False
    
    def _export_csv(self, data, file_path):
        """导出为CSV格式"""
        import csv
        if not data:
            return
        
        keys = data[0].keys()
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    
    @Slot(result=dict)
    def get_alert_configs(self):
        """获取告警配置"""
        return self._alert_configs.copy()
    
    @Slot(dict)
    def update_alert_configs(self, configs):
        """更新告警配置"""
        self._alert_configs.update(configs)
        # 重置告警状态
        for key in self._alert_configs:
            self._alert_configs[key]['alerted'] = False
    
    @Slot(result=dict)
    def get_task_stats(self):
        """获取任务统计信息"""
        return self._task_stats.copy()
    
    @Slot(result=str)
    def get_diagnostic_package(self):
        """获取诊断包"""
        try:
            # 获取系统信息
            system_info = {
                'platform': os.name,
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_usage': psutil.disk_usage('/').percent,
                'gpu_info': self._get_gpu_info()
            }
            
            # 获取最近10分钟的性能数据
            performance_data = self.get_performance_data(600)
            
            # 获取任务统计
            task_stats = self.get_task_stats()
            
            # 获取告警配置
            alert_configs = self.get_alert_configs()
            
            # 获取硬件调度器状态
            scheduler = HardwareScheduler.get_instance()
            scheduler_status = {
                'current_backend': scheduler.current_backend.value,
                'target_backend': scheduler.target_backend.value,
                'gpu_status': scheduler.gpu_status.value,
                'gpu_memory_available': scheduler.gpu_memory_available
            }
            
            diagnostic_data = {
                'timestamp': datetime.now().isoformat(),
                'system_info': system_info,
                'performance_data': performance_data,
                'task_stats': task_stats,
                'alert_configs': alert_configs,
                'scheduler_status': scheduler_status
            }
            
            return json.dumps(diagnostic_data, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"生成诊断包失败: {e}", exc_info=True)
            return ""
    
    def _get_gpu_info(self):
        """获取GPU信息"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                return {
                    'name': gpus[0].name,
                    'memory_total': gpus[0].memoryTotal,
                    'memory_used': gpus[0].memoryUsed,
                    'memory_free': gpus[0].memoryFree,
                    'temperature': gpus[0].temperature
                }
        except ImportError:
            pass
        return {}
    
    def _process_performance_data(self, data):
        """处理性能数据"""
        # 添加时间戳
        data['timestamp'] = time.time()
        
        # 计算任务失败率
        if self._task_stats['total_tasks'] > 0:
            data['task_failure_rate'] = (self._task_stats['failed_tasks'] / self._task_stats['total_tasks']) * 100
        else:
            data['task_failure_rate'] = 0
        
        # 计算任务吞吐量
        elapsed_time = time.time() - self._task_stats['start_time']
        if elapsed_time > 0:
            data['task_throughput'] = self._task_stats['total_tasks'] / elapsed_time
        else:
            data['task_throughput'] = 0
        
        # 存储数据（保留24小时）
        self._performance_data.append(data)
        self._cleanup_old_data()
        
        # 检查告警
        self._check_alerts(data)
        
        # 发布性能数据更新事件
        PubSubService.publish("PerformanceDataUpdated", data)
        
        # 发送信号给QML
        self.performanceDataUpdated.emit(data)
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = time.time() - 86400  # 24小时
        self._performance_data = [data for data in self._performance_data if data['timestamp'] >= cutoff_time]
    
    def _check_alerts(self, data):
        """检查告警"""
        for metric, config in self._alert_configs.items():
            if not config['enabled']:
                continue
                
            if metric in data and data[metric] > config['threshold']:
                if not config['alerted']:
                    alert_info = {
                        'metric': metric,
                        'value': data[metric],
                        'threshold': config['threshold'],
                        'timestamp': data['timestamp']
                    }
                    logger.warning(f"性能告警: {metric} 超过阈值 {config['threshold']}, 当前值: {data[metric]}")
                    PubSubService.publish("PerformanceAlert", alert_info)
                    self.alertTriggered.emit(alert_info)
                    config['alerted'] = True
            else:
                # 如果值低于阈值，重置告警状态
                config['alerted'] = False
    
    def onTaskStarted(self):
        """任务开始事件处理"""
        self._task_stats['total_tasks'] += 1
    
    def onTaskCompleted(self):
        """任务完成事件处理"""
        self._task_stats['success_tasks'] += 1
    
    def onTaskFailed(self):
        """任务失败事件处理"""
        self._task_stats['failed_tasks'] += 1


class PerformanceMonitorWorker(QObject):
    """性能监控工作线程"""
    
    performanceData = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._collect_performance_data)
        self._timer.setInterval(1000)  # 每秒收集一次数据
    
    def start(self):
        """开始监控"""
        self._is_running = True
        self._timer.start()
    
    def stop(self):
        """停止监控"""
        self._is_running = False
        self._timer.stop()
    
    def _collect_performance_data(self):
        """收集性能数据"""
        if not self._is_running:
            return
        
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # GPU使用率（如果可用）
            gpu_usage = 0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_usage = gpus[0].load * 100
            except ImportError:
                pass
            
            # 获取硬件调度器状态
            scheduler = HardwareScheduler.get_instance()
            current_backend = scheduler.current_backend.value
            gpu_status = scheduler.gpu_status.value
            
            data = {
                'cpu_usage': cpu_usage,
                'gpu_usage': gpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'current_backend': current_backend,
                'gpu_status': gpu_status
            }
            
            self.performanceData.emit(data)
        except Exception as e:
            logger.error(f"收集性能数据失败: {e}", exc_info=True)