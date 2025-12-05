# =============================================
# =============== 性能监控页面控制器 ===============
# =============================================

from PySide2.QtCore import QObject, Slot, Signal
import time
import json
import csv
from datetime import datetime, timedelta

from umi_log import logger
from ..event_bus.pubsub_service import PubSubServiceGlobal
from ..utils.utils import get_system_info


class PerformanceMonitor(QObject):
    def __init__(self, ctrlKey, controller):
        super().__init__()
        self.ctrlKey = ctrlKey
        self.controller = controller
        logger.debug(f"性能监控页面控制器 {self.ctrlKey} 实例化！")

        # 性能数据存储
        self.performance_data = []
        self.max_data_points = 86400  # 24小时，每秒一个数据点

        # 告警阈值
        self.alert_thresholds = {
            "cpu_usage": 80,
            "gpu_usage": 85,
            "memory_usage": 80,
            "task_failure_rate": 10,
            "throughput": 1  # 每秒处理任务数
        }

        # 告警状态
        self.alert_status = {
            "cpu_usage": False,
            "gpu_usage": False,
            "memory_usage": False,
            "task_failure_rate": False,
            "throughput": False
        }

        # 订阅性能数据事件
        PubSubServiceGlobal.subscribe("performance_data", self.on_performance_data)

    def __del__(self):
        logger.debug(f"性能监控页面控制器 {self.ctrlKey} 销毁！")
        # 取消订阅
        PubSubServiceGlobal.unsubscribe("performance_data", self.on_performance_data)

    # 处理性能数据
    def on_performance_data(self, data):
        # 添加时间戳
        data["timestamp"] = time.time()
        # 添加到性能数据列表
        self.performance_data.append(data)
        # 保持数据列表在最大数据点以内
        if len(self.performance_data) > self.max_data_points:
            self.performance_data = self.performance_data[-self.max_data_points:]
        # 检查告警阈值
        self.check_alert_thresholds(data)

    # 检查告警阈值
    def check_alert_thresholds(self, data):
        for metric, threshold in self.alert_thresholds.items():
            if metric in data:
                current_value = data[metric]
                # 检查是否超过阈值
                if current_value > threshold:
                    if not self.alert_status[metric]:
                        # 触发告警
                        self.trigger_alert(metric, current_value, threshold)
                        self.alert_status[metric] = True
                else:
                    if self.alert_status[metric]:
                        # 清除告警
                        self.clear_alert(metric)
                        self.alert_status[metric] = False

    # 触发告警
    def trigger_alert(self, metric, current_value, threshold):
        alert_message = f"性能告警：{metric} 超过阈值！当前值：{current_value:.2f}%，阈值：{threshold}%"
        logger.warning(alert_message)
        # 向QML发送告警消息
        self.callQml("showAlert", alert_message)
        # 这里可以添加系统通知推送逻辑

    # 清除告警
    def clear_alert(self, metric):
        clear_message = f"性能告警已清除：{metric}"
        logger.info(clear_message)
        # 向QML发送告警清除消息
        self.callQml("clearAlert", metric)

    # 设置告警阈值
    @Slot(str, float)
    def set_alert_threshold(self, metric, threshold):
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            logger.info(f"告警阈值已更新：{metric} = {threshold}")

    # 获取告警阈值
    @Slot(str, result=float)
    def get_alert_threshold(self, metric):
        if metric in self.alert_thresholds:
            return self.alert_thresholds[metric]
        return 0.0

    # 获取性能数据（最近N秒）
    @Slot(int, result="QVariant")
    def get_performance_data(self, seconds):
        if seconds <= 0:
            return self.performance_data
        # 计算时间范围
        end_time = time.time()
        start_time = end_time - seconds
        # 过滤数据
        filtered_data = [data for data in self.performance_data if data["timestamp"] >= start_time]
        return filtered_data

    # 导出性能数据为JSON
    @Slot(str, int, int, result=bool)
    def export_data_to_json(self, file_path, start_seconds, end_seconds):
        try:
            # 获取指定时间范围内的数据
            end_time = time.time()
            start_time = end_time - end_seconds
            end_time = end_time - start_seconds
            filtered_data = [data for data in self.performance_data if start_time <= data["timestamp"] <= end_time]

            # 导出为JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=4)

            logger.info(f"性能数据已导出为JSON：{file_path}")
            return True
        except Exception as e:
            logger.error(f"导出性能数据为JSON失败：{e}")
            return False

    # 导出性能数据为CSV
    @Slot(str, int, int, result=bool)
    def export_data_to_csv(self, file_path, start_seconds, end_seconds):
        try:
            # 获取指定时间范围内的数据
            end_time = time.time()
            start_time = end_time - end_seconds
            end_time = end_time - start_seconds
            filtered_data = [data for data in self.performance_data if start_time <= data["timestamp"] <= end_time]

            if not filtered_data:
                logger.warning("没有数据可以导出！")
                return False

            # 导出为CSV
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)

                # 写入表头
                headers = list(filtered_data[0].keys())
                writer.writerow(headers)

                # 写入数据
                for data in filtered_data:
                    row = [data[key] for key in headers]
                    writer.writerow(row)

            logger.info(f"性能数据已导出为CSV：{file_path}")
            return True
        except Exception as e:
            logger.error(f"导出性能数据为CSV失败：{e}")
            return False

    # 生成诊断包
    @Slot(str, result=bool)
    def generate_diagnostic_package(self, file_path):
        try:
            # 收集诊断信息
            diagnostic_info = {
                "timestamp": datetime.now().isoformat(),
                "system_info": get_system_info(),
                "performance_snapshot": self.performance_data[-100:],  # 最近100个数据点
                "alert_thresholds": self.alert_thresholds,
                "alert_status": self.alert_status
            }

            # 导出为JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(diagnostic_info, f, ensure_ascii=False, indent=4)

            logger.info(f"诊断包已生成：{file_path}")
            return True
        except Exception as e:
            logger.error(f"生成诊断包失败：{e}")
            return False

    # 清空性能数据
    @Slot()
    def clear_performance_data(self):
        self.performance_data.clear()
        logger.info("性能数据已清空！")
