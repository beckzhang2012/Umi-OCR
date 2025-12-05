#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= 硬件管理器与自适应调度 ===========
# ===============================================

import os
import time
import threading
import psutil
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from umi_log import logger


class BackendType(Enum):
    """后端类型枚举"""
    GPU = "GPU"
    CPU = "CPU"


class SwitchReason(Enum):
    """切换原因枚举"""
    NO_GPU_AVAILABLE = "没有可用的GPU"
    GPU_OCCUPANCY_HIGH = "GPU占用率过高"
    GPU_TEMPERATURE_HIGH = "GPU温度过高"
    GPU_MEMORY_FULL = "GPU显存不足"
    GPU_ERROR = "GPU驱动错误"
    MANUAL_SWITCH = "手动切换"
    GPU_RECOVERED = "GPU已恢复"


class HardwareManager:
    """硬件管理器与自适应调度器"""
    
    def __init__(self):
        self._current_backend: BackendType = BackendType.CPU
        self._switch_reason: Optional[SwitchReason] = None
        self._expected_recovery_time: Optional[float] = None
        
        self._gpu_devices: List[Dict[str, Any]] = []
        self._gpu_priority: List[int] = []  # GPU设备优先级列表
        
        # GPU监控阈值
        self._gpu_occupancy_threshold: float = 90.0  # GPU占用率阈值（%）
        self._gpu_temperature_threshold: float = 85.0  # GPU温度阈值（℃）
        self._gpu_memory_threshold: float = 90.0  # GPU显存阈值（%）
        self._gpu_monitor_interval: float = 2.0  # GPU监控间隔（秒）
        self._gpu_over_threshold_duration: int = 10  # 连续超阈值持续时间（秒）
        
        # CPU配置
        self._cpu_threads: int = psutil.cpu_count(logical=True)  # CPU线程数
        self._cpu_hybrid_mode: bool = True  # CPU混合多进程/多线程模式
        
        self._lock: threading.Lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running: bool = False
        
        self._backend_switch_callback: Optional[Callable[[BackendType, SwitchReason], None]] = None
        
        # 检测可用硬件
        self._detect_hardware()
    
    def _detect_hardware(self):
        """检测可用硬件"""
        logger.info("开始检测可用硬件...")
        
        # 检测GPU设备
        self._detect_gpu_devices()
        
        # 初始化默认后端
        if self._gpu_devices:
            self._current_backend = BackendType.GPU
            self._switch_reason = None
            logger.info(f"检测到 {len(self._gpu_devices)} 个GPU设备，默认使用GPU后端")
        else:
            self._current_backend = BackendType.CPU
            self._switch_reason = SwitchReason.NO_GPU_AVAILABLE
            logger.info("未检测到GPU设备，使用CPU后端")
        
        logger.info(f"当前后端: {self._current_backend.value}")
    
    def _detect_gpu_devices(self):
        """检测GPU设备"""
        self._gpu_devices = []
        
        # 尝试检测NVIDIA GPU
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle).decode()
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                gpu_device = {
                    "index": i,
                    "name": name,
                    "total_memory": memory_info.total,
                    "free_memory": memory_info.free,
                    "used_memory": memory_info.used,
                }
                
                self._gpu_devices.append(gpu_device)
                logger.info(f"检测到NVIDIA GPU: {name} (设备索引: {i})")
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            logger.info("未安装pynvml库，无法检测NVIDIA GPU")
        except Exception as e:
            logger.error(f"检测NVIDIA GPU时发生错误: {e}")
        
        # 尝试检测AMD GPU
        # TODO: 实现AMD GPU检测
        
        # 尝试检测Intel GPU
        # TODO: 实现Intel GPU检测
    
    def start_gpu_monitoring(self):
        """启动GPU监控"""
        if not self._gpu_devices:
            logger.info("没有GPU设备，无法启动GPU监控")
            return
        
        with self._lock:
            if self._monitor_running:
                logger.info("GPU监控已在运行")
                return
            
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._gpu_monitor_thread_func, daemon=True)
            self._monitor_thread.start()
            
            logger.info("GPU监控已启动")
    
    def stop_gpu_monitoring(self):
        """停止GPU监控"""
        with self._lock:
            if not self._monitor_running:
                logger.info("GPU监控未在运行")
                return
            
            self._monitor_running = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5.0)
                self._monitor_thread = None
            
            logger.info("GPU监控已停止")
    
    def _gpu_monitor_thread_func(self):
        """GPU监控线程函数"""
        over_threshold_start_time: Optional[float] = None
        
        while self._monitor_running:
            try:
                # 获取GPU状态
                gpu_status = self._get_gpu_status()
                
                if not gpu_status:
                    logger.warning("无法获取GPU状态")
                    time.sleep(self._gpu_monitor_interval)
                    continue
                
                # 检查GPU状态是否超过阈值
                over_threshold = False
                reason: Optional[SwitchReason] = None
                
                for status in gpu_status:
                    if status["occupancy"] > self._gpu_occupancy_threshold:
                        over_threshold = True
                        reason = SwitchReason.GPU_OCCUPANCY_HIGH
                        break
                    
                    if status["temperature"] > self._gpu_temperature_threshold:
                        over_threshold = True
                        reason = SwitchReason.GPU_TEMPERATURE_HIGH
                        break
                    
                    memory_usage_percent = (status["used_memory"] / status["total_memory"]) * 100
                    if memory_usage_percent > self._gpu_memory_threshold:
                        over_threshold = True
                        reason = SwitchReason.GPU_MEMORY_FULL
                        break
                
                # 处理超阈值情况
                if over_threshold:
                    if over_threshold_start_time is None:
                        over_threshold_start_time = time.time()
                    else:
                        duration = time.time() - over_threshold_start_time
                        if duration >= self._gpu_over_threshold_duration:
                            # 连续超阈值超过指定时间，切换到CPU后端
                            self.switch_to_backend(BackendType.CPU, reason)
                            over_threshold_start_time = None
                else:
                    over_threshold_start_time = None
                    
                    # 如果当前后端是CPU，尝试切换回GPU
                    if self._current_backend == BackendType.CPU:
                        self.switch_to_backend(BackendType.GPU, SwitchReason.GPU_RECOVERED)
            
            except Exception as e:
                logger.error(f"GPU监控线程发生错误: {e}")
                
                # GPU发生错误，切换到CPU后端
                self.switch_to_backend(BackendType.CPU, SwitchReason.GPU_ERROR)
            
            finally:
                time.sleep(self._gpu_monitor_interval)
    
    def _get_gpu_status(self) -> List[Dict[str, Any]]:
        """
        获取GPU状态
        
        Returns:
            GPU状态列表
        """
        gpu_status = []
        
        try:
            import pynvml
            
            pynvml.nvmlInit()
            
            for i in range(len(self._gpu_devices)):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # 获取GPU占用率
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                occupancy = utilization.gpu
                
                # 获取GPU温度
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # 获取GPU显存使用情况
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                status = {
                    "index": i,
                    "occupancy": occupancy,
                    "temperature": temperature,
                    "total_memory": memory_info.total,
                    "free_memory": memory_info.free,
                    "used_memory": memory_info.used,
                }
                
                gpu_status.append(status)
            
            pynvml.nvmlShutdown()
        
        except Exception as e:
            logger.error(f"获取GPU状态时发生错误: {e}")
        
        return gpu_status
    
    def switch_to_backend(self, backend: BackendType, reason: SwitchReason):
        """
        切换到指定后端
        
        Args:
            backend: 目标后端类型
            reason: 切换原因
        """
        with self._lock:
            if self._current_backend == backend:
                logger.info(f"当前已使用 {backend.value} 后端，无需切换")
                return
            
            # 更新当前后端和切换原因
            self._current_backend = backend
            self._switch_reason = reason
            
            # 设置预计恢复时间（仅当切换到CPU时）
            if backend == BackendType.CPU:
                self._expected_recovery_time = time.time() + 60.0  # 预计60秒后恢复
            else:
                self._expected_recovery_time = None
            
            logger.info(f"后端已切换到 {backend.value}，原因：{reason.value}")
            
            # 调用后端切换回调函数
            if self._backend_switch_callback:
                try:
                    self._backend_switch_callback(backend, reason)
                except Exception as e:
                    logger.error(f"调用后端切换回调函数时发生错误: {e}")
    
    def set_backend_switch_callback(self, callback: Callable[[BackendType, SwitchReason], None]):
        """
        设置后端切换回调函数
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            self._backend_switch_callback = callback
    
    def get_current_backend(self) -> BackendType:
        """
        获取当前后端类型
        
        Returns:
            当前后端类型
        """
        with self._lock:
            return self._current_backend
    
    def get_switch_reason(self) -> Optional[SwitchReason]:
        """
        获取最后一次切换原因
        
        Returns:
            最后一次切换原因
        """
        with self._lock:
            return self._switch_reason
    
    def get_expected_recovery_time(self) -> Optional[float]:
        """
        获取预计恢复时间
        
        Returns:
            预计恢复时间（Unix时间戳）
        """
        with self._lock:
            return self._expected_recovery_time
    
    def get_gpu_devices(self) -> List[Dict[str, Any]]:
        """
        获取GPU设备列表
        
        Returns:
            GPU设备列表
        """
        with self._lock:
            return self._gpu_devices.copy()
    
    def set_gpu_priority(self, priority: List[int]):
        """
        设置GPU设备优先级
        
        Args:
            priority: GPU设备索引列表，顺序表示优先级从高到低
        """
        with self._lock:
            # 验证优先级列表中的GPU索引是否有效
            valid_indices = [i for i in range(len(self._gpu_devices))]
            invalid_indices = [i for i in priority if i not in valid_indices]
            
            if invalid_indices:
                logger.warning(f"优先级列表中包含无效的GPU索引: {invalid_indices}")
                
                # 过滤无效索引
                priority = [i for i in priority if i in valid_indices]
                
                # 补充缺失的有效索引
                for i in valid_indices:
                    if i not in priority:
                        priority.append(i)
            
            self._gpu_priority = priority
            logger.info(f"GPU设备优先级已设置: {priority}")
    
    def get_gpu_priority(self) -> List[int]:
        """
        获取GPU设备优先级
        
        Returns:
            GPU设备优先级列表
        """
        with self._lock:
            return self._gpu_priority.copy()
    
    def set_cpu_threads(self, threads: int):
        """
        设置CPU线程数
        
        Args:
            threads: CPU线程数
        """
        with self._lock:
            max_threads = psutil.cpu_count(logical=True)
            if threads < 1 or threads > max_threads:
                logger.warning(f"CPU线程数必须在1到{max_threads}之间，当前值: {threads}")
                return
            
            self._cpu_threads = threads
            logger.info(f"CPU线程数已设置: {threads}")
    
    def get_cpu_threads(self) -> int:
        """
        获取CPU线程数
        
        Returns:
            CPU线程数
        """
        with self._lock:
            return self._cpu_threads
    
    def set_cpu_hybrid_mode(self, enabled: bool):
        """
        设置CPU混合模式
        
        Args:
            enabled: 是否启用CPU混合多进程/多线程模式
        """
        with self._lock:
            self._cpu_hybrid_mode = enabled
            logger.info(f"CPU混合模式已{'启用' if enabled else '禁用'}")
    
    def get_cpu_hybrid_mode(self) -> bool:
        """
        获取CPU混合模式状态
        
        Returns:
            CPU混合模式是否启用
        """
        with self._lock:
            return self._cpu_hybrid_mode
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        获取硬件信息
        
        Returns:
            硬件信息字典
        """
        with self._lock:
            # 获取CPU信息
            cpu_info = {
                "count": psutil.cpu_count(logical=True),
                "physical_count": psutil.cpu_count(logical=False),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            }
            
            # 获取内存信息
            memory_info = psutil.virtual_memory()
            memory_info_dict = {
                "total": memory_info.total,
                "available": memory_info.available,
                "used": memory_info.used,
                "percent": memory_info.percent,
            }
            
            return {
                "cpu": cpu_info,
                "memory": memory_info_dict,
                "gpu": self._gpu_devices.copy(),
                "current_backend": self._current_backend.value,
                "switch_reason": self._switch_reason.value if self._switch_reason else None,
                "expected_recovery_time": self._expected_recovery_time,
            }


# 创建全局硬件管理器实例
HardwareManagerGlobal = HardwareManager()
