# ===============================================
# =============== 自适应推理调度器 ===============
# ===============================================

import threading
import time
from enum import Enum
from umi_log import logger
from ..platform.hardware_detector import HardwareDetectorInstance
from ..monitoring.gpu_monitor import GPUMonitorInstance


class InferenceBackend(Enum):
    """推理后端类型"""
    GPU = "GPU"
    CPU = "CPU"
    AUTO = "AUTO"


class SchedulerState(Enum):
    """调度器状态"""
    INITIALIZING = "INITIALIZING"
    GPU_MODE = "GPU_MODE"
    CPU_MODE = "CPU_MODE"
    SWITCHING = "SWITCHING"


class AdaptiveInferenceScheduler:
    """自适应推理调度器，用于实现CPU/GPU自适应推理调度"""

    def __init__(self):
        """初始化自适应推理调度器"""
        self._lock = threading.Lock()
        self._state = SchedulerState.INITIALIZING
        self._current_backend = InferenceBackend.AUTO
        self._switch_reason = ""
        self._last_switch_time = 0
        self._retry_gpu_interval = 60  # GPU恢复重试间隔（秒）

        # 硬件信息
        self._hardware_info = None
        self._available_gpus = []
        self._selected_gpu_id = 0

        # CPU模式配置
        self._cpu_thread_count = None  # CPU线程数，None表示自动选择
        self._cpu_process_count = 1  # CPU进程数
        self._cpu_throughput_target = 0.85  # CPU模式吞吐目标（相对于GPU模式）

        # 回调函数
        self.on_backend_switch = None  # 后端切换时的回调
        self.on_status_update = None  # 状态更新时的回调

        # OCR API实例
        self._ocr_api = None
        self._ocr_api_key = ""

    def _detect_hardware(self):
        """检测硬件信息"""
        logger.info("开始检测硬件信息...")
        self._hardware_info = HardwareDetectorInstance.detect_hardware()
        self._available_gpus = self._hardware_info.get("gpu", [])

        logger.info(f"检测到GPU数量: {len(self._available_gpus)}")
        for gpu in self._available_gpus:
            logger.info(f"  GPU {gpu['id']}: {gpu['name']}, 显存: {gpu['memory_total']}MB")

        cpu_info = self._hardware_info.get("cpu", {})
        logger.info(f"CPU信息: {cpu_info.get('name', '未知')}")
        logger.info(f"  物理核心数: {cpu_info.get('physical_cores', 0)}")
        logger.info(f"  逻辑核心数: {cpu_info.get('logical_cores', 0)}")

        # 自动选择CPU线程数
        if self._cpu_thread_count is None:
            self._cpu_thread_count = cpu_info.get("logical_cores", 4)
            logger.info(f"自动选择CPU线程数: {self._cpu_thread_count}")

    def _initialize_gpu_monitor(self):
        """初始化GPU监控"""
        if self._available_gpus:
            GPUMonitorInstance.gpu_id = self._selected_gpu_id
            GPUMonitorInstance.on_gpu_exception = self._on_gpu_exception
            GPUMonitorInstance.on_gpu_recovered = self._on_gpu_recovered
            GPUMonitorInstance.start()
            logger.info(f"GPU监控已初始化，监控GPU ID: {self._selected_gpu_id}")
        else:
            logger.warning("未检测到可用GPU，跳过GPU监控初始化")

    def _select_initial_backend(self):
        """选择初始推理后端"""
        logger.info("选择初始推理后端...")

        # 如果有可用GPU，优先选择GPU模式
        if self._available_gpus:
            self._current_backend = InferenceBackend.GPU
            self._state = SchedulerState.GPU_MODE
            logger.info("初始后端选择: GPU")
        else:
            self._current_backend = InferenceBackend.CPU
            self._state = SchedulerState.CPU_MODE
            logger.warning("未检测到可用GPU，初始后端选择: CPU")

        return self._current_backend

    def _switch_to_cpu(self, reason=""):
        """切换到CPU模式"""
        with self._lock:
            if self._state == SchedulerState.CPU_MODE:
                return  # 已经是CPU模式

            self._state = SchedulerState.SWITCHING
            self._switch_reason = reason
            self._last_switch_time = time.time()

        logger.info(f"正在切换到CPU模式，原因: {reason}")

        # 停止GPU监控
        GPUMonitorInstance.stop()

        # 切换OCR后端到CPU
        if self._ocr_api:
            try:
                # TODO: 实现OCR后端切换逻辑
                self._ocr_api.switch_backend(InferenceBackend.CPU.value, {
                    "thread_count": self._cpu_thread_count,
                    "process_count": self._cpu_process_count
                })
                logger.info("OCR后端已切换到CPU模式")
            except Exception as e:
                logger.error(f"切换OCR后端到CPU模式失败: {e}")

        with self._lock:
            self._current_backend = InferenceBackend.CPU
            self._state = SchedulerState.CPU_MODE

        # 触发回调
        if self.on_backend_switch:
            self.on_backend_switch(InferenceBackend.CPU, reason)

        # 记录日志
        logger.info(f"已切换到CPU模式，原因: {reason}")

    def _switch_to_gpu(self, reason=""):
        """切换到GPU模式"""
        with self._lock:
            if self._state == SchedulerState.GPU_MODE:
                return  # 已经是GPU模式

            self._state = SchedulerState.SWITCHING
            self._switch_reason = reason
            self._last_switch_time = time.time()

        logger.info(f"正在切换到GPU模式，原因: {reason}")

        # 初始化GPU监控
        self._initialize_gpu_monitor()

        # 切换OCR后端到GPU
        if self._ocr_api:
            try:
                # TODO: 实现OCR后端切换逻辑
                self._ocr_api.switch_backend(InferenceBackend.GPU.value, {
                    "gpu_id": self._selected_gpu_id
                })
                logger.info("OCR后端已切换到GPU模式")
            except Exception as e:
                logger.error(f"切换OCR后端到GPU模式失败: {e}")
                # 切换失败，回退到CPU模式
                self._switch_to_cpu(f"切换GPU模式失败: {e}")
                return

        with self._lock:
            self._current_backend = InferenceBackend.GPU
            self._state = SchedulerState.GPU_MODE

        # 触发回调
        if self.on_backend_switch:
            self.on_backend_switch(InferenceBackend.GPU, reason)

        # 记录日志
        logger.info(f"已切换到GPU模式，原因: {reason}")

    def _on_gpu_exception(self, reason):
        """GPU异常回调"""
        logger.error(f"GPU异常，准备切换到CPU模式: {reason}")
        self._switch_to_cpu(reason)

    def _on_gpu_recovered(self):
        """GPU恢复回调"""
        logger.info("GPU已恢复正常，准备切换回GPU模式")
        self._switch_to_gpu("GPU已恢复正常")

    def _retry_gpu_periodically(self):
        """定期重试GPU模式"""
        while True:
            time.sleep(self._retry_gpu_interval)

            with self._lock:
                if self._state != SchedulerState.CPU_MODE:
                    continue  # 不是CPU模式，不需要重试

                # 检查是否可以重试GPU
                if time.time() - self._last_switch_time < self._retry_gpu_interval:
                    continue

            logger.info("正在重试GPU模式...")

            # 重新检测GPU
            new_gpu_info = HardwareDetectorInstance.get_gpu_info()
            if new_gpu_info:
                self._available_gpus = new_gpu_info
                self._switch_to_gpu("GPU重试成功")
            else:
                logger.warning("GPU重试失败，未检测到可用GPU")

    def start(self, ocr_api=None, ocr_api_key=""):
        """启动自适应推理调度器"""
        logger.info("启动自适应推理调度器...")

        with self._lock:
            if self._state != SchedulerState.INITIALIZING:
                logger.warning("自适应推理调度器已经在运行中")
                return

        # 保存OCR API实例
        self._ocr_api = ocr_api
        self._ocr_api_key = ocr_api_key

        # 检测硬件
        self._detect_hardware()

        # 选择初始后端
        self._select_initial_backend()

        # 初始化GPU监控（如果是GPU模式）
        if self._current_backend == InferenceBackend.GPU:
            self._initialize_gpu_monitor()

        # 启动定期重试GPU线程
        retry_thread = threading.Thread(target=self._retry_gpu_periodically, daemon=True)
        retry_thread.start()

        logger.info("自适应推理调度器已启动")

        # 触发状态更新回调
        if self.on_status_update:
            self.on_status_update(self.get_status())

    def stop(self):
        """停止自适应推理调度器"""
        logger.info("停止自适应推理调度器...")

        with self._lock:
            self._state = SchedulerState.INITIALIZING

        # 停止GPU监控
        GPUMonitorInstance.stop()

        logger.info("自适应推理调度器已停止")

    def get_status(self):
        """获取调度器状态"""
        with self._lock:
            status = {
                "state": self._state.value,
                "current_backend": self._current_backend.value,
                "switch_reason": self._switch_reason,
                "last_switch_time": self._last_switch_time,
                "available_gpus": len(self._available_gpus),
                "selected_gpu_id": self._selected_gpu_id,
                "cpu_thread_count": self._cpu_thread_count,
                "cpu_process_count": self._cpu_process_count,
                "retry_gpu_interval": self._retry_gpu_interval
            }

            # 添加GPU状态信息
            if self._current_backend == InferenceBackend.GPU:
                status["gpu_status"] = GPUMonitorInstance.get_status()

            # 添加CPU信息
            if self._hardware_info and "cpu" in self._hardware_info:
                status["cpu_info"] = self._hardware_info["cpu"]

            return status

    def set_cpu_config(self, thread_count=None, process_count=None):
        """设置CPU模式配置"""
        with self._lock:
            if thread_count is not None:
                self._cpu_thread_count = thread_count
                logger.info(f"CPU线程数已设置为: {thread_count}")

            if process_count is not None:
                self._cpu_process_count = process_count
                logger.info(f"CPU进程数已设置为: {process_count}")

        # 如果当前是CPU模式，更新OCR配置
        if self._current_backend == InferenceBackend.CPU and self._ocr_api:
            try:
                self._ocr_api.update_cpu_config({
                    "thread_count": self._cpu_thread_count,
                    "process_count": self._cpu_process_count
                })
                logger.info("CPU模式配置已更新")
            except Exception as e:
                logger.error(f"更新CPU模式配置失败: {e}")

    def set_retry_interval(self, interval):
        """设置GPU重试间隔"""
        with self._lock:
            self._retry_gpu_interval = interval
            logger.info(f"GPU重试间隔已设置为: {interval}秒")

    def force_switch_backend(self, backend):
        """强制切换推理后端"""
        if not isinstance(backend, InferenceBackend):
            raise ValueError("backend必须是InferenceBackend枚举类型")

        if backend == InferenceBackend.GPU:
            self._switch_to_gpu("手动切换")
        elif backend == InferenceBackend.CPU:
            self._switch_to_cpu("手动切换")


# 全局自适应推理调度器实例
AdaptiveInferenceSchedulerInstance = AdaptiveInferenceScheduler()