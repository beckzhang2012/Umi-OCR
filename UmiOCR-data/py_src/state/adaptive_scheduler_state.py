# ===============================================
# =============== 自适应调度器状态管理 ===============
# ===============================================

import time
import threading
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from umi_log import logger


class BackendType(Enum):
    """后端类型"""
    GPU = "GPU"
    CPU = "CPU"
    AUTO = "AUTO"


class SwitchReason(Enum):
    """切换原因"""
    STARTUP = "启动时自动选择"
    GPU_NOT_AVAILABLE = "GPU不可用"
    GPU_UTILIZATION_HIGH = "GPU占用率过高"
    GPU_TEMPERATURE_HIGH = "GPU温度过高"
    GPU_MEMORY_HIGH = "GPU显存占用过高"
    GPU_DRIVER_ERROR = "GPU驱动错误"
    GPU_RECOVERED = "GPU已恢复"
    MANUAL_SWITCH = "手动切换"
    TEST_MODE = "测试模式"


@dataclass
class HardwareInfo:
    """硬件信息"""
    gpu_available: bool = False
    gpu_count: int = 0
    gpu_models: List[str] = field(default_factory=list)
    cpu_count: int = 0
    cpu_model: str = ""
    system_memory: int = 0  # MB


@dataclass
class GPUStatus:
    """GPU状态"""
    utilization: int = 0  # %
    temperature: int = 0  # °C
    memory_used: int = 0  # MB
    memory_total: int = 0  # MB
    memory_utilization: int = 0  # %
    driver_version: str = ""
    has_error: bool = False
    error_message: str = ""


@dataclass
class CPUStatus:
    """CPU状态"""
    utilization: int = 0  # %
    temperature: int = 0  # °C
    memory_used: int = 0  # MB
    memory_total: int = 0  # MB
    threads_active: int = 0
    processes_active: int = 0


@dataclass
class BackendStatus:
    """后端状态"""
    current_backend: BackendType = BackendType.AUTO
    switch_reason: SwitchReason = SwitchReason.STARTUP
    switch_time: float = 0.0
    gpu_enabled: bool = True
    cpu_config: Dict = field(default_factory=dict)
    gpu_config: Dict = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_processing_time: float = 0.0  # 秒
    tasks_per_second: float = 0.0
    last_task_time: float = 0.0


@dataclass
class SchedulerState:
    """调度器状态"""
    # 硬件信息
    hardware: HardwareInfo = field(default_factory=HardwareInfo)
    
    # GPU状态
    gpu_status: GPUStatus = field(default_factory=GPUStatus)
    
    # CPU状态
    cpu_status: CPUStatus = field(default_factory=CPUStatus)
    
    # 后端状态
    backend: BackendStatus = field(default_factory=BackendStatus)
    
    # 性能指标
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # 调度器状态
    is_running: bool = False
    last_updated: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        
        # 转换枚举类型为字符串
        data['backend']['current_backend'] = self.backend.current_backend.value
        data['backend']['switch_reason'] = self.backend.switch_reason.value
        
        return data


class StateManager:
    """状态管理器"""
    
    _instance: Optional['StateManager'] = None
    _state: SchedulerState
    _lock: threading.Lock
    _callbacks: List[Callable[[Dict], None]]
    
    @classmethod
    def get_instance(cls) -> 'StateManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化"""
        if StateManager._instance is not None:
            raise RuntimeError("StateManager是单例类，请使用get_instance()获取实例")
        StateManager._instance = self
        
        self._state = SchedulerState()
        self._lock = threading.Lock()
        self._callbacks = []
    
    def get_state(self) -> SchedulerState:
        """获取当前状态"""
        with self._lock:
            return self._state
    
    def get_state_dict(self) -> Dict:
        """获取当前状态的字典表示"""
        with self._lock:
            return self._state.to_dict()
    
    def update_hardware_info(self, hardware_info: HardwareInfo):
        """更新硬件信息"""
        with self._lock:
            self._state.hardware = hardware_info
            self._state.last_updated = time.time()
        self._notify_callbacks()
    
    def update_gpu_status(self, gpu_status: GPUStatus):
        """更新GPU状态"""
        with self._lock:
            self._state.gpu_status = gpu_status
            self._state.last_updated = time.time()
        self._notify_callbacks()
    
    def update_cpu_status(self, cpu_status: CPUStatus):
        """更新CPU状态"""
        with self._lock:
            self._state.cpu_status = cpu_status
            self._state.last_updated = time.time()
        self._notify_callbacks()
    
    def update_backend_status(self, backend_type: BackendType, reason: SwitchReason, 
                            gpu_enabled: bool = True, cpu_config: Optional[Dict] = None, 
                            gpu_config: Optional[Dict] = None):
        """更新后端状态"""
        with self._lock:
            self._state.backend.current_backend = backend_type
            self._state.backend.switch_reason = reason
            self._state.backend.switch_time = time.time()
            self._state.backend.gpu_enabled = gpu_enabled
            
            if cpu_config:
                self._state.backend.cpu_config.update(cpu_config)
            if gpu_config:
                self._state.backend.gpu_config.update(gpu_config)
            
            self._state.last_updated = time.time()
        
        logger.info(f"后端已切换到{backend_type.value}，原因: {reason.value}")
        self._notify_callbacks()
    
    def update_performance_metrics(self, task_count: int = 0, successful: int = 0, 
                                 failed: int = 0, processing_time: float = 0.0):
        """更新性能指标"""
        with self._lock:
            self._state.performance.total_tasks += task_count
            self._state.performance.successful_tasks += successful
            self._state.performance.failed_tasks += failed
            
            # 更新平均处理时间
            if task_count > 0:
                total_time = self._state.performance.avg_processing_time * self._state.performance.total_tasks
                total_time += processing_time * task_count
                self._state.performance.avg_processing_time = total_time / self._state.performance.total_tasks
            
            # 更新处理速度
            current_time = time.time()
            if self._state.performance.last_task_time > 0 and current_time > self._state.performance.last_task_time:
                time_diff = current_time - self._state.performance.last_task_time
                self._state.performance.tasks_per_second = task_count / time_diff
            
            self._state.performance.last_task_time = current_time
            self._state.last_updated = time.time()
        
        self._notify_callbacks()
    
    def set_running_state(self, is_running: bool):
        """设置运行状态"""
        with self._lock:
            self._state.is_running = is_running
            self._state.last_updated = time.time()
        self._notify_callbacks()
    
    def register_callback(self, callback: Callable[[Dict], None]):
        """注册状态更新回调"""
        with self._lock:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[Dict], None]):
        """取消注册状态更新回调"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """通知所有回调函数"""
        state_dict = self.get_state_dict()
        
        # 复制回调列表以防止在回调中修改列表
        callbacks = None
        with self._lock:
            callbacks = self._callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(state_dict)
            except Exception as e:
                logger.error(f"状态更新回调执行失败: {e}")
    
    def get_current_backend(self) -> BackendType:
        """获取当前后端类型"""
        with self._lock:
            return self._state.backend.current_backend
    
    def get_switch_reason(self) -> SwitchReason:
        """获取最后一次切换原因"""
        with self._lock:
            return self._state.backend.switch_reason
    
    def get_switch_time(self) -> float:
        """获取最后一次切换时间"""
        with self._lock:
            return self._state.backend.switch_time
    
    def is_gpu_available(self) -> bool:
        """检查GPU是否可用"""
        with self._lock:
            return self._state.hardware.gpu_available
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        with self._lock:
            performance = self._state.performance
            success_rate = (performance.successful_tasks / performance.total_tasks * 100) if performance.total_tasks > 0 else 0
            
            return {
                "total_tasks": performance.total_tasks,
                "successful_tasks": performance.successful_tasks,
                "failed_tasks": performance.failed_tasks,
                "success_rate": success_rate,
                "avg_processing_time": performance.avg_processing_time,
                "tasks_per_second": performance.tasks_per_second
            }
    
    def get_hardware_summary(self) -> Dict:
        """获取硬件摘要"""
        with self._lock:
            hardware = self._state.hardware
            return {
                "gpu_available": hardware.gpu_available,
                "gpu_count": hardware.gpu_count,
                "gpu_models": hardware.gpu_models,
                "cpu_count": hardware.cpu_count,
                "cpu_model": hardware.cpu_model,
                "system_memory": hardware.system_memory
            }
    
    def reset(self):
        """重置状态"""
        with self._lock:
            self._state = SchedulerState()
        self._notify_callbacks()


# 全局状态实例
state_manager = StateManager.get_instance()


# 辅助函数
def format_state_for_ui(state_dict: Dict) -> Dict:
    """格式化状态数据用于UI显示"""
    formatted = {
        "current_backend": state_dict["backend"]["current_backend"],
        "switch_reason": state_dict["backend"]["switch_reason"],
        "switch_time": time.strftime("%H:%M:%S", time.localtime(state_dict["backend"]["switch_time"])),
        "gpu_available": state_dict["hardware"]["gpu_available"],
        "gpu_count": state_dict["hardware"]["gpu_count"],
        "cpu_count": state_dict["hardware"]["cpu_count"],
        "is_running": state_dict["is_running"],
        "last_updated": time.strftime("%H:%M:%S", time.localtime(state_dict["last_updated"])),
        
        # GPU状态
        "gpu_utilization": f"{state_dict['gpu_status']['utilization']}%",
        "gpu_temperature": f"{state_dict['gpu_status']['temperature']}°C",
        "gpu_memory": f"{state_dict['gpu_status']['memory_used']}/{state_dict['gpu_status']['memory_total']}MB "
                       f"({state_dict['gpu_status']['memory_utilization']}%)",
        "gpu_has_error": state_dict["gpu_status"]["has_error"],
        
        # CPU状态
        "cpu_utilization": f"{state_dict['cpu_status']['utilization']}%",
        "cpu_memory": f"{state_dict['cpu_status']['memory_used']}/{state_dict['cpu_status']['memory_total']}MB",
        "cpu_threads": state_dict["cpu_status"]["threads_active"],
        
        # 性能指标
        "total_tasks": state_dict["performance"]["total_tasks"],
        "successful_tasks": state_dict["performance"]["successful_tasks"],
        "failed_tasks": state_dict["performance"]["failed_tasks"],
        "avg_processing_time": f"{state_dict['performance']['avg_processing_time']:.3f}s",
        "tasks_per_second": f"{state_dict['performance']['tasks_per_second']:.2f}"
    }
    
    # 添加预计恢复时间（如果当前是CPU模式且GPU可能恢复）
    if state_dict["backend"]["current_backend"] == "CPU" and state_dict["hardware"]["gpu_available"]:
        # 简单估计：假设每30秒检查一次恢复
        time_since_switch = time.time() - state_dict["backend"]["switch_time"]
        next_check_in = 30 - (time_since_switch % 30)
        formatted["estimated_recovery_check"] = f"{next_check_in:.0f}秒后检查GPU恢复"
    
    return formatted


def get_state_summary() -> Dict:
    """获取状态摘要"""
    return state_manager.get_state_dict()


def get_ui_state() -> Dict:
    """获取用于UI显示的状态"""
    state_dict = state_manager.get_state_dict()
    return format_state_for_ui(state_dict)