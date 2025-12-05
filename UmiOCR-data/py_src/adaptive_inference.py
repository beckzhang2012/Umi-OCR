# ===============================================
# =============== 自适应推理调度器 ===============
# ===============================================

"""
CPU/GPU自适应推理调度器

功能特性:
1. 启动时自动检测可用GPU，多卡场景支持配置优先级
2. 运行过程中实时监控GPU状态，异常时自动切换到CPU
3. CPU模式支持多进程/多线程混合策略，保持高吞吐
4. 提供统一的配置管理和状态上报
5. 支持GPU恢复后自动切换回GPU模式

使用示例:
```python
from adaptive_inference import AdaptiveInferenceScheduler

# 初始化调度器
scheduler = AdaptiveInferenceScheduler()

# 启动调度器
scheduler.start(ocr_api, "test_ocr_api")

# 运行OCR任务
result = scheduler.run_ocr(image_data)

# 获取当前状态
state = scheduler.get_state()

# 停止调度器
scheduler.stop()
```
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from umi_log import logger

# 导入子模块
from .platform.hardware_detector import HardwareDetector
from .monitoring.gpu_monitor import GPUMonitor
from .scheduler.adaptive_inference_scheduler import AdaptiveInferenceScheduler as SchedulerCore
from .config.adaptive_scheduler_config import ConfigManager, AdaptiveSchedulerConfig
from .state.adaptive_scheduler_state import StateManager, BackendType, SwitchReason, format_state_for_ui


class AdaptiveInferenceScheduler:
    """自适应推理调度器主类"""
    
    _instance: Optional['AdaptiveInferenceScheduler'] = None
    
    @classmethod
    def get_instance(cls) -> 'AdaptiveInferenceScheduler':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化"""
        if AdaptiveInferenceScheduler._instance is not None:
            raise RuntimeError("AdaptiveInferenceScheduler是单例类，请使用get_instance()获取实例")
        AdaptiveInferenceScheduler._instance = self
        
        # 核心组件
        self._hardware_detector = HardwareDetector()
        self._gpu_monitor = GPUMonitor()
        self._config_manager = ConfigManager.get_instance()
        self._state_manager = StateManager.get_instance()
        self._scheduler_core: Optional[SchedulerCore] = None
        
        # 回调函数
        self._backend_switch_callback: Optional[Callable[[str, str], None]] = None
        self._status_update_callback: Optional[Callable[[Dict], None]] = None
        
        # 运行状态
        self._is_running = False
        self._lock = threading.Lock()
        
        # 注册GPU监控回调
        self._gpu_monitor.register_callback(self._on_gpu_status_update)
    
    def _on_gpu_status_update(self, gpu_status: Dict):
        """GPU状态更新回调"""
        from .state.adaptive_scheduler_state import GPUStatus
        
        # 更新状态管理器中的GPU状态
        gpu_status_obj = GPUStatus(
            utilization=gpu_status.get('utilization', 0),
            temperature=gpu_status.get('temperature', 0),
            memory_used=gpu_status.get('memory_used', 0),
            memory_total=gpu_status.get('memory_total', 0),
            memory_utilization=gpu_status.get('memory_utilization', 0),
            driver_version=gpu_status.get('driver_version', ''),
            has_error=gpu_status.get('has_error', False),
            error_message=gpu_status.get('error_message', '')
        )
        self._state_manager.update_gpu_status(gpu_status_obj)
    
    def _on_backend_switch(self, backend: BackendType, reason: SwitchReason):
        """后端切换回调"""
        # 更新状态管理器
        self._state_manager.update_backend_status(backend, reason)
        
        # 调用用户回调
        if self._backend_switch_callback:
            try:
                self._backend_switch_callback(backend.value, reason.value)
            except Exception as e:
                logger.error(f"后端切换回调执行失败: {e}")
    
    def _on_status_update(self, status: Dict):
        """状态更新回调"""
        # 调用用户回调
        if self._status_update_callback:
            try:
                self._status_update_callback(status)
            except Exception as e:
                logger.error(f"状态更新回调执行失败: {e}")
    
    def start(self, ocr_api: Any, api_name: str = "default"):
        """启动自适应推理调度器"""
        with self._lock:
            if self._is_running:
                logger.warning("自适应推理调度器已经在运行中")
                return
            
            logger.info("启动自适应推理调度器...")
            
            # 1. 检测硬件信息
            logger.info("步骤1: 检测硬件信息")
            hardware_info = self._hardware_detector.detect_hardware()
            
            from .state.adaptive_scheduler_state import HardwareInfo
            hardware_info_obj = HardwareInfo(
                gpu_available=hardware_info.get('gpu_available', False),
                gpu_count=hardware_info.get('gpu_count', 0),
                gpu_models=hardware_info.get('gpu_models', []),
                cpu_count=hardware_info.get('cpu_count', 0),
                cpu_model=hardware_info.get('cpu_model', ''),
                system_memory=hardware_info.get('system_memory', 0)
            )
            self._state_manager.update_hardware_info(hardware_info_obj)
            
            logger.info(f"硬件检测结果: {hardware_info}")
            
            # 2. 初始化调度器核心
            logger.info("步骤2: 初始化调度器核心")
            self._scheduler_core = SchedulerCore()
            
            # 注册回调
            self._scheduler_core.on_backend_switch = self._on_backend_switch
            self._scheduler_core.on_status_update = self._on_status_update
            
            # 3. 启动GPU监控
            logger.info("步骤3: 启动GPU监控")
            self._gpu_monitor.start()
            
            # 4. 启动调度器
            logger.info("步骤4: 启动调度器")
            self._scheduler_core.start(ocr_api, api_name)
            
            # 5. 更新运行状态
            self._is_running = True
            self._state_manager.set_running_state(True)
            
            logger.info("自适应推理调度器启动完成")
    
    def stop(self):
        """停止自适应推理调度器"""
        with self._lock:
            if not self._is_running:
                logger.warning("自适应推理调度器已经停止")
                return
            
            logger.info("停止自适应推理调度器...")
            
            # 1. 停止调度器核心
            if self._scheduler_core:
                self._scheduler_core.stop()
                self._scheduler_core = None
            
            # 2. 停止GPU监控
            self._gpu_monitor.stop()
            
            # 3. 更新运行状态
            self._is_running = False
            self._state_manager.set_running_state(False)
            
            logger.info("自适应推理调度器停止完成")
    
    def run_ocr(self, image_data: Any, **kwargs) -> Dict:
        """运行OCR任务"""
        if not self._is_running or not self._scheduler_core:
            raise RuntimeError("自适应推理调度器未启动")
        
        try:
            result = self._scheduler_core.run_ocr(image_data, **kwargs)
            
            # 更新性能指标
            if result.get('code') == 100:
                self._state_manager.update_performance_metrics(
                    task_count=1,
                    successful=1,
                    processing_time=result.get('processing_time', 0.0)
                )
            else:
                self._state_manager.update_performance_metrics(
                    task_count=1,
                    failed=1
                )
            
            return result
        except Exception as e:
            logger.error(f"OCR任务执行失败: {e}")
            self._state_manager.update_performance_metrics(
                task_count=1,
                failed=1
            )
            raise
    
    def get_state(self) -> Dict:
        """获取当前状态"""
        return self._state_manager.get_state_dict()
    
    def get_ui_state(self) -> Dict:
        """获取用于UI显示的状态"""
        return format_state_for_ui(self.get_state())
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        return self._state_manager.get_performance_summary()
    
    def get_hardware_summary(self) -> Dict:
        """获取硬件摘要"""
        return self._state_manager.get_hardware_summary()
    
    def get_current_backend(self) -> str:
        """获取当前后端类型"""
        return self._state_manager.get_current_backend().value
    
    def get_switch_reason(self) -> str:
        """获取最后一次切换原因"""
        return self._state_manager.get_switch_reason().value
    
    def is_gpu_available(self) -> bool:
        """检查GPU是否可用"""
        return self._state_manager.is_gpu_available()
    
    def is_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._is_running
    
    def get_config(self) -> AdaptiveSchedulerConfig:
        """获取当前配置"""
        return self._config_manager.get_config()
    
    def update_config(self, config_updates: Dict):
        """更新配置"""
        self._config_manager.update_config(config_updates)
        
        # 如果调度器正在运行，应用新配置
        if self._is_running and self._scheduler_core:
            self._scheduler_core.update_config()
    
    def save_config(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        self._config_manager.save_config(config_file)
    
    def load_config(self, config_file: Optional[str] = None):
        """从文件加载配置"""
        self._config_manager.load_config(config_file)
    
    def register_backend_switch_callback(self, callback: Callable[[str, str], None]):
        """注册后端切换回调"""
        self._backend_switch_callback = callback
    
    def register_status_update_callback(self, callback: Callable[[Dict], None]):
        """注册状态更新回调"""
        self._status_update_callback = callback
    
    def switch_backend(self, backend_type: str, reason: str = "手动切换"):
        """手动切换后端"""
        if not self._is_running or not self._scheduler_core:
            raise RuntimeError("自适应推理调度器未启动")
        
        try:
            backend = BackendType(backend_type.upper())
            switch_reason = SwitchReason.MANUAL_SWITCH
            
            self._scheduler_core.switch_backend(backend, switch_reason)
            logger.info(f"手动切换后端到{backend_type}")
        except ValueError:
            raise ValueError(f"无效的后端类型: {backend_type}，必须是GPU或CPU")
    
    def reset_state(self):
        """重置状态"""
        self._state_manager.reset()
    
    def get_gpu_status(self) -> Dict:
        """获取GPU状态"""
        return self._gpu_monitor.get_status()


# 全局实例
adaptive_inference = AdaptiveInferenceScheduler.get_instance()


# 便捷函数
def start_adaptive_inference(ocr_api: Any, api_name: str = "default"):
    """启动自适应推理"""
    adaptive_inference.start(ocr_api, api_name)


def stop_adaptive_inference():
    """停止自适应推理"""
    adaptive_inference.stop()


def run_ocr_task(image_data: Any, **kwargs) -> Dict:
    """运行OCR任务"""
    return adaptive_inference.run_ocr(image_data, **kwargs)


def get_adaptive_inference_state() -> Dict:
    """获取自适应推理状态"""
    return adaptive_inference.get_state()


def get_adaptive_inference_ui_state() -> Dict:
    """获取自适应推理UI状态"""
    return adaptive_inference.get_ui_state()


def update_adaptive_inference_config(config_updates: Dict):
    """更新自适应推理配置"""
    adaptive_inference.update_config(config_updates)


def switch_adaptive_inference_backend(backend_type: str):
    """切换自适应推理后端"""
    adaptive_inference.switch_backend(backend_type)


# 模块导出
__all__ = [
    'AdaptiveInferenceScheduler',
    'adaptive_inference',
    'start_adaptive_inference',
    'stop_adaptive_inference',
    'run_ocr_task',
    'get_adaptive_inference_state',
    'get_adaptive_inference_ui_state',
    'update_adaptive_inference_config',
    'switch_adaptive_inference_backend',
    'BackendType',
    'SwitchReason'
]