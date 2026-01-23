# ========================================  
# =============== 内存监控模块 ===============  
# ========================================

import psutil
import threading
import time
from umi_log import logger


class MemoryMonitor:
    def __init__(self):
        self._threshold = 1.5 * 1024 * 1024 * 1024  # 1.5GB内存阈值
        self._is_monitoring = False
        self._monitor_thread = None
        self._warning_callback = None
        self._last_warning_time = 0
        self._warning_interval = 60  # 警告间隔时间（秒）
    
    def set_threshold(self, threshold_gb):
        """设置内存警告阈值（GB）"""
        self._threshold = threshold_gb * 1024 * 1024 * 1024
    
    def set_warning_callback(self, callback):
        """设置警告回调函数"""
        self._warning_callback = callback
    
    def start_monitoring(self):
        """开始内存监控"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self._is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.debug("内存监控已停止")
    
    def get_current_memory(self):
        """获取当前内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss,  # 常驻内存
            "vms": memory_info.vms,  # 虚拟内存
            "rss_gb": memory_info.rss / (1024 * 1024 * 1024),
            "vms_gb": memory_info.vms / (1024 * 1024 * 1024)
        }
    
    def _monitor_loop(self):
        """监控循环"""
        while self._is_monitoring:
            try:
                mem_info = self.get_current_memory()
                current_memory = mem_info["rss"]
                
                # 检查是否超过阈值
                if current_memory > self._threshold:
                    current_time = time.time()
                    # 避免频繁警告
                    if current_time - self._last_warning_time > self._warning_interval:
                        self._last_warning_time = current_time
                        warning_msg = f"内存使用警告：当前使用 {mem_info['rss_gb']:.2f}GB，超过阈值 1.5GB"
                        logger.warning(warning_msg)
                        
                        # 调用回调函数
                        if self._warning_callback:
                            try:
                                self._warning_callback(warning_msg, mem_info)
                            except Exception as e:
                                logger.error(f"内存警告回调执行失败：{e}")
                
                time.sleep(5)  # 每5秒检查一次
            except Exception as e:
                logger.error(f"内存监控异常：{e}")
                time.sleep(10)


# 全局内存监控实例
memory_monitor = MemoryMonitor()