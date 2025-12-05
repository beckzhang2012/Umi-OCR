#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============== CPU/GPU 切换回归测试 ===========
# ===============================================

import os
import time
import threading
import random
from typing import List, Dict, Any

from umi_log import logger
from mission.mission_ocr import __MissionOcrClass
from ocr.api.hardware_manager import HardwareManagerGlobal, BackendType, SwitchReason


class RegressionTest:
    """CPU/GPU切换回归测试"""
    
    def __init__(self):
        self.mission_ocr = __MissionOcrClass()
        self.hardware_manager = HardwareManagerGlobal
        
        # 测试配置
        self.test_image_path = "test_images/sample.png"  # 测试图像路径
        self.test_iterations = 100  # 测试迭代次数
        self.gpu_failure_probability = 0.1  # GPU故障概率
        self.gpu_recovery_interval = 30  # GPU恢复间隔（秒）
        
        # 测试结果
        self.test_results: List[Dict[str, Any]] = []
        self.failed_tasks = 0
        self.gpu_to_cpu_switches = 0
        self.cpu_to_gpu_switches = 0
        
        logger.info("回归测试已初始化")
    
    def run_test(self):
        """运行回归测试"""
        logger.info("开始CPU/GPU切换回归测试")
        
        # 检查测试图像是否存在
        if not os.path.exists(self.test_image_path):
            logger.error(f"测试图像不存在: {self.test_image_path}")
            return
        
        # 启动GPU故障模拟线程
        gpu_failure_thread = threading.Thread(target=self._simulate_gpu_failure, daemon=True)
        gpu_failure_thread.start()
        
        # 启动GPU恢复模拟线程
        gpu_recovery_thread = threading.Thread(target=self._simulate_gpu_recovery, daemon=True)
        gpu_recovery_thread.start()
        
        # 运行OCR测试任务
        for i in range(self.test_iterations):
            logger.info(f"运行测试迭代 {i+1}/{self.test_iterations}")
            
            start_time = time.time()
            
            # 创建OCR任务
            msnInfo = {
                "tbpu": False,  # 禁用TBPU
                "threads": 1,  # 单线程测试
            }
            
            msn = {
                "path": self.test_image_path,
            }
            
            # 执行OCR任务
            try:
                res = self.mission_ocr.msnTask(msnInfo, msn)
                
                # 记录测试结果
                test_result = {
                    "iteration": i+1,
                    "start_time": start_time,
                    "processing_time": time.time() - start_time,
                    "success": res["code"] == 100,
                    "current_backend": res.get("hardware_info", {}).get("current_backend"),
                    "switch_reason": res.get("hardware_info", {}).get("switch_reason"),
                    "result_data": res.get("data", ""),
                }
                
                self.test_results.append(test_result)
                
                if not test_result["success"]:
                    self.failed_tasks += 1
                    logger.error(f"测试迭代 {i+1} 失败")
                else:
                    logger.info(f"测试迭代 {i+1} 成功，处理时间: {test_result['processing_time']:.2f}秒")
            
            except Exception as e:
                self.failed_tasks += 1
                logger.error(f"测试迭代 {i+1} 发生异常: {e}")
            
            # 测试间隔
            time.sleep(0.1)
        
        # 停止模拟线程
        self._stop_simulating = True
        
        # 生成测试报告
        self._generate_test_report()
        
        logger.info("回归测试已完成")
    
    def _simulate_gpu_failure(self):
        """模拟GPU故障"""
        self._stop_simulating = False
        
        while not self._stop_simulating:
            try:
                # 随机生成GPU故障
                if random.random() < self.gpu_failure_probability:
                    current_backend = self.hardware_manager.get_current_backend()
                    
                    if current_backend == BackendType.GPU:
                        # 模拟GPU故障，切换到CPU
                        logger.info("模拟GPU故障，切换到CPU后端")
                        self.hardware_manager.switch_to_backend(BackendType.CPU, SwitchReason.GPU_ERROR)
                        self.gpu_to_cpu_switches += 1
                
                # 故障模拟间隔
                time.sleep(1.0)
            
            except Exception as e:
                logger.error(f"GPU故障模拟线程发生错误: {e}")
                time.sleep(1.0)
    
    def _simulate_gpu_recovery(self):
        """模拟GPU恢复"""
        while not getattr(self, "_stop_simulating", False):
            try:
                current_backend = self.hardware_manager.get_current_backend()
                
                if current_backend == BackendType.CPU:
                    # 模拟GPU恢复，切换回GPU
                    logger.info("模拟GPU恢复，切换回GPU后端")
                    self.hardware_manager.switch_to_backend(BackendType.GPU, SwitchReason.GPU_RECOVERED)
                    self.cpu_to_gpu_switches += 1
                
                # 恢复模拟间隔
                time.sleep(self.gpu_recovery_interval)
            
            except Exception as e:
                logger.error(f"GPU恢复模拟线程发生错误: {e}")
                time.sleep(self.gpu_recovery_interval)
    
    def _generate_test_report(self):
        """生成测试报告"""
        logger.info("\n=== CPU/GPU切换回归测试报告 ===")
        
        # 测试统计
        total_tasks = self.test_iterations
        successful_tasks = total_tasks - self.failed_tasks
        success_rate = (successful_tasks / total_tasks) * 100
        
        logger.info(f"总测试任务数: {total_tasks}")
        logger.info(f"成功任务数: {successful_tasks}")
        logger.info(f"失败任务数: {self.failed_tasks}")
        logger.info(f"任务成功率: {success_rate:.2f}%")
        
        logger.info(f"GPU到CPU切换次数: {self.gpu_to_cpu_switches}")
        logger.info(f"CPU到GPU切换次数: {self.cpu_to_gpu_switches}")
        
        # 性能统计
        if self.test_results:
            processing_times = [r["processing_time"] for r in self.test_results if r["success"]]
            
            if processing_times:
                average_processing_time = sum(processing_times) / len(processing_times)
                min_processing_time = min(processing_times)
                max_processing_time = max(processing_times)
                
                logger.info(f"平均处理时间: {average_processing_time:.2f}秒")
                logger.info(f"最小处理时间: {min_processing_time:.2f}秒")
                logger.info(f"最大处理时间: {max_processing_time:.2f}秒")
        
        # 后端使用统计
        backend_usage = {}
        for r in self.test_results:
            backend = r["current_backend"]
            if backend:
                backend_usage[backend] = backend_usage.get(backend, 0) + 1
        
        logger.info("\n后端使用统计:")
        for backend, count in backend_usage.items():
            percentage = (count / total_tasks) * 100
            logger.info(f"{backend}: {count}次 ({percentage:.2f}%)")
        
        # 切换原因统计
        switch_reasons = {}
        for r in self.test_results:
            reason = r["switch_reason"]
            if reason:
                switch_reasons[reason] = switch_reasons.get(reason, 0) + 1
        
        if switch_reasons:
            logger.info("\n切换原因统计:")
            for reason, count in switch_reasons.items():
                logger.info(f"{reason}: {count}次")
        
        logger.info("\n=== 测试报告结束 ===")
        
        # 将测试报告写入文件
        report_file_path = "regression_test_report.txt"
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write("=== CPU/GPU切换回归测试报告 ===\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write(f"总测试任务数: {total_tasks}\n")
            f.write(f"成功任务数: {successful_tasks}\n")
            f.write(f"失败任务数: {self.failed_tasks}\n")
            f.write(f"任务成功率: {success_rate:.2f}%\n")
            f.write(f"GPU到CPU切换次数: {self.gpu_to_cpu_switches}\n")
            f.write(f"CPU到GPU切换次数: {self.cpu_to_gpu_switches}\n")
            
            if processing_times:
                f.write(f"平均处理时间: {average_processing_time:.2f}秒\n")
                f.write(f"最小处理时间: {min_processing_time:.2f}秒\n")
                f.write(f"最大处理时间: {max_processing_time:.2f}秒\n")
            
            f.write("\n后端使用统计:\n")
            for backend, count in backend_usage.items():
                percentage = (count / total_tasks) * 100
                f.write(f"{backend}: {count}次 ({percentage:.2f}%)\n")
            
            if switch_reasons:
                f.write("\n切换原因统计:\n")
                for reason, count in switch_reasons.items():
                    f.write(f"{reason}: {count}次\n")
            
            f.write("\n=== 测试报告结束 ===\n")
        
        logger.info(f"测试报告已写入文件: {report_file_path}")


if __name__ == "__main__":
    # 运行回归测试
    test = RegressionTest()
    test.run_test()
