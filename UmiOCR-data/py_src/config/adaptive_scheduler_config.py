# ===============================================
# =============== 自适应调度器配置 ===============
# ===============================================

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from umi_log import logger


@dataclass
class GPUThresholdConfig:
    """GPU阈值配置"""
    utilization_threshold: int = 85  # GPU占用率阈值(%)
    temperature_threshold: int = 90  # GPU温度阈值(°C)
    memory_threshold: int = 90       # GPU显存占用阈值(%)
    threshold_duration: int = 10     # 超过阈值持续时间(秒)
    retry_interval: int = 60         # 重试间隔(秒)
    recovery_check_interval: int = 30  # 恢复检查间隔(秒)


@dataclass
class CPUConfig:
    """CPU配置"""
    enable_multiprocessing: bool = True  # 是否启用多进程
    enable_multithreading: bool = True  # 是否启用多线程
    max_workers: Optional[int] = None    # 最大工作进程数，None表示自动检测
    threads_per_worker: int = 4         # 每个工作进程的线程数
    queue_size: int = 100               # 任务队列大小
    batch_size: int = 8                 # 批处理大小


@dataclass
class GPUConfig:
    """GPU配置"""
    enabled: bool = True                # 是否启用GPU
    device_ids: List[int] = field(default_factory=lambda: [0])  # GPU设备ID列表
    priority_order: List[int] = field(default_factory=lambda: [0])  # GPU优先级顺序
    memory_allocation: float = 0.8      # GPU显存分配比例
    enable_half_precision: bool = True  # 是否启用半精度计算


@dataclass
class AdaptiveSchedulerConfig:
    """自适应调度器配置"""
    # 通用配置
    enabled: bool = True                # 是否启用自适应调度
    backend: str = "auto"               # 初始后端选择: auto, gpu, cpu
    status_update_interval: int = 5     # 状态更新间隔(秒)
    
    # GPU阈值配置
    gpu_thresholds: GPUThresholdConfig = field(default_factory=GPUThresholdConfig)
    
    # CPU配置
    cpu: CPUConfig = field(default_factory=CPUConfig)
    
    # GPU配置
    gpu: GPUConfig = field(default_factory=GPUConfig)
    
    # 日志配置
    log_level: str = "INFO"             # 日志级别
    log_backend_switches: bool = True   # 是否记录后端切换日志
    log_performance_metrics: bool = True  # 是否记录性能指标
    
    # 测试配置
    enable_test_mode: bool = False      # 是否启用测试模式
    test_gpu_exception_probability: float = 0.0  # 测试模式下GPU异常概率

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'AdaptiveSchedulerConfig':
        """从字典创建配置"""
        config = cls()
        
        # 通用配置
        if 'enabled' in data:
            config.enabled = data['enabled']
        if 'backend' in data:
            config.backend = data['backend']
        if 'status_update_interval' in data:
            config.status_update_interval = data['status_update_interval']
        
        # GPU阈值配置
        if 'gpu_thresholds' in data:
            gpu_thresholds_data = data['gpu_thresholds']
            config.gpu_thresholds.utilization_threshold = gpu_thresholds_data.get('utilization_threshold', 85)
            config.gpu_thresholds.temperature_threshold = gpu_thresholds_data.get('temperature_threshold', 90)
            config.gpu_thresholds.memory_threshold = gpu_thresholds_data.get('memory_threshold', 90)
            config.gpu_thresholds.threshold_duration = gpu_thresholds_data.get('threshold_duration', 10)
            config.gpu_thresholds.retry_interval = gpu_thresholds_data.get('retry_interval', 60)
            config.gpu_thresholds.recovery_check_interval = gpu_thresholds_data.get('recovery_check_interval', 30)
        
        # CPU配置
        if 'cpu' in data:
            cpu_data = data['cpu']
            config.cpu.enable_multiprocessing = cpu_data.get('enable_multiprocessing', True)
            config.cpu.enable_multithreading = cpu_data.get('enable_multithreading', True)
            config.cpu.max_workers = cpu_data.get('max_workers')
            config.cpu.threads_per_worker = cpu_data.get('threads_per_worker', 4)
            config.cpu.queue_size = cpu_data.get('queue_size', 100)
            config.cpu.batch_size = cpu_data.get('batch_size', 8)
        
        # GPU配置
        if 'gpu' in data:
            gpu_data = data['gpu']
            config.gpu.enabled = gpu_data.get('enabled', True)
            config.gpu.device_ids = gpu_data.get('device_ids', [0])
            config.gpu.priority_order = gpu_data.get('priority_order', [0])
            config.gpu.memory_allocation = gpu_data.get('memory_allocation', 0.8)
            config.gpu.enable_half_precision = gpu_data.get('enable_half_precision', True)
        
        # 日志配置
        if 'log_level' in data:
            config.log_level = data['log_level']
        if 'log_backend_switches' in data:
            config.log_backend_switches = data['log_backend_switches']
        if 'log_performance_metrics' in data:
            config.log_performance_metrics = data['log_performance_metrics']
        
        # 测试配置
        if 'enable_test_mode' in data:
            config.enable_test_mode = data['enable_test_mode']
        if 'test_gpu_exception_probability' in data:
            config.test_gpu_exception_probability = data['test_gpu_exception_probability']
        
        return config


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AdaptiveSchedulerConfig] = None
    _config_file: str = "adaptive_scheduler_config.json"
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化"""
        if ConfigManager._instance is not None:
            raise RuntimeError("ConfigManager是单例类，请使用get_instance()获取实例")
        ConfigManager._instance = self
        self.load_config()
    
    def get_config(self) -> AdaptiveSchedulerConfig:
        """获取配置"""
        if self._config is None:
            self._config = AdaptiveSchedulerConfig()
        return self._config
    
    def set_config(self, config: AdaptiveSchedulerConfig):
        """设置配置"""
        self._config = config
    
    def load_config(self, config_file: Optional[str] = None):
        """从文件加载配置"""
        if config_file:
            self._config_file = config_file
        
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config = AdaptiveSchedulerConfig.from_dict(data)
                    logger.info(f"自适应调度器配置已从文件加载: {self._config_file}")
            except Exception as e:
                logger.error(f"加载自适应调度器配置失败: {e}")
                self._config = AdaptiveSchedulerConfig()
        else:
            self._config = AdaptiveSchedulerConfig()
            logger.info("未找到配置文件，使用默认配置")
    
    def save_config(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        if config_file:
            self._config_file = config_file
        
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"自适应调度器配置已保存到文件: {self._config_file}")
        except Exception as e:
            logger.error(f"保存自适应调度器配置失败: {e}")
    
    def update_config(self, updates: Dict):
        """更新配置"""
        if self._config is None:
            self._config = AdaptiveSchedulerConfig()
        
        # 递归更新配置
        def recursive_update(obj, updates_dict):
            for key, value in updates_dict.items():
                if hasattr(obj, key):
                    attr = getattr(obj, key)
                    if isinstance(attr, (AdaptiveSchedulerConfig, GPUThresholdConfig, CPUConfig, GPUConfig)):
                        recursive_update(attr, value)
                    else:
                        setattr(obj, key, value)
                else:
                    logger.warning(f"配置项不存在: {key}")
        
        recursive_update(self._config, updates)
        logger.info("自适应调度器配置已更新")
    
    def get_cpu_config(self) -> CPUConfig:
        """获取CPU配置"""
        return self.get_config().cpu
    
    def get_gpu_config(self) -> GPUConfig:
        """获取GPU配置"""
        return self.get_config().gpu
    
    def get_gpu_thresholds(self) -> GPUThresholdConfig:
        """获取GPU阈值配置"""
        return self.get_config().gpu_thresholds
    
    def is_enabled(self) -> bool:
        """检查是否启用自适应调度"""
        return self.get_config().enabled
    
    def get_initial_backend(self) -> str:
        """获取初始后端选择"""
        return self.get_config().backend


# 全局配置实例
config_manager = ConfigManager.get_instance()


# 配置常量
DEFAULT_CONFIG_FILE = "adaptive_scheduler_config.json"
CONFIG_DIR = "config"


# 辅助函数
def get_default_config() -> AdaptiveSchedulerConfig:
    """获取默认配置"""
    return AdaptiveSchedulerConfig()


def create_config_file(config_file: str = DEFAULT_CONFIG_FILE):
    """创建配置文件"""
    config = get_default_config()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"默认配置文件已创建: {config_file}")
    except Exception as e:
        logger.error(f"创建配置文件失败: {e}")


def validate_config(config: AdaptiveSchedulerConfig) -> List[str]:
    """验证配置有效性"""
    errors = []
    
    # 验证后端选择
    if config.backend not in ['auto', 'gpu', 'cpu']:
        errors.append(f"无效的后端选择: {config.backend}，必须是auto、gpu或cpu")
    
    # 验证GPU阈值
    if not (0 <= config.gpu_thresholds.utilization_threshold <= 100):
        errors.append(f"GPU占用率阈值必须在0-100之间: {config.gpu_thresholds.utilization_threshold}")
    if not (0 <= config.gpu_thresholds.temperature_threshold <= 150):
        errors.append(f"GPU温度阈值必须在0-150之间: {config.gpu_thresholds.temperature_threshold}")
    if not (0 <= config.gpu_thresholds.memory_threshold <= 100):
        errors.append(f"GPU显存阈值必须在0-100之间: {config.gpu_thresholds.memory_threshold}")
    if config.gpu_thresholds.threshold_duration <= 0:
        errors.append(f"阈值持续时间必须大于0: {config.gpu_thresholds.threshold_duration}")
    
    # 验证CPU配置
    if config.cpu.threads_per_worker <= 0:
        errors.append(f"每个工作进程的线程数必须大于0: {config.cpu.threads_per_worker}")
    if config.cpu.queue_size <= 0:
        errors.append(f"任务队列大小必须大于0: {config.cpu.queue_size}")
    if config.cpu.batch_size <= 0:
        errors.append(f"批处理大小必须大于0: {config.cpu.batch_size}")
    
    # 验证GPU配置
    if not config.gpu.device_ids:
        errors.append("GPU设备ID列表不能为空")
    if not config.gpu.priority_order:
        errors.append("GPU优先级顺序不能为空")
    if not (0 <= config.gpu.memory_allocation <= 1):
        errors.append(f"GPU显存分配比例必须在0-1之间: {config.gpu.memory_allocation}")
    
    # 验证日志级别
    if config.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        errors.append(f"无效的日志级别: {config.log_level}")
    
    return errors