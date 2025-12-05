# ===============================================
# =============== OCR优化模块入口 ===============
# ===============================================

"""
OCR推理流水线优化模块
提供内存池、纹理缓存、输入切片、任务调度、吞吐监测和硬件自适应调度等功能
"""

# 版本信息
__version__ = "1.0.0"

# 从config模块导入配置类和函数
from .config import (
    OptimizationConfig,
    get_config,
    update_config,
    get_section_config
)

# 从hardware_scheduler模块导入硬件调度组件
from .hardware_scheduler import (
    HardwareScheduler,
    HardwareMonitor,
    BackendType,
    GPUStatus,
    hardware_scheduler
)


# 全局实例获取函数
def get_hardware_scheduler() -> HardwareScheduler:
    """获取全局硬件调度器实例"""
    return hardware_scheduler


# 优化模块初始化函数
def optimize_ocr_pipeline(config_updates: dict = None):
    """
    初始化OCR优化流水线
    
    Args:
        config_updates: 配置更新字典
    """
    if config_updates:
        update_config(config_updates)
    
    # 启动硬件监控
    get_hardware_scheduler()
    
    print(f"OCR优化流水线已初始化，版本: {__version__}")


# 导出符号列表
__all__ = [
    # 配置相关
    'OptimizationConfig',
    'get_config',
    'update_config',
    'get_section_config',
    
    # 硬件调度组件类
    'HardwareScheduler',
    'HardwareMonitor',
    'BackendType',
    'GPUStatus',
    
    # 全局实例获取函数
    'get_hardware_scheduler',
    
    # 优化初始化函数
    'optimize_ocr_pipeline',
    
    # 模块信息
    '__version__'
]


# 默认初始化优化模块
optimize_ocr_pipeline()
