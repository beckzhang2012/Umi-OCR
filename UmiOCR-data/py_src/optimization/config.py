# ===============================================
# =============== 优化模块配置文件 ===============
# ===============================================

"""OCR推理流水线优化模块的配置参数"""


class OptimizationConfig:
    """优化模块配置类"""
    
    # ========================= 内存池配置 =========================
    
    # 内存池最大buffer数量
    MEMORY_POOL_MAX_BUFFERS = 15
    
    # 每个buffer的大小（字节）
    MEMORY_POOL_BUFFER_SIZE = 1024 * 1024 * 200  # 200MB
    
    # ========================= 纹理缓存配置 =========================
    
    # 纹理缓存最大数量
    TEXTURE_CACHE_MAX_SIZE = 100
    
    # ========================= 输入切片配置 =========================
    
    # 最大同时处理的段数
    INPUT_SLICER_MAX_SEGMENTS = 6
    
    # 需要切片的图片最小像素数（小于此值的图片不切片）
    INPUT_SLICER_MIN_AREA = 1024 * 1024  # 100万像素
    
    # ========================= 任务调度配置 =========================
    
    # 小图片的像素阈值（小于此值的图片视为小图片）
    TASK_SCHEDULER_SMALL_IMAGE_THRESHOLD = 1024 * 1024  # 100万像素
    
    # 最大并发任务数
    TASK_SCHEDULER_MAX_CONCURRENT_TASKS = 6
    
    # 默认调度模式: "1111" (轮询), "1234" (顺序), "optimized" (优化)
    TASK_SCHEDULER_DEFAULT_MODE = "optimized"
    
    # ========================= 吞吐监测配置 =========================
    
    # 保留的最大批次记录数
    THROUGHPUT_MONITOR_MAX_BATCHES = 1000
    
    # 是否启用详细日志
    THROUGHPUT_MONITOR_DETAILED_LOGGING = False
    
    # ========================= 动态调参配置 =========================
    
    # 是否启用动态调参
    DYNAMIC_TUNING_ENABLED = True
    
    # 性能监测间隔（秒）
    DYNAMIC_TUNING_INTERVAL = 5
    
    # 目标CPU利用率（百分比）
    DYNAMIC_TUNING_TARGET_CPU_USAGE = 70
    
    # 目标内存利用率（百分比）
    DYNAMIC_TUNING_TARGET_MEMORY_USAGE = 60
    
    # ========================= 调试配置 =========================
    
    # 是否启用调试模式
    DEBUG_MODE = False
    
    # 调试日志级别: "DEBUG", "INFO", "WARNING", "ERROR"
    DEBUG_LOG_LEVEL = "INFO"
    
    @classmethod
    def update_config(cls, config_dict: dict) -> None:
        """更新配置参数
        
        Args:
            config_dict: 配置字典
        """
        for key, value in config_dict.items():
            if hasattr(cls, key):
                current_value = getattr(cls, key)
                
                # 检查类型是否匹配
                if isinstance(current_value, (int, float, bool, str)):
                    if isinstance(value, type(current_value)):
                        setattr(cls, key, value)
                elif isinstance(current_value, list) and isinstance(value, list):
                    setattr(cls, key, value)
                elif isinstance(current_value, dict) and isinstance(value, dict):
                    setattr(cls, key, value)
    
    @classmethod
    def get_config(cls) -> dict:
        """获取当前配置
        
        Returns:
            配置字典
        """
        config = {}
        for key in dir(cls):
            if not key.startswith('_') and key.isupper():
                config[key] = getattr(cls, key)
        return config
    
    @classmethod
    def validate_config(cls) -> dict:
        """验证配置参数
        
        Returns:
            验证结果字典，包含错误信息
        """
        errors = []
        
        # 验证内存池配置
        if cls.MEMORY_POOL_MAX_BUFFERS < 1:
            errors.append("MEMORY_POOL_MAX_BUFFERS 必须大于0")
        if cls.MEMORY_POOL_BUFFER_SIZE < 1024 * 1024:  # 最小1MB
            errors.append("MEMORY_POOL_BUFFER_SIZE 必须大于等于1MB")
        
        # 验证纹理缓存配置
        if cls.TEXTURE_CACHE_MAX_SIZE < 0:
            errors.append("TEXTURE_CACHE_MAX_SIZE 不能为负数")
        
        # 验证输入切片配置
        if cls.INPUT_SLICER_MAX_SEGMENTS < 1:
            errors.append("INPUT_SLICER_MAX_SEGMENTS 必须大于0")
        if cls.INPUT_SLICER_MIN_AREA < 1024 * 1024:  # 最小100万像素
            errors.append("INPUT_SLICER_MIN_AREA 必须大于等于100万像素")
        
        # 验证任务调度配置
        if cls.TASK_SCHEDULER_SMALL_IMAGE_THRESHOLD < 1:
            errors.append("TASK_SCHEDULER_SMALL_IMAGE_THRESHOLD 必须大于0")
        if not (1 <= cls.TASK_SCHEDULER_MAX_CONCURRENT_TASKS <= 16):
            errors.append("TASK_SCHEDULER_MAX_CONCURRENT_TASKS 必须在1-16之间")
        if cls.TASK_SCHEDULER_DEFAULT_MODE not in ["1111", "1234", "optimized"]:
            errors.append("TASK_SCHEDULER_DEFAULT_MODE 必须是 '1111', '1234' 或 'optimized'")
        
        # 验证吞吐监测配置
        if cls.THROUGHPUT_MONITOR_MAX_BATCHES < 1:
            errors.append("THROUGHPUT_MONITOR_MAX_BATCHES 必须大于0")
        
        # 验证动态调参配置
        if not (1 <= cls.DYNAMIC_TUNING_INTERVAL <= 60):
            errors.append("DYNAMIC_TUNING_INTERVAL 必须在1-60秒之间")
        if not (0 <= cls.DYNAMIC_TUNING_TARGET_CPU_USAGE <= 100):
            errors.append("DYNAMIC_TUNING_TARGET_CPU_USAGE 必须在0-100之间")
        if not (0 <= cls.DYNAMIC_TUNING_TARGET_MEMORY_USAGE <= 100):
            errors.append("DYNAMIC_TUNING_TARGET_MEMORY_USAGE 必须在0-100之间")
        
        # 验证调试配置
        if cls.DEBUG_LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append("DEBUG_LOG_LEVEL 必须是 'DEBUG', 'INFO', 'WARNING' 或 'ERROR'")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


# 全局配置实例
global_config = OptimizationConfig()


def get_config() -> OptimizationConfig:
    """获取全局配置实例"""
    return global_config

def update_config(config_dict: dict) -> None:
    """更新全局配置"""
global_config.update_config(config_dict)

def validate_config() -> dict:
    """验证全局配置"""
    return global_config.validate_config()

def get_config_dict() -> dict:
    """获取配置字典"""
    return global_config.get_config()
