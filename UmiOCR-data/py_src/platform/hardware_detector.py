# ===============================================
# =============== 硬件检测模块 ===================
# ===============================================

import subprocess
import re
import platform
from umi_log import logger


class HardwareDetector:
    """硬件检测类，用于检测系统中的GPU和CPU信息"""

    @staticmethod
    def get_gpu_info():
        """获取系统中的GPU信息"""
        gpu_info = []
        system = platform.system()

        try:
            if system == "Windows":
                # 使用nvidia-smi检测NVIDIA GPU
                try:
                    result = subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=name,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    lines = result.strip().split('\n')
                    for i, line in enumerate(lines):
                        if line.strip():
                            parts = line.split(',')
                            if len(parts) >= 4:
                                gpu_info.append({
                                    "id": i,
                                    "name": parts[0].strip(),
                                    "memory_total": int(parts[1].strip()),
                                    "utilization": int(parts[2].strip()),
                                    "temperature": int(parts[3].strip()),
                                    "type": "NVIDIA",
                                    "available": True
                                })
                except subprocess.CalledProcessError as e:
                    logger.warning(f"NVIDIA GPU检测失败: {e.output}")
                except FileNotFoundError:
                    logger.warning("nvidia-smi未找到，可能没有NVIDIA GPU或驱动未安装")

                # 使用dxdiag检测其他GPU
                try:
                    result = subprocess.check_output(
                        ["dxdiag", "/t", "dxdiag_output.txt"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    # 读取dxdiag输出文件
                    with open("dxdiag_output.txt", "r", encoding="utf-8") as f:
                        content = f.read()
                    # 解析GPU信息
                    gpu_sections = re.findall(r'Card Name:\s*(.*?)\n.*?Dedicated Memory:\s*(.*?)\n', content, re.DOTALL)
                    for i, (name, memory) in enumerate(gpu_sections):
                        # 跳过已检测的NVIDIA GPU
                        if "NVIDIA" not in name:
                            gpu_info.append({
                                "id": i + len(gpu_info),
                                "name": name.strip(),
                                "memory_total": int(re.search(r'(\d+)', memory).group(1)) if re.search(r'(\d+)', memory) else 0,
                                "utilization": 0,
                                "temperature": 0,
                                "type": "Other",
                                "available": True
                            })
                except Exception as e:
                    logger.warning(f"DXDIAG检测失败: {e}")

            elif system == "Linux":
                # 使用lspci检测GPU
                try:
                    result = subprocess.check_output(
                        ["lspci", "|", "grep", "VGA"],
                        shell=True,
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    lines = result.strip().split('\n')
                    for i, line in enumerate(lines):
                        if line.strip():
                            gpu_info.append({
                                "id": i,
                                "name": line.split(':')[-1].strip(),
                                "memory_total": 0,
                                "utilization": 0,
                                "temperature": 0,
                                "type": "Linux GPU",
                                "available": True
                            })
                except Exception as e:
                    logger.warning(f"Linux GPU检测失败: {e}")

            elif system == "Darwin":
                # 使用system_profiler检测Mac GPU
                try:
                    result = subprocess.check_output(
                        ["system_profiler", "SPDisplaysDataType"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    # 解析GPU信息
                    gpu_sections = re.findall(r'Chipset Model:\s*(.*?)\n.*?VRAM (Total):\s*(.*?)\n', result, re.DOTALL)
                    for i, (name, memory) in enumerate(gpu_sections):
                        gpu_info.append({
                            "id": i,
                            "name": name.strip(),
                            "memory_total": int(re.search(r'(\d+)', memory).group(1)) if re.search(r'(\d+)', memory) else 0,
                            "utilization": 0,
                            "temperature": 0,
                            "type": "Mac GPU",
                            "available": True
                        })
                except Exception as e:
                    logger.warning(f"Mac GPU检测失败: {e}")

        except Exception as e:
            logger.error(f"GPU检测发生未知错误: {e}")

        return gpu_info

    @staticmethod
    def get_cpu_info():
        """获取系统中的CPU信息"""
        cpu_info = {}
        system = platform.system()

        try:
            if system == "Windows":
                # 使用wmic检测CPU信息
                try:
                    # 获取CPU名称
                    result = subprocess.check_output(
                        ["wmic", "cpu", "get", "Name"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    lines = result.strip().split('\n')
                    if len(lines) >= 2:
                        cpu_info["name"] = lines[1].strip()

                    # 获取CPU核心数
                    result = subprocess.check_output(
                        ["wmic", "cpu", "get", "NumberOfCores,NumberOfLogicalProcessors"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    lines = result.strip().split('\n')
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 2:
                            cpu_info["physical_cores"] = int(parts[0])
                            cpu_info["logical_cores"] = int(parts[1])

                except Exception as e:
                    logger.warning(f"Windows CPU检测失败: {e}")

            elif system == "Linux":
                # 使用/proc/cpuinfo检测CPU信息
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        content = f.read()

                    # 获取CPU名称
                    match = re.search(r'model name\s*:\s*(.*)', content)
                    if match:
                        cpu_info["name"] = match.group(1).strip()

                    # 获取CPU核心数
                    physical_cores = len(re.findall(r'physical id\s*:\s*(\d+)', content))
                    logical_cores = len(re.findall(r'processor\s*:\s*(\d+)', content))
                    cpu_info["physical_cores"] = physical_cores
                    cpu_info["logical_cores"] = logical_cores

                except Exception as e:
                    logger.warning(f"Linux CPU检测失败: {e}")

            elif system == "Darwin":
                # 使用sysctl检测CPU信息
                try:
                    # 获取CPU名称
                    result = subprocess.check_output(
                        ["sysctl", "-n", "machdep.cpu.brand_string"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    cpu_info["name"] = result.strip()

                    # 获取CPU核心数
                    result = subprocess.check_output(
                        ["sysctl", "-n", "hw.physicalcpu", "hw.logicalcpu"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    parts = result.strip().split()
                    if len(parts) >= 2:
                        cpu_info["physical_cores"] = int(parts[0])
                        cpu_info["logical_cores"] = int(parts[1])

                except Exception as e:
                    logger.warning(f"Mac CPU检测失败: {e}")

            # 获取CPU使用率（跨平台方法）
            try:
                if system == "Windows":
                    result = subprocess.check_output(
                        ["wmic", "cpu", "get", "LoadPercentage"],
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    lines = result.strip().split('\n')
                    if len(lines) >= 2:
                        cpu_info["utilization"] = int(lines[1].strip())
                else:
                    # Linux和Mac使用top命令
                    result = subprocess.check_output(
                        ["top", "-bn1"],
                        shell=True,
                        encoding="utf-8",
                        stderr=subprocess.STDOUT
                    )
                    match = re.search(r'Cpu\(s\):\s*(\d+\.\d+)%', result)
                    if match:
                        cpu_info["utilization"] = float(match.group(1))

            except Exception as e:
                logger.warning(f"CPU使用率检测失败: {e}")
                cpu_info["utilization"] = 0

        except Exception as e:
            logger.error(f"CPU检测发生未知错误: {e}")

        return cpu_info

    @staticmethod
    def get_system_info():
        """获取系统信息"""
        system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
        return system_info

    @staticmethod
    def detect_hardware():
        """检测所有硬件信息"""
        hardware_info = {
            "gpu": HardwareDetector.get_gpu_info(),
            "cpu": HardwareDetector.get_cpu_info(),
            "system": HardwareDetector.get_system_info()
        }
        return hardware_info


# 全局硬件检测器实例
HardwareDetectorInstance = HardwareDetector()