# ===============================================
# =============== 硬件自适应调度器 ===============
# ===============================================

import time
import threading
import subprocess
import platform
from enum import Enum
from typing import List, Dict, Optional
from PySide2.QtCore import QObject, Signal, QTimer
from umi_log import logger
from .config import get_config


class BackendType(Enum):
    GPU = "gpu"
    CPU = "cpu"
    AUTO = "auto"


class GPUStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


class HardwareMonitor(QObject):
    """硬件状态监控器"""
    
    # 信号定义
    gpu_status_changed = Signal(str, str)  # (status, message)
    cpu_usage_updated = Signal(float)
    memory_usage_updated = Signal(float)
    
    def __init__(self):
        super().__init__()
        self._config = get_config()
        self._gpu_status = GPUStatus.UNAVAILABLE
        self._gpu_info = {}
        self._cpu_usage = 0.0
        self._memory_usage = 0.0
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._monitor_hardware)
        
    def start_monitoring(self, interval: int = 2000):
        """启动硬件监控"""
        self._monitor_timer.start(interval)
        
    def stop_monitoring(self):
        """停止硬件监控"""
        self._monitor_timer.stop()
        
    def get_gpu_status(self) -> GPUStatus:
        """获取GPU状态"""
        return self._gpu_status
        
    def get_gpu_info(self) -> Dict:
        """获取GPU信息"""
        return self._gpu_info
        
    def _monitor_hardware(self):
        """监控硬件状态"""
        # 监控GPU
        self._monitor_gpu()
        
        # 监控CPU和内存
        self._monitor_cpu_memory()
        
    def _monitor_gpu(self):
        """监控GPU状态"""
        try:
            if platform.system() == "Windows":
                self._monitor_gpu_windows()
            elif platform.system() == "Linux":
                self._monitor_gpu_linux()
            else:
                self._gpu_status = GPUStatus.UNAVAILABLE
                self._gpu_info = {}
        except Exception as e:
            logger.error(f"GPU监控失败: {e}")
            self._gpu_status = GPUStatus.ERROR
            self._gpu_info = {"error": str(e)}
            self.gpu_status_changed.emit(GPUStatus.ERROR.value, f"GPU监控失败: {e}")
            
    def _monitor_gpu_windows(self):
        """Windows系统GPU监控"""
        try:
            # 使用nvidia-smi获取GPU信息
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,memory.total,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                gpu_data = result.stdout.strip().split('\n')[0].split(', ')
                gpu_util = int(gpu_data[0])
                mem_util = int(gpu_data[1])
                temp = int(gpu_data[2])
                mem_total = int(gpu_data[3])
                mem_used = int(gpu_data[4])
                
                self._gpu_info = {
                    "utilization": gpu_util,
                    "memory_utilization": mem_util,
                    "temperature": temp,
                    "memory_total": mem_total,
                    "memory_used": mem_used,
                    "driver": "NVIDIA"
                }
                
                # 检查阈值
                config = self._config.get("hardware_scheduler", {})
                temp_threshold = config.get("gpu_temperature_threshold", 85)
                util_threshold = config.get("gpu_utilization_threshold", 95)
                mem_threshold = config.get("gpu_memory_threshold", 90)
                
                status = GPUStatus.HEALTHY
                message = "GPU状态正常"
                
                if temp > temp_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU温度过高: {temp}°C"
                elif gpu_util > util_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU利用率过高: {gpu_util}%"
                elif mem_util > mem_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU显存占用过高: {mem_util}%"
                
                if self._gpu_status != status:
                    self._gpu_status = status
                    self.gpu_status_changed.emit(status.value, message)
            else:
                self._gpu_status = GPUStatus.UNAVAILABLE
                self._gpu_info = {}
                self.gpu_status_changed.emit(GPUStatus.UNAVAILABLE.value, "未检测到NVIDIA GPU")
                
        except FileNotFoundError:
            self._gpu_status = GPUStatus.UNAVAILABLE
            self._gpu_info = {}
            self.gpu_status_changed.emit(GPUStatus.UNAVAILABLE.value, "未找到nvidia-smi工具")
        except Exception as e:
            logger.error(f"Windows GPU监控失败: {e}")
            self._gpu_status = GPUStatus.ERROR
            self._gpu_info = {"error": str(e)}
            self.gpu_status_changed.emit(GPUStatus.ERROR.value, f"GPU监控失败: {e}")
            
    def _monitor_gpu_linux(self):
        """Linux系统GPU监控"""
        try:
            # 使用nvidia-smi获取GPU信息
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,memory.total,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                gpu_data = result.stdout.strip().split('\n')[0].split(', ')
                gpu_util = int(gpu_data[0])
                mem_util = int(gpu_data[1])
                temp = int(gpu_data[2])
                mem_total = int(gpu_data[3])
                mem_used = int(gpu_data[4])
                
                self._gpu_info = {
                    "utilization": gpu_util,
                    "memory_utilization": mem_util,
                    "temperature": temp,
                    "memory_total": mem_total,
                    "memory_used": mem_used,
                    "driver": "NVIDIA"
                }
                
                # 检查阈值
                config = self._config.get("hardware_scheduler", {})
                temp_threshold = config.get("gpu_temperature_threshold", 85)
                util_threshold = config.get("gpu_utilization_threshold", 95)
                mem_threshold = config.get("gpu_memory_threshold", 90)
                
                status = GPUStatus.HEALTHY
                message = "GPU状态正常"
                
                if temp > temp_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU温度过高: {temp}°C"
                elif gpu_util > util_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU利用率过高: {gpu_util}%"
                elif mem_util > mem_threshold:
                    status = GPUStatus.WARNING
                    message = f"GPU显存占用过高: {mem_util}%"
                
                if self._gpu_status != status:
                    self._gpu_status = status
                    self.gpu_status_changed.emit(status.value, message)
            else:
                self._gpu_status = GPUStatus.UNAVAILABLE
                self._gpu_info = {}
                self.gpu_status_changed.emit(GPUStatus.UNAVAILABLE.value, "未检测到NVIDIA GPU")
                
        except FileNotFoundError:
            self._gpu_status = GPUStatus.UNAVAILABLE
            self._gpu_info = {}
            self.gpu_status_changed.emit(GPUStatus.UNAVAILABLE.value, "未找到nvidia-smi工具")
        except Exception as e:
            logger.error(f"Linux GPU监控失败: {e}")
            self._gpu_status = GPUStatus.ERROR
            self._gpu_info = {"error": str(e)}
            self.gpu_status_changed.emit(GPUStatus.ERROR.value, f"GPU监控失败: {e}")
            
    def _monitor_cpu_memory(self):
        """监控CPU和内存使用情况"""
        try:
            if platform.system() == "Windows":
                # Windows系统监控
                result = subprocess.run(
                    ["wmic", "cpu", "get", "loadpercentage"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    cpu_usage = int(result.stdout.strip().split('\n')[1])
                    self._cpu_usage = cpu_usage
                    self.cpu_usage_updated.emit(cpu_usage)
                    
                # 获取内存使用情况
                result = subprocess.run(
                    ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        total_mem, free_mem = map(int, lines[1].split())
                        used_mem = total_mem - free_mem
                        memory_usage = (used_mem / total_mem) * 100
                        self._memory_usage = memory_usage
                        self.memory_usage_updated.emit(memory_usage)
                        
            elif platform.system() == "Linux":
                # Linux系统监控
                with open("/proc/stat", "r") as f:
                    cpu_stats = f.readline().split()
                    total = sum(map(int, cpu_stats[1:8]))
                    idle = int(cpu_stats[4])
                    cpu_usage = 100 - (idle / total) * 100
                    self._cpu_usage = cpu_usage
                    self.cpu_usage_updated.emit(cpu_usage)
                    
                # 获取内存使用情况
                with open("/proc/meminfo", "r") as f:
                    lines = f.readlines()
                    mem_total = int(lines[0].split()[1])
                    mem_free = int(lines[1].split()[1])
                    mem_buffers = int(lines[2].split()[1])
                    mem_cached = int(lines[3].split()[1])
                    used_mem = mem_total - mem_free - mem_buffers - mem_cached
                    memory_usage = (used_mem / mem_total) * 100
                    self._memory_usage = memory_usage
                    self.memory_usage_updated.emit(memory_usage)
                    
        except Exception as e:
            logger.error(f"CPU/内存监控失败: {e}")


class HardwareScheduler(QObject):
    """硬件自适应调度器"""
    
    # 信号定义
    backend_changed = Signal(str, str, str)  # (new_backend, old_backend, reason)
    status_updated = Signal(dict)  # 状态更新
    
    def __init__(self):
        super().__init__()
        self._config = get_config()
        self._current_backend = BackendType.AUTO
        self._target_backend = BackendType.AUTO
        self._last_switch_time = 0
        self._warning_counter = 0
        self._recovery_timer = QTimer()
        
        # 初始化硬件监控器
        self._hardware_monitor = HardwareMonitor()
        self._hardware_monitor.gpu_status_changed.connect(self._on_gpu_status_changed)
        
        # 启动监控
        self._hardware_monitor.start_monitoring()
        
    def set_backend(self, backend: str):
        """设置后端类型"""
        try:
            self._target_backend = BackendType(backend.lower())
            if self._target_backend != BackendType.AUTO:
                self._switch_backend(self._target_backend, "手动切换后端")
        except ValueError:
            logger.error(f"无效的后端类型: {backend}")
            
    def get_current_backend(self) -> str:
        """获取当前后端类型"""
        return self._current_backend.value
        
    def get_hardware_info(self) -> Dict:
        """获取硬件信息"""
        return {
            "current_backend": self._current_backend.value,
            "target_backend": self._target_backend.value,
            "gpu_status": self._hardware_monitor.get_gpu_status().value,
            "gpu_info": self._hardware_monitor.get_gpu_info(),
            "last_switch_time": self._last_switch_time
        }
        
    def _on_gpu_status_changed(self, status: str, message: str):
        """GPU状态变化处理"""
        if self._target_backend != BackendType.AUTO:
            return  # 如果是手动模式，不自动切换
            
        gpu_status = GPUStatus(status)
        config = self._config.get("hardware_scheduler", {})
        
        if gpu_status == GPUStatus.ERROR or gpu_status == GPUStatus.UNAVAILABLE:
            # GPU不可用，切换到CPU
            self._switch_backend(BackendType.CPU, f"GPU {status}: {message}")
            self._warning_counter = 0
            
        elif gpu_status == GPUStatus.WARNING:
            # GPU警告，增加计数器
            self._warning_counter += 1
            warning_threshold = config.get("gpu_warning_threshold", 3)
            
            if self._warning_counter >= warning_threshold:
                # 连续警告达到阈值，切换到CPU
                self._switch_backend(BackendType.CPU, f"GPU连续警告 {self._warning_counter} 次: {message}")
                self._warning_counter = 0
                
                # 启动恢复计时器
                recovery_interval = config.get("gpu_recovery_check_interval", 30000)  # 30秒
                self._recovery_timer.timeout.connect(self._check_gpu_recovery)
                self._recovery_timer.start(recovery_interval)
                
        elif gpu_status == GPUStatus.HEALTHY:
            # GPU恢复正常
            self._warning_counter = 0
            
            if self._current_backend == BackendType.CPU and self._target_backend == BackendType.AUTO:
                # 如果当前是CPU模式且目标是自动模式，切换回GPU
                self._switch_backend(BackendType.GPU, "GPU状态恢复正常")
                self._recovery_timer.stop()
                
    def _check_gpu_recovery(self):
        """检查GPU是否恢复"""
        gpu_status = self._hardware_monitor.get_gpu_status()
        if gpu_status == GPUStatus.HEALTHY:
            self._switch_backend(BackendType.GPU, "GPU状态恢复正常")
            self._recovery_timer.stop()
            
    def _switch_backend(self, new_backend: BackendType, reason: str):
        """切换后端"""
        if self._current_backend == new_backend:
            return  # 后端未变化，不切换
            
        old_backend = self._current_backend
        self._current_backend = new_backend
        self._last_switch_time = time.time()
        
        logger.info(f"后端切换: {old_backend.value} -> {new_backend.value}, 原因: {reason}")
        
        # 发送后端变化信号
        self.backend_changed.emit(new_backend.value, old_backend.value, reason)
        
        # 更新状态
        self._update_status()
        
    def _update_status(self):
        """更新状态"""
        status = {
            "current_backend": self._current_backend.value,
            "target_backend": self._target_backend.value,
            "gpu_status": self._hardware_monitor.get_gpu_status().value,
            "gpu_info": self._hardware_monitor.get_gpu_info(),
            "last_switch_time": self._last_switch_time,
            "warning_counter": self._warning_counter
        }
        self.status_updated.emit(status)
        
    def get_optimized_params(self, base_params: Dict) -> Dict:
        """根据当前后端获取优化后的参数"""
        params = base_params.copy()
        config = self._config.get("hardware_scheduler", {})
        
        if self._current_backend == BackendType.CPU:
            # CPU模式优化参数
            cpu_threads = config.get("cpu_threads", -1)
            if cpu_threads > 0:
                params["cpu_threads"] = cpu_threads
            
            # 启用多进程/多线程混合策略
            params["use_multiprocessing"] = config.get("cpu_use_multiprocessing", True)
            params["process_count"] = config.get("cpu_process_count", 2)
            
        elif self._current_backend == BackendType.GPU:
            # GPU模式优化参数
            params["gpu_id"] = config.get("gpu_id", 0)
            params["gpu_memory_limit"] = config.get("gpu_memory_limit", 0)
            
        return params


# 全局硬件调度器实例
hardware_scheduler = HardwareScheduler()
