# =============================================
# =============== 性能数据收集器 ===============
# =============================================

import psutil
import time
import threading
from PySide2.QtCore import QObject

from umi_log import logger
from ..event_bus.pubsub_service import PubSubServiceGlobal


try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
    logger.info("NVIDIA GPU 检测成功！")
except Exception as e:
    GPU_AVAILABLE = False
    logger.info(f"未检测到 NVIDIA GPU 或 pynvml 库：{e}")


class PerformanceDataCollector(QObject):
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._collect_thread = None
        self._collect_interval = 1  # 收集间隔，单位：秒

        # 任务统计
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._last_task_count = 0

    # 启动数据收集
    def start(self):
        if self._is_running:
            logger.warning("性能数据收集器已经在运行！")
            return

        self._is_running = True
        self._collect_thread = threading.Thread(target=self._collect_data_loop)
        self._collect_thread.daemon = True
        self._collect_thread.start()

        logger.info("性能数据收集器已启动！")

    # 停止数据收集
    def stop(self):
        if not self._is_running:
            logger.warning("性能数据收集器已经停止！")
            return

        self._is_running = False
        if self._collect_thread:
            self._collect_thread.join()
            self._collect_thread = None

        logger.info("性能数据收集器已停止！")

    # 数据收集循环
    def _collect_data_loop(self):
        while self._is_running:
            start_time = time.time()

            # 收集性能数据
            performance_data = self._collect_performance_data()

            # 发布性能数据事件
            PubSubServiceGlobal.publish("performance_data", performance_data)

            # 等待收集间隔
            elapsed_time = time.time() - start_time
            sleep_time = max(0, self._collect_interval - elapsed_time)
            time.sleep(sleep_time)

    # 收集性能数据
    def _collect_performance_data(self):
        performance_data = {}

        # 收集CPU使用率
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            performance_data["cpu_usage"] = cpu_usage
        except Exception as e:
            logger.error(f"收集 CPU 使用率失败：{e}")

        # 收集内存使用率
        try:
            memory_info = psutil.virtual_memory()
            performance_data["memory_usage"] = memory_info.percent
            performance_data["memory_total"] = memory_info.total
            performance_data["memory_used"] = memory_info.used
        except Exception as e:
            logger.error(f"收集内存使用率失败：{e}")

        # 收集GPU使用率（如果可用）
        if GPU_AVAILABLE:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    gpu_usage = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    memory_usage = pynvml.nvmlDeviceGetUtilizationRates(handle).memory
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    performance_data[f"gpu_{i}_usage"] = gpu_usage
                    performance_data[f"gpu_{i}_memory_usage"] = memory_usage
                    performance_data[f"gpu_{i}_memory_total"] = memory_info.total
                    performance_data[f"gpu_{i}_memory_used"] = memory_info.used
            except Exception as e:
                logger.error(f"收集 GPU 使用率失败：{e}")

        # 收集任务统计数据
        try:
            total_tasks = self._total_tasks
            completed_tasks = self._completed_tasks
            failed_tasks = self._failed_tasks

            performance_data["total_tasks"] = total_tasks
            performance_data["completed_tasks"] = completed_tasks
            performance_data["failed_tasks"] = failed_tasks

            # 计算任务失败率
            if total_tasks > 0:
                failure_rate = (failed_tasks / total_tasks) * 100
            else:
                failure_rate = 0.0
            performance_data["task_failure_rate"] = failure_rate

            # 计算任务吞吐率（每秒处理任务数）
            current_task_count = completed_tasks + failed_tasks
            task_diff = current_task_count - self._last_task_count
            throughput = task_diff / self._collect_interval
            performance_data["throughput"] = throughput

            # 更新最后任务计数
            self._last_task_count = current_task_count
        except Exception as e:
            logger.error(f"收集任务统计数据失败：{e}")

        return performance_data

    # 记录任务完成
    def record_task_completion(self):
        self._total_tasks += 1
        self._completed_tasks += 1

    # 记录任务失败
    def record_task_failure(self):
        self._total_tasks += 1
        self._failed_tasks += 1

    # 获取任务统计
    def get_task_statistics(self):
        return {
            "total_tasks": self._total_tasks,
            "completed_tasks": self._completed_tasks,
            "failed_tasks": self._failed_tasks
        }


# 创建全局实例
PerformanceDataCollectorGlobal = PerformanceDataCollector()
