# ===============================================
# =============== 硬件调度器测试脚本 ===============
# ===============================================

import time
import sys
import os

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src'))

from optimization import get_hardware_scheduler, BackendType
from optimization.hardware_scheduler import GPUStatus
from umi_log import logger


class HardwareSchedulerTest:
    """硬件调度器测试类"""
    
    def __init__(self):
        self.scheduler = get_hardware_scheduler()
        self.test_results = []
        
        # 连接信号
        self.scheduler.backend_changed.connect(self._on_backend_changed)
        self.scheduler.status_updated.connect(self._on_status_updated)
        
    def _on_backend_changed(self, new_backend: str, old_backend: str, reason: str):
        """后端变化回调"""
        print(f"\n=== 后端切换事件 ===")
        print(f"从 {old_backend} 切换到 {new_backend}")
        print(f"原因: {reason}")
        self.test_results.append(f"后端切换: {old_backend} -> {new_backend} ({reason})")
        
    def _on_status_updated(self, status: dict):
        """状态更新回调"""
        print(f"\n=== 状态更新 ===")
        print(f"当前后端: {status['current_backend']}")
        print(f"目标后端: {status['target_backend']}")
        print(f"GPU状态: {status['gpu_status']}")
        
    def test_hardware_detection(self):
        """测试硬件检测功能"""
        print("\n=== 测试硬件检测 ===")
        
        hardware_info = self.scheduler.get_hardware_info()
        print(f"硬件信息: {hardware_info}")
        
        gpu_status = hardware_info['gpu_status']
        if gpu_status == GPUStatus.HEALTHY.value:
            print("✓ GPU检测成功，状态正常")
            gpu_info = hardware_info['gpu_info']
            print(f"  GPU利用率: {gpu_info.get('utilization', 'N/A')}%")
            print(f"  GPU温度: {gpu_info.get('temperature', 'N/A')}°C")
            print(f"  显存占用: {gpu_info.get('memory_utilization', 'N/A')}%")
            return True
        elif gpu_status == GPUStatus.WARNING.value:
            print("⚠ GPU检测成功，但状态警告")
            return True
        elif gpu_status == GPUStatus.UNAVAILABLE.value:
            print("⚠ GPU不可用，将使用CPU后端")
            return True
        else:
            print("✗ GPU检测失败")
            return False
            
    def test_backend_switching(self):
        """测试后端切换功能"""
        print("\n=== 测试后端切换 ===")
        
        # 测试手动切换到CPU
        print("1. 手动切换到CPU后端...")
        self.scheduler.set_backend(BackendType.CPU.value)
        time.sleep(1)
        
        current_backend = self.scheduler.get_current_backend()
        if current_backend == BackendType.CPU.value:
            print("✓ 成功切换到CPU后端")
        else:
            print(f"✗ 切换到CPU后端失败，当前后端: {current_backend}")
            return False
            
        # 测试手动切换到AUTO
        print("2. 手动切换到AUTO后端...")
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        
        current_backend = self.scheduler.get_current_backend()
        print(f"✓ 当前后端: {current_backend}")
        
        return True
        
    def test_optimized_params(self):
        """测试优化参数生成"""
        print("\n=== 测试优化参数生成 ===")
        
        base_params = {"param1": "value1", "param2": "value2"}
        
        # 测试CPU模式参数
        print("1. CPU模式优化参数...")
        self.scheduler.set_backend(BackendType.CPU.value)
        time.sleep(1)
        cpu_params = self.scheduler.get_optimized_params(base_params)
        print(f"   CPU参数: {cpu_params}")
        
        # 测试GPU模式参数
        print("2. GPU模式优化参数...")
        self.scheduler.set_backend(BackendType.GPU.value)
        time.sleep(1)
        gpu_params = self.scheduler.get_optimized_params(base_params)
        print(f"   GPU参数: {gpu_params}")
        
        # 测试AUTO模式参数
        print("3. AUTO模式优化参数...")
        self.scheduler.set_backend(BackendType.AUTO.value)
        time.sleep(1)
        auto_params = self.scheduler.get_optimized_params(base_params)
        print(f"   AUTO参数: {auto_params}")
        
        return True
        
    def test_gpu_monitoring(self):
        """测试GPU监控功能"""
        print("\n=== 测试GPU监控 ===")
        
        # 获取多次GPU状态
        print("监控GPU状态 5 秒...")
        for i in range(5):
            hardware_info = self.scheduler.get_hardware_info()
            gpu_status = hardware_info['gpu_status']
            gpu_info = hardware_info['gpu_info']
            
            print(f"[{i+1}] GPU状态: {gpu_status}")
            if gpu_info:
                print(f"   利用率: {gpu_info.get('utilization', 'N/A')}%, 温度: {gpu_info.get('temperature', 'N/A')}°C, 显存: {gpu_info.get('memory_utilization', 'N/A')}%")
            
            time.sleep(1)
            
        return True
        
    def run_all_tests(self):
        """运行所有测试"""
        print("="*50)
        print("硬件自适应调度器测试")
        print("="*50)
        
        tests = [
            ("硬件检测", self.test_hardware_detection),
            ("后端切换", self.test_backend_switching),
            ("优化参数生成", self.test_optimized_params),
            ("GPU监控", self.test_gpu_monitoring),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if test_func():
                    print(f"✓ {test_name} 测试通过")
                    passed += 1
                else:
                    print(f"✗ {test_name} 测试失败")
            except Exception as e:
                print(f"✗ {test_name} 测试异常: {e}")
                logger.error(f"测试异常: {e}", exc_info=True)
                
        print(f"\n{'='*50}")
        print(f"测试完成: {passed}/{total} 项通过")
        print(f"{'='*50}")
        
        if self.test_results:
            print("\n测试结果摘要:")
            for result in self.test_results:
                print(f"  - {result}")
                
        return passed == total


if __name__ == "__main__":
    print("启动硬件调度器测试...")
    
    # 配置日志
    logger.setLevel("INFO")
    
    test = HardwareSchedulerTest()
    
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
