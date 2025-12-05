# ===============================================
# =============== GPU状态监控模块 ===============
# ===============================================

import threading
import time
import subprocess
import re
from umi_log import logger


class GPUMonitor:
    """GPU状态监控类，用于实时监控GPU的占用、温度和显存使用情况"""

    def __init__(self, gpu_id=0, check_interval=1.0):
        """
        初始化GPU监控器
        :param gpu_id: 要监控的GPU ID
        :param check_interval: 监控检查间隔（秒）
        """
        self.gpu_id = gpu_id
        self.check_interval = check_interval
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # GPU状态信息
        self.utilization = 0  # GPU占用率（%）
        self.temperature = 0  # GPU温度（℃）
        self.memory_used = 0  # 已使用显存（MB）
        self.memory_total = 0  # 总显存（MB）
        self.memory_utilization = 0  # 显存使用率（%）
        self.driver_error = False  # 驱动错误标志

        # 异常检测阈值
        self.utilization_threshold = 95  # GPU占用率阈值（%）
        self.temperature_threshold = 90  # GPU温度阈值（℃）
        self.memory_threshold = 95  # 显存使用率阈值（%）
        self.error_duration_threshold = 5  # 异常持续时间阈值（秒）

        # 异常状态跟踪
        self._utilization_exceeded_since = None
        self._temperature_exceeded_since = None
        self._memory_exceeded_since = None
        self._driver_error_since = None

        # 回调函数
        self.on_gpu_exception = None  # GPU异常时的回调
        self.on_gpu_recovered = None  # GPU恢复正常时的回调

    def _update_gpu_status(self):
        """更新GPU状态信息"""
        try:
            # 使用nvidia-smi获取GPU状态
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                encoding="utf-8",
                stderr=subprocess.STDOUT
            )

            lines = result.strip().split('\n')
            if self.gpu_id < len(lines):
                line = lines[self.gpu_id]
                parts = line.split(',')
                if len(parts) >= 4:
                    with self._lock:
                        self.utilization = int(parts[0].strip())
                        self.temperature = int(parts[1].strip())
                        self.memory_used = int(parts[2].strip())
                        self.memory_total = int(parts[3].strip())
                        self.memory_utilization = (self.memory_used / self.memory_total) * 100 if self.memory_total > 0 else 0
                        self.driver_error = False

        except subprocess.CalledProcessError as e:
            logger.error(f"获取GPU状态失败: {e.output}")
            with self._lock:
                self.driver_error = True
        except FileNotFoundError:
            logger.warning("nvidia-smi未找到，可能没有NVIDIA GPU或驱动未安装")
            with self._lock:
                self.driver_error = True
        except Exception as e:
            logger.error(f"更新GPU状态发生未知错误: {e}")
            with self._lock:
                self.driver_error = True

    def _check_gpu_exception(self):
        """检查GPU是否异常"""
        with self._lock:
            utilization = self.utilization
            temperature = self.temperature
            memory_utilization = self.memory_utilization
            driver_error = self.driver_error

        current_time = time.time()
        exception = False
        exception_reason = ""

        # 检查GPU占用率
        if utilization > self.utilization_threshold:
            if self._utilization_exceeded_since is None:
                self._utilization_exceeded_since = current_time
            elif current_time - self._utilization_exceeded_since >= self.error_duration_threshold:
                exception = True
                exception_reason += f"GPU占用率过高({utilization}%)，"
        else:
            self._utilization_exceeded_since = None

        # 检查GPU温度
        if temperature > self.temperature_threshold:
            if self._temperature_exceeded_since is None:
                self._temperature_exceeded_since = current_time
            elif current_time - self._temperature_exceeded_since >= self.error_duration_threshold:
                exception = True
                exception_reason += f"GPU温度过高({temperature}℃)，"
        else:
            self._temperature_exceeded_since = None

        # 检查显存使用率
        if memory_utilization > self.memory_threshold:
            if self._memory_exceeded_since is None:
                self._memory_exceeded_since = current_time
            elif current_time - self._memory_exceeded_since >= self.error_duration_threshold:
                exception = True
                exception_reason += f"显存使用率过高({memory_utilization:.1f}%)，"
        else:
            self._memory_exceeded_since = None

        # 检查驱动错误
        if driver_error:
            if self._driver_error_since is None:
                self._driver_error_since = current_time
            elif current_time - self._driver_error_since >= self.error_duration_threshold:
                exception = True
                exception_reason += "GPU驱动错误，"
        else:
            self._driver_error_since = None

        if exception:
            exception_reason = exception_reason.rstrip('，')
            logger.error(f"GPU异常: {exception_reason}")
            if self.on_gpu_exception:
                self.on_gpu_exception(exception_reason)
        else:
            # 检查是否从异常恢复
            if any([self._utilization_exceeded_since, self._temperature_exceeded_since, self._memory_exceeded_since, self._driver_error_since]):
                logger.info("GPU状态已恢复正常")
                if self.on_gpu_recovered:
                    self.on_gpu_recovered()

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            self._update_gpu_status()
            self._check_gpu_exception()
            time.sleep(self.check_interval)

    def start(self):
        """启动GPU监控"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            logger.info(f"GPU监控已启动，GPU ID: {self.gpu_id}，检查间隔: {self.check_interval}秒")

    def stop(self):
        """停止GPU监控"""
        if self._running:
            self._running = False
            if self._thread:
                self._thread.join()
            logger.info("GPU监控已停止")

    def get_status(self):
        """获取当前GPU状态"""
        with self._lock:
            return {
                "utilization": self.utilization,
                "temperature": self.temperature,
                "memory_used": self.memory_used,
                "memory_total": self.memory_total,
                "memory_utilization": self.memory_utilization,
                "driver_error": self.driver_error
            }

    def set_thresholds(self, utilization_threshold=None, temperature_threshold=None, memory_threshold=None, error_duration_threshold=None):
        """设置异常检测阈值"""
        with self._lock:
            if utilization_threshold is not None:
                self.utilization_threshold = utilization_threshold
            if temperature_threshold is not None:
                self.temperature_threshold = temperature_threshold
            if memory_threshold is not None:
                self.memory_threshold = memory_threshold
            if error_duration_threshold is not None:
                self.error_duration_threshold = error_duration_threshold


# 全局GPU监控器实例
GPUMonitorInstance = GPUMonitor()