# ===============================================
# =============== 硬件调度器 ===============
# ===============================================

from PySide2.QtCore import QObject, Slot, Signal
from enum import Enum
import psutil
import GPUtil
import time
from ..event_bus.pubsub_service import PubSubService
from umi_log import logger


class BackendType(Enum):
    """后端类型枚举"""
    CPU = "cpu"
    GPU = "gpu"
    AUTO = "auto"


class GPUStatus(Enum):
    """GPU状态枚举"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class HardwareScheduler(QObject):
    """硬件调度器"""

    # 信号：后端切换
    backendSwitched = Signal(str, str)  # 旧后端, 新后端

    # 信号：GPU状态变化
    gpuStatusChanged = Signal(str)  # 新状态

    def __init__(self):
        super().__init__()
        self._current_backend = BackendType.CPU
        self._target_backend = BackendType.AUTO
        self._gpu_status = GPUStatus.UNKNOWN
        self._gpu_memory_available = 0
        self._last_check_time = 0
        self._check_interval = 5  # 检查间隔（秒）

        # 初始化GPU状态
        self._check_gpu_status()

        # 订阅任务事件
        PubSubService.subscribeGroup("HardwareScheduler", self.onTaskStarted, "TaskStarted")
        PubSubService.subscribeGroup("HardwareScheduler", self.onTaskCompleted, "TaskCompleted")
        PubSubService.subscribeGroup("HardwareScheduler", self.onTaskFailed, "TaskFailed")

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    @property
    def current_backend(self):
        """获取当前后端"""
        return self._current_backend

    @property
    def target_backend(self):
        """获取目标后端"""
        return self._target_backend

    @property
    def gpu_status(self):
        """获取GPU状态"""
        return self._gpu_status

    @property
    def gpu_memory_available(self):
        """获取可用GPU内存"""
        return self._gpu_memory_available

    @Slot(str)
    def set_target_backend(self, backend):
        """设置目标后端"""
        try:
            self._target_backend = BackendType(backend)
            logger.info(f"目标后端已设置为: {backend}")
            # 立即检查并切换后端
            self._check_and_switch_backend()
        except ValueError:
            logger.error(f"无效的后端类型: {backend}")

    def _check_gpu_status(self):
        """检查GPU状态"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                self._gpu_status = GPUStatus.AVAILABLE
                self._gpu_memory_available = gpus[0].memoryFree
                logger.info(f"GPU可用，可用内存: {self._gpu_memory_available}MB")
            else:
                self._gpu_status = GPUStatus.UNAVAILABLE
                self._gpu_memory_available = 0
                logger.warning("未检测到可用GPU")
        except Exception as e:
            self._gpu_status = GPUStatus.UNAVAILABLE
            self._gpu_memory_available = 0
            logger.error(f"检查GPU状态失败: {e}")

        # 发送GPU状态变化信号
        self.gpuStatusChanged.emit(self._gpu_status.value)

    def _check_and_switch_backend(self):
        """检查并切换后端"""
        current_time = time.time()
        if current_time - self._last_check_time < self._check_interval:
            return

        self._last_check_time = current_time

        # 检查GPU状态
        self._check_gpu_status()

        # 根据目标后端和硬件状态选择最佳后端
        if self._target_backend == BackendType.AUTO:
            # 自动模式：优先使用GPU，如果GPU不可用则使用CPU
            if self._gpu_status == GPUStatus.AVAILABLE:
                new_backend = BackendType.GPU
            else:
                new_backend = BackendType.CPU
        else:
            # 手动模式：使用指定的后端
            new_backend = self._target_backend

        # 如果后端发生变化，则切换后端
        if new_backend != self._current_backend:
            old_backend = self._current_backend
            self._current_backend = new_backend
            logger.info(f"后端已切换: {old_backend.value} -> {new_backend.value}")
            # 发送后端切换信号
            self.backendSwitched.emit(old_backend.value, new_backend.value)
            # 发布后端切换事件
            PubSubService.publish("BackendSwitched", {
                "old_backend": old_backend.value,
                "new_backend": new_backend.value
            })

    def onTaskStarted(self):
        """任务开始事件处理"""
        # 任务开始时检查并切换后端
        self._check_and_switch_backend()

    def onTaskCompleted(self):
        """任务完成事件处理"""
        # 任务完成时检查并切换后端
        self._check_and_switch_backend()

    def onTaskFailed(self):
        """任务失败事件处理"""
        # 任务失败时检查并切换后端
        self._check_and_switch_backend()

    @Slot(result=str)
    def get_current_backend(self):
        """获取当前后端（供QML调用）"""
        return self._current_backend.value

    @Slot(result=str)
    def get_target_backend(self):
        """获取目标后端（供QML调用）"""
        return self._target_backend.value

    @Slot(result=str)
    def get_gpu_status(self):
        """获取GPU状态（供QML调用）"""
        return self._gpu_status.value

    @Slot(result=int)
    def get_gpu_memory_available(self):
        """获取可用GPU内存（供QML调用）"""
        return self._gpu_memory_available

    @Slot(result=dict)
    def get_hardware_info(self):
        """获取硬件信息"""
        try:
            # CPU信息
            cpu_info = {
                "count": psutil.cpu_count(),
                "usage": psutil.cpu_percent(interval=0.1)
            }

            # 内存信息
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "usage": memory.percent
            }

            # 磁盘信息
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": disk.total,
                "available": disk.free,
                "usage": disk.percent
            }

            # GPU信息
            gpu_info = {
                "status": self._gpu_status.value,
                "memory_available": self._gpu_memory_available
            }

            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "gpu": gpu_info,
                "current_backend": self._current_backend.value,
                "target_backend": self._target_backend.value
            }
        except Exception as e:
            logger.error(f"获取硬件信息失败: {e}")
            return {}
