#!/usr/bin/env python3
"""
性能监控界面测试脚本

测试PerformanceMonitor页面控制器和performance_collector的功能
"""

import sys
import time
import threading
import random
from datetime import datetime

# 添加py_src到Python路径
sys.path.insert(0, 'd:\\beck\\work\\test\\buzzer\\C\\Umi-OCR\\UmiOCR-data\\py_src')

from tag_pages.PerformanceMonitor import PerformanceMonitor
from monitoring.performance_collector import PerformanceCollector
from event_bus.pubsub_service import PubSubService

def test_performance_collector():
    """测试性能指标收集器"""
    print("=== 测试性能指标收集器 ===")
    
    collector = PerformanceCollector()
    
    # 测试启动收集器
    print("启动性能收集器...")
    collector.start()
    time.sleep(3)  # 等待收集数据
    
    # 测试停止收集器
    print("停止性能收集器...")
    collector.stop()
    
    print("性能收集器测试完成！")

def test_performance_monitor():
    """测试性能监控页面控制器"""
    print("\n=== 测试性能监控页面控制器 ===")
    
    monitor = PerformanceMonitor()
    
    # 测试阈值配置
    print("\n测试阈值配置：")
    cpu_threshold = monitor.getThreshold("cpu_usage")
    print(f"当前CPU阈值: {cpu_threshold}%")
    
    monitor.setThreshold("cpu_usage", 85)
    new_cpu_threshold = monitor.getThreshold("cpu_usage")
    print(f"更新后CPU阈值: {new_cpu_threshold}%")
    
    # 测试告警配置
    print("\n测试告警配置：")
    popup_enabled = monitor.getAlertConfig("enable_popup")
    print(f"当前弹出提醒配置: {popup_enabled}")
    
    monitor.setAlertConfig("enable_popup", False)
    new_popup_enabled = monitor.getAlertConfig("enable_popup")
    print(f"更新后弹出提醒配置: {new_popup_enabled}")
    
    # 测试更新指标
    print("\n测试更新指标：")
    test_metrics = {
        'cpu_usage': 75.5,
        'gpu_usage': 45.2,
        'memory_usage': 60.8,
        'task_throughput': 15,
        'failure_rate': 3.2,
        'total_tasks': 200,
        'success_tasks': 194,
        'failed_tasks': 6
    }
    monitor.updateMetrics(test_metrics)
    print("指标更新成功！")
    
    # 测试告警功能
    print("\n测试告警功能：")
    monitor.showAlert("CPU使用率过高！", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("告警显示成功！")
    
    # 测试数据导出（模拟）
    print("\n测试数据导出：")
    result = monitor.exportToFile("all", "24h", "test_export.json")
    print(f"导出结果: {result}")
    
    # 测试诊断包功能
    print("\n测试诊断包功能：")
    success = monitor.copyDiagnosticPackage()
    print(f"诊断包复制: {'成功' if success else '失败'}")
    
    print("\n性能监控页面控制器测试完成！")

def test_pubsub_integration():
    """测试PubSubService集成"""
    print("\n=== 测试PubSubService集成 ===")
    
    monitor = PerformanceMonitor()
    collector = PerformanceCollector()
    
    # 模拟性能数据推送
    def simulate_metrics():
        for i in range(5):
            metrics = {
                'cpu_usage': random.uniform(30, 80),
                'gpu_usage': random.uniform(20, 70),
                'memory_usage': random.uniform(40, 85),
                'task_throughput': random.randint(5, 20),
                'failure_rate': random.uniform(0, 15),
                'total_tasks': 100 + i * 10,
                'success_tasks': 95 + i * 10,
                'failed_tasks': 5
            }
            PubSubService.publish("<<PerformanceMetrics>>", metrics)
            print(f"推送性能数据 #{i+1}: {metrics}")
            time.sleep(1)
    
    # 启动模拟线程
    print("启动性能数据模拟...")
    simulation_thread = threading.Thread(target=simulate_metrics)
    simulation_thread.start()
    
    # 等待模拟完成
    simulation_thread.join()
    
    print("PubSubService集成测试完成！")

def test_full_integration():
    """测试完整集成流程"""
    print("\n=== 测试完整集成流程 ===")
    
    monitor = PerformanceMonitor()
    collector = PerformanceCollector()
    
    print("启动完整集成测试...")
    
    # 启动收集器
    collector.start()
    
    # 运行一段时间
    print("运行性能监控系统...")
    time.sleep(5)
    
    # 停止收集器
    collector.stop()
    
    print("完整集成测试完成！")

def main():
    """主测试函数"""
    print("=" * 60)
    print("Umi-OCR 性能监控界面测试脚本")
    print("=" * 60)
    
    try:
        # 运行所有测试
        test_performance_collector()
        test_performance_monitor()
        test_pubsub_integration()
        test_full_integration()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
