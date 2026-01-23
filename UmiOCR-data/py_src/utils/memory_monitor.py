# ===============================================
# =============== 内存监控模块 =================
# ===============================================

import os
import sys
import time
from umi_log import logger

# 尝试导入psutil库
psutil_available = False
try:
    import psutil
    psutil_available = True
except ImportError:
    logger.warning("psutil库未安装，内存监控功能将受限")

# 内存警告阈值（1.5GB）
MEMORY_WARNING_THRESHOLD = 1.5 * 1024 * 1024 * 1024  # 1.5GB

class MemoryMonitor:
    """内存监控类"""
    
    def __init__(self):
        self._last_warning_time = 0
        self._warning_interval = 10  # 警告间隔，避免频繁警告
    
    def get_memory_usage(self):
        """
        获取当前进程的内存使用情况
        返回：内存使用量（字节），如果无法获取则返回None
        """
        if not psutil_available:
            return None
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss  # 物理内存使用量
        except Exception as e:
            logger.error(f"获取内存使用情况失败：{e}")
            return None
    
    def check_memory_usage(self):
        """
        检查内存使用情况，如果超过阈值则触发警告
        返回：(内存使用量, 是否超过阈值)
        """
        memory_usage = self.get_memory_usage()
        if memory_usage is None:
            return None, False
        
        over_threshold = memory_usage > MEMORY_WARNING_THRESHOLD
        
        # 如果超过阈值且距离上次警告超过间隔时间，则触发警告
        current_time = time.time()
        if over_threshold and (current_time - self._last_warning_time) > self._warning_interval:
            self._last_warning_time = current_time
            self._trigger_warning(memory_usage)
        
        return memory_usage, over_threshold
    
    def _trigger_warning(self, memory_usage):
        """
        触发内存警告
        """
        memory_gb = memory_usage / (1024 * 1024 * 1024)
        warning_msg = f"[Warning] 内存使用过高：{memory_gb:.2f}GB，超过1.5GB阈值"
        logger.warning(warning_msg)
        
        # 可以在这里添加其他警告方式，比如发送信号给主线程等
    
    def format_memory(self, memory_bytes):
        """
        格式化内存大小为人类可读的格式
        """
        if memory_bytes is None:
            return "未知"
        
        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        memory = memory_bytes
        
        while memory >= 1024 and unit_index < len(units) - 1:
            memory /= 1024
            unit_index += 1
        
        return f"{memory:.2f} {units[unit_index]}"

# 全局内存监控实例
memory_monitor = MemoryMonitor()
