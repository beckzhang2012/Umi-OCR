# =============================================
# =============== 性能监控页面 ===============
# =============================================

from PySide2.QtCore import QObject, Slot, Signal, QTimer, QMutex
from PySide2.QtGui import QGuiApplication
import time
import json
import csv
import os
import threading
from datetime import datetime, timedelta
from collections import deque

from ..event_bus.pubsub_service import PubSubService
from umi_log import logger
from .page import Page


class PerformanceMonitor(Page):
    def __init__(self, ctrlKey, controller):
        super().__init__(ctrlKey, controller)
        
        # 性能指标数据队列（保留24小时数据）
        self._metrics_data = {
            'cpu_usage': deque(maxlen=86400),  # 24小时，每秒一条
            'gpu_usage': deque(maxlen=86400),
            'memory_usage': deque(maxlen=86400),
            'task_throughput': deque(maxlen=86400),
            'failure_rate': deque(maxlen=86400)
        }
        
        # 阈值配置
        self._thresholds = {
            'cpu_usage': 80,
            'gpu_usage': 90,
            'memory_usage': 85,
            'task_throughput': 0,
            'failure_rate': 10
        }
        
        # 告警配置
        self._alert_config = {
            'enable_popup': True,
            'enable_log': True,
            'enable_notification': False
        }
        
        # 任务统计
        self._task_stats = {
            'total_tasks': 0,
            'failed_tasks': 0,
            'success_tasks': 0,
            'last_task_time': 0
        }
        
        # 定时器
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_metrics)
        self._update_timer.start(1000)  # 每秒更新一次
        
        # 锁
        self._data_mutex = QMutex()
        
        # 订阅性能指标事件
        PubSubService.subscribe("<<PerformanceMetrics>>", self._on_performance_metrics)
        PubSubService.subscribe("<<TaskCompleted>>", self._on_task_completed)
        PubSubService.subscribe("<<TaskFailed>>", self._on_task_failed)
        
        logger.info(f"性能监控页面初始化完成: {self.ctrlKey}")
    
    def __del__(self):
        # 取消订阅
        PubSubService.unsubscribe("<<PerformanceMetrics>>", self._on_performance_metrics)
        PubSubService.unsubscribe("<<TaskCompleted>>", self._on_task_completed)
        PubSubService.unsubscribe("<<TaskFailed>>", self._on_task_failed)
        
        # 停止定时器
        self._update_timer.stop()
        
        super().__del__()
    
    # ========================= 【事件处理】 =========================
    
    def _on_performance_metrics(self, metrics):
        """处理性能指标事件"""
        self._data_mutex.lock()
        try:
            timestamp = time.time()
            
            # 更新指标数据
            if 'cpu_usage' in metrics:
                self._metrics_data['cpu_usage'].append((timestamp, metrics['cpu_usage']))
            if 'gpu_usage' in metrics:
                self._metrics_data['gpu_usage'].append((timestamp, metrics['gpu_usage']))
            if 'memory_usage' in metrics:
                self._metrics_data['memory_usage'].append((timestamp, metrics['memory_usage']))
            
            # 检查阈值告警
            self._check_thresholds(metrics)
            
        finally:
            self._data_mutex.unlock()
    
    def _on_task_completed(self, task_info):
        """处理任务完成事件"""
        self._data_mutex.lock()
        try:
            self._task_stats['total_tasks'] += 1
            self._task_stats['success_tasks'] += 1
            self._task_stats['last_task_time'] = time.time()
            
            # 更新吞吐率
            self._update_throughput()
            
        finally:
            self._data_mutex.unlock()
    
    def _on_task_failed(self, task_info):
        """处理任务失败事件"""
        self._data_mutex.lock()
        try:
            self._task_stats['total_tasks'] += 1
            self._task_stats['failed_tasks'] += 1
            self._task_stats['last_task_time'] = time.time()
            
            # 更新吞吐率和失败率
            self._update_throughput()
            self._update_failure_rate()
            
        finally:
            self._data_mutex.unlock()
    
    # ========================= 【数据更新】 =========================
    
    def _update_throughput(self):
        """更新任务吞吐率"""
        now = time.time()
        # 计算最近1分钟的吞吐率
        minute_ago = now - 60
        tasks_in_minute = sum(1 for t in self._metrics_data['task_throughput'] if t[0] > minute_ago)
        throughput = tasks_in_minute / 60 if tasks_in_minute > 0 else 0
        
        self._metrics_data['task_throughput'].append((now, throughput))
    
    def _update_failure_rate(self):
        """更新任务失败率"""
        now = time.time()
        if self._task_stats['total_tasks'] > 0:
            failure_rate = (self._task_stats['failed_tasks'] / self._task_stats['total_tasks']) * 100
        else:
            failure_rate = 0
        
        self._metrics_data['failure_rate'].append((now, failure_rate))
    
    def _update_metrics(self):
        """定时更新指标并推送到UI"""
        self._data_mutex.lock()
        try:
            # 获取最新指标
            latest_metrics = {}
            
            for metric_name, data_queue in self._metrics_data.items():
                if data_queue:
                    latest_metrics[metric_name] = data_queue[-1][1]
            
            # 添加任务统计
            latest_metrics.update({
                'total_tasks': self._task_stats['total_tasks'],
                'success_tasks': self._task_stats['success_tasks'],
                'failed_tasks': self._task_stats['failed_tasks']
            })
            
            # 推送到UI
            self.callQml("updateMetrics", latest_metrics)
            
        finally:
            self._data_mutex.unlock()
    
    # ========================= 【阈值检查】 =========================
    
    def _check_thresholds(self, metrics):
        """检查指标是否超过阈值"""
        alerts = []
        
        for metric_name, value in metrics.items():
            if metric_name in self._thresholds:
                threshold = self._thresholds[metric_name]
                if value > threshold:
                    alerts.append({
                        'metric': metric_name,
                        'value': value,
                        'threshold': threshold,
                        'timestamp': time.time()
                    })
        
        for alert in alerts:
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert):
        """触发告警"""
        metric_name = alert['metric']
        value = alert['value']
        threshold = alert['threshold']
        timestamp = alert['timestamp']
        
        # 格式化告警信息
        alert_msg = f"性能指标告警: {metric_name} 达到 {value:.1f}%，超过阈值 {threshold:.1f}%"
        alert_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入日志
        if self._alert_config['enable_log']:
            logger.warning(f"[性能告警] {alert_msg} 时间: {alert_time}")
        
        # 弹出提醒
        if self._alert_config['enable_popup']:
            self.callQml("showAlert", alert_msg, alert_time)
        
        # 系统通知
        if self._alert_config['enable_notification']:
            self._show_system_notification(alert_msg)
    
    def _show_system_notification(self, message):
        """显示系统通知"""
        # TODO: 实现系统通知功能
        pass
    
    # ========================= 【QML接口】 =========================
    
    @Slot(str, float)
    def setThreshold(self, metric_name, threshold):
        """设置指标阈值"""
        if metric_name in self._thresholds:
            self._thresholds[metric_name] = threshold
            logger.info(f"更新阈值: {metric_name} = {threshold}")
            return True
        return False
    
    @Slot(str, result=float)
    def getThreshold(self, metric_name):
        """获取指标阈值"""
        return self._thresholds.get(metric_name, 0)
    
    @Slot(str, bool)
    def setAlertConfig(self, config_name, enabled):
        """设置告警配置"""
        if config_name in self._alert_config:
            self._alert_config[config_name] = enabled
            logger.info(f"更新告警配置: {config_name} = {enabled}")
            return True
        return False
    
    @Slot(str, result=bool)
    def getAlertConfig(self, config_name):
        """获取告警配置"""
        return self._alert_config.get(config_name, False)
    
    @Slot(str, str, result=str)
    def exportData(self, metric_name, time_range):
        """导出历史数据"""
        self._data_mutex.lock()
        try:
            if metric_name not in self._metrics_data:
                return json.dumps({'error': '无效的指标名称'})
            
            # 解析时间范围
            end_time = time.time()
            if time_range == '1h':
                start_time = end_time - 3600
            elif time_range == '24h':
                start_time = end_time - 86400
            elif time_range == '7d':
                start_time = end_time - 604800
            else:
                return json.dumps({'error': '无效的时间范围'})
            
            # 过滤数据
            data = self._metrics_data[metric_name]
            filtered_data = [(timestamp, value) for timestamp, value in data if timestamp >= start_time]
            
            # 转换为JSON格式
            export_data = {
                'metric': metric_name,
                'time_range': time_range,
                'start_time': start_time,
                'end_time': end_time,
                'data': filtered_data
            }
            
            return json.dumps(export_data, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return json.dumps({'error': str(e)})
        finally:
            self._data_mutex.unlock()
    
    @Slot(str, str, str, result=str)
    def exportToFile(self, metric_name, time_range, file_path):
        """导出数据到文件"""
        try:
            # 获取数据
            json_data = self.exportData(metric_name, time_range)
            data = json.loads(json_data)
            
            if 'error' in data:
                return data['error']
            
            # 确定文件格式
            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif file_path.endswith('.csv'):
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'value'])
                    for timestamp, value in data['data']:
                        writer.writerow([timestamp, value])
            else:
                return '不支持的文件格式'
            
            return f'数据已成功导出到: {file_path}'
            
        except Exception as e:
            logger.error(f"导出文件失败: {e}")
            return f'导出失败: {str(e)}'
    
    @Slot(result=str)
    def getDiagnosticPackage(self):
        """生成诊断包"""
        self._data_mutex.lock()
        try:
            # 获取系统信息
            import platform
            import psutil
            
            system_info = {
                'system': platform.system(),
                'platform': platform.platform(),
                'python': platform.python_version(),
                'cpu': platform.processor(),
                'cpu_cores': psutil.cpu_count(logical=False),
                'cpu_threads': psutil.cpu_count(logical=True),
                'ram_total': psutil.virtual_memory().total,
                'ram_available': psutil.virtual_memory().available
            }
            
            # 获取当前指标快照
            snapshot = {}
            for metric_name, data_queue in self._metrics_data.items():
                if data_queue:
                    snapshot[metric_name] = data_queue[-1][1]
            
            # 获取任务统计
            task_stats = self._task_stats.copy()
            
            # 获取最近的日志
            recent_logs = self._get_recent_logs()
            
            # 构建诊断包
            diagnostic_package = {
                'timestamp': time.time(),
                'system_info': system_info,
                'metrics_snapshot': snapshot,
                'task_stats': task_stats,
                'recent_logs': recent_logs
            }
            
            return json.dumps(diagnostic_package, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"生成诊断包失败: {e}")
            return f'生成失败: {str(e)}'
        finally:
            self._data_mutex.unlock()
    
    def _get_recent_logs(self, lines=50):
        """获取最近的日志"""
        # TODO: 实现从日志文件读取最近日志
        return []
    
    @Slot()
    def copyDiagnosticPackage(self):
        """一键复制诊断包到剪贴板"""
        try:
            diagnostic_data = self.getDiagnosticPackage()
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(diagnostic_data)
            return True
        except Exception as e:
            logger.error(f"复制诊断包失败: {e}")
            return False
    
    @Slot(str, str, result=str)
    def getHistoryData(self, metric_name, time_range):
        """获取历史数据用于绘制图表"""
        return self.exportData(metric_name, time_range)