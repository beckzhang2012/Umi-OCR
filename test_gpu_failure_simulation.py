# ===============================================
# =============== GPU异常模拟测试脚本 ===============
# ===============================================

import time
import sys
import os
import threading
from unittest.mock import patch, MagicMock

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src', 'imports'))

from optimization import get_hardware_scheduler, BackendType
from optimization.hardware_scheduler import HardwareMonitor, GPUStatus
from umi_log import logger


class GPUFailureSimulationTest:
    """GPU异常模拟测试类"""
    
    def __init__(self):
        self.scheduler = get_hardware_scheduler()
        self.monitor = self.scheduler._hardware_monitor
        self.test_results = []
        self.switch_events = []
        
        # 连接信号
        self.scheduler.backend_changed.connect(self._on_backend_changed)
        
    def _on_backend_changed(self, new_backend: str, old_backend: str, reason: str):
        """后端变化回调"""
        print(f"\n=== 后端切换事件 ===")
        print(f"从 {old_backend} 切换到 {new_backend}")
        print(f"原因: {reason}")
        self.switch_events.append((new_backend, old_backend, reason))
        self.test_results.append(f"后端切换: {old_backend} -> {new_backend} ({reason})")
        
    def _simulate_gpu_status(self, status: GPUStatus, gpu_info: dict = None):
        """模拟GPU状态"""
        self.monitor._gpu_status = status
        if gpu_info:
            self.monitor._gpu_info = gpu_info
        
        # 触发状态变化信号
        self.monitor.gpu_status_changed.emit(status.value, f"模拟{status.value}状态")
        
    def test_gpu_unavailable_switch(self):
        """测试GPU不可用时自动切换到CPU"""
        print("\n=== 测试GPU不可用时自动切换 ===")
        
        # 首先切换到AUTO模式
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        # 模拟GPU不可用
        print("1. 模拟GPU不可用...")
        self._simulate_gpu_status(GPUStatus.UNAVAILABLE, {})
        time.sleep(2)
        
        # 检查是否切换到CPU
        current_backend = self.scheduler.get_current_backend()
        if current_backend == BackendType.CPU.value:
            print("✓ 成功自动切换到CPU后端")
            return True
        else:
            print(f"✗ 切换到CPU后端失败，当前后端: {current_backend}")
            return False
            
    def test_gpu_error_switch(self):
        """测试GPU错误时自动切换到CPU"""
        print("\n=== 测试GPU错误时自动切换 ===")
        
        # 首先切换到AUTO模式
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        # 模拟GPU错误
        print("1. 模拟GPU错误...")
        self._simulate_gpu_status(GPUStatus.ERROR, {"error": "模拟GPU驱动错误"})
        time.sleep(2)
        
        # 检查是否切换到CPU
        current_backend = self.scheduler.get_current_backend()
        if current_backend == BackendType.CPU.value:
            print("✓ 成功自动切换到CPU后端")
            return True
        else:
            print(f"✗ 切换到CPU后端失败，当前后端: {current_backend}")
            return False
            
    def test_gpu_warning_switch(self):
        """测试GPU连续警告时自动切换到CPU"""
        print("\n=== 测试GPU连续警告时自动切换 ===")
        
        # 首先切换到AUTO模式
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        # 模拟GPU连续警告
        print("1. 模拟GPU连续警告...")
        warning_count = self.scheduler._config.get("hardware_scheduler", {}).get("gpu_warning_threshold", 3)
        
        for i in range(warning_count):
            print(f"   发送第 {i+1}/{warning_count} 次警告...")
            self._simulate_gpu_status(
                GPUStatus.WARNING,
                {"utilization": 96, "temperature": 86, "memory_utilization": 91}
            )
            time.sleep(1)
        
        time.sleep(2)
        
        # 检查是否切换到CPU
        current_backend = self.scheduler.get_current_backend()
        if current_backend == BackendType.CPU.value:
            print("✓ 成功自动切换到CPU后端")
            return True
        else:
            print(f"✗ 切换到CPU后端失败，当前后端: {current_backend}")
            return False
            
    def test_gpu_recovery_switch(self):
        """测试GPU恢复后自动切换回GPU"""
        print("\n=== 测试GPU恢复后自动切换 ===")
        
        # 首先切换到CPU模式（模拟之前GPU异常）
        self.scheduler.set_backend(BackendType.CPU.value)
        time.sleep(1)
        
        # 然后切换到AUTO模式
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        # 模拟GPU恢复正常
        print("1. 模拟GPU恢复正常...")
        self._simulate_gpu_status(
            GPUStatus.HEALTHY,
            {"utilization": 30, "temperature": 60, "memory_utilization": 40}
        )
        time.sleep(2)
        
        # 检查是否切换到GPU
        current_backend = self.scheduler.get_current_backend()
        if current_backend == BackendType.GPU.value:
            print("✓ 成功自动切换回GPU后端")
            return True
        else:
            print(f"✗ 切换回GPU后端失败，当前后端: {current_backend}")
            return False
            
    def test_task_continuity_during_switch(self):
        """测试切换期间任务连续性"""
        print("\n=== 测试切换期间任务连续性 ===")
        
        # 模拟一些任务正在执行
        print("1. 模拟任务执行中...")
        
        # 切换到AUTO模式
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        # 模拟GPU异常并切换
        print("2. 模拟GPU异常并切换...")
        self._simulate_gpu_status(GPUStatus.ERROR, {"error": "模拟GPU错误"})
        time.sleep(2)
        
        # 检查任务是否可以继续执行（通过检查调度器状态）
        hardware_info = self.scheduler.get_hardware_info()
        if hardware_info['current_backend'] in [BackendType.CPU.value, BackendType.GPU.value]:
            print("✓ 切换完成，系统处于可用状态")
            return True
        else:
            print(f"✗ 切换后系统状态异常: {hardware_info['current_backend']}")
            return False
            
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("GPU异常模拟测试")
        print("="*60)
        
        tests = [
            ("GPU不可用时自动切换", self.test_gpu_unavailable_switch),
            ("GPU错误时自动切换", self.test_gpu_error_switch),
            ("GPU连续警告时自动切换", self.test_gpu_warning_switch),
            ("GPU恢复后自动切换", self.test_gpu_recovery_switch),
            ("切换期间任务连续性", self.test_task_continuity_during_switch),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                # 重置切换事件
                self.switch_events.clear()
                
                if test_func():
                    print(f"✓ {test_name} 测试通过")
                    passed += 1
                else:
                    print(f"✗ {test_name} 测试失败")
            except Exception as e:
                print(f"✗ {test_name} 测试异常: {e}")
                logger.error(f"测试异常: {e}", exc_info=True)
                
        print(f"\n{'='*60}")
        print(f"测试完成: {passed}/{total} 项通过")
        print(f"{'='*60}")
        
        if self.test_results:
            print("\n测试结果摘要:")
            for result in self.test_results:
                print(f"  - {result}")
                
        if self.switch_events:
            print("\n切换事件统计:")
            for i, event in enumerate(self.switch_events):
                new_backend, old_backend, reason = event
                print(f"  {i+1}. {old_backend} -> {new_backend}: {reason}")
                
        return passed == total


if __name__ == "__main__":
    print("启动GPU异常模拟测试...")
    
    # 配置日志
    logger.setLevel("INFO")
    
    test = GPUFailureSimulationTest()
    
    try:
        success = test.run_all_tests()
        
        if success:
            print("\n所有测试通过！")
            sys.exit(0)
        else:
            print("\n部分测试失败！")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试发生严重错误: {e}")
        logger.error(f"测试严重错误: {e}", exc_info=True)
        sys.exit(1)
