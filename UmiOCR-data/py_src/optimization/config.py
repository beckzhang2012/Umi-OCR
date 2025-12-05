# ===============================================
# =============== 优化模块配置 ===============
# ===============================================

from typing import Dict, Any


class OptimizationConfig:
    """优化模块配置管理"""
    
    def __init__(self):
        # 初始化默认配置
        self.config = {
            # 内存池配置
            "memory_pool": {
                "max_memory_mb": 512,
                "block_size_mb": 16,
                "preallocate_blocks": 4
            },
            
            # 纹理缓存配置
            "texture_cache": {
                "max_cache_size": 100,
                "expiration_time": 300,
                "cleanup_interval": 60
            },
            
            # 输入切片配置
            "input_slicer": {
                "max_slice_size": 1024,
                "overlap_size": 32,
                "min_slice_size": 256,
                "enable_slicing": True,
                "max_pixels": 1000000  # 100万像素
            },
            
            # 任务调度配置
            "task_scheduler": {
                "max_batch_size": 8,
                "batch_timeout": 0.1,
                "max_queue_size": 100,
                "keep_batch_data_count": 5
            },
            
            # 吞吐监测配置
            "throughput_monitor": {
                "window_size": 10,
                "monitor_interval": 1.0,
                "min_samples": 5
            },
            
            # 硬件调度器配置
            "hardware_scheduler": {
                # GPU配置
                "gpu_id": 0,
                "gpu_memory_limit": 0,  # 0表示不限制
                "gpu_temperature_threshold": 85,  # 摄氏度
                "gpu_utilization_threshold": 95,  # 百分比
                "gpu_memory_threshold": 90,  # 百分比
                "gpu_warning_threshold": 3,  # 连续警告次数阈值
                "gpu_recovery_check_interval": 30000,  # 恢复检查间隔（毫秒）
                
                # CPU配置
                "cpu_threads": -1,  # -1表示自动检测
                "cpu_use_multiprocessing": True,
                "cpu_process_count": 2,
                "cpu_min_throughput_ratio": 0.85,  # 相对于GPU的最小吞吐率
                
                # 自动切换配置
                "auto_switch_enabled": True,
                "switch_cooldown_time": 60,  # 切换冷却时间（秒）
                "min_task_count_for_switch": 5  # 切换前的最小任务数
            }
        }
        
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self._deep_update(self.config, new_config)
        
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config.copy()
        
    def get_section_config(self, section: str) -> Dict[str, Any]:
        """获取指定部分的配置"""
        return self.config.get(section, {})
        
    def _deep_update(self, original: Dict[str, Any], update: Dict[str, Any]):
        """深度更新字典"""
        for key, value in update.items():
            if isinstance(value, dict) and key in original and isinstance(original[key], dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value


# 全局配置实例
_config_instance = OptimizationConfig()


def get_config() -> Dict[str, Any]:
    """获取全局配置"""
    return _config_instance.get_config()


def update_config(new_config: Dict[str, Any]):
    """更新全局配置"""
    _config_instance.update_config(new_config)


def get_section_config(section: str) -> Dict[str, Any]:
    """获取指定部分的配置"""
    return _config_instance.get_section_config(section)
