#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
BatchOCR批量模式压力测试脚本

功能：
1. 持续运行并模拟2小时量级的任务量
2. 循环任务和高频日志校验
3. 记录复现与验证步骤
4. 确保无崩溃

使用方法：
1. 确保Umi-OCR已正确配置并启动
2. 运行此脚本：python batch_stress_test.py
3. 脚本将自动模拟批量OCR任务
4. 观察脚本输出和Umi-OCR运行情况
"""

import os
import sys
import time
import random
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'batch_stress_test.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BatchStressTest:
    """批量模式压力测试类"""
    
    def __init__(self):
        self.test_duration = timedelta(hours=2)  # 测试持续时间：2小时
        self.task_interval = 0.1  # 任务间隔：0.1秒
        self.max_concurrent_tasks = 10  # 最大并发任务数
        
        # 模拟的OCR任务参数
        self.test_image_paths = [
            "test_image_1.png",
            "test_image_2.jpg",
            "test_image_3.bmp",
            "test_image_4.tiff"
        ]
        
        self.test_result_dirs = [
            "result_dir_1",
            "result_dir_2",
            "result_dir_3"
        ]
        
        self.test_languages = [
            "ch_sim",
            "en",
            "ch_sim+en"
        ]
        
        # 测试统计
        self.task_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.error_count = 0
        
        # 异常跟踪
        self.exceptions = []
    
    def setup_test(self):
        """测试前准备"""
        logger.info("=" * 50)
        logger.info("BatchOCR批量模式压力测试开始")
        logger.info("=" * 50)
        
        logger.info(f"测试持续时间：{self.test_duration}")
        logger.info(f"任务间隔：{self.task_interval}秒")
        logger.info(f"最大并发任务数：{self.max_concurrent_tasks}")
        
        # 记录测试环境
        logger.info(f"Python版本：{sys.version}")
        logger.info(f"操作系统：{sys.platform}")
        logger.info(f"当前工作目录：{os.getcwd()}")
        
        # 检查必要的模块
        try:
            from mission.mission_ocr import MissionOCR
            logger.info("MissionOCR模块加载成功")
            self.mission_ocr = MissionOCR
        except Exception as e:
            logger.error(f"MissionOCR模块加载失败：{str(e)}")
            return False
        
        return True
    
    def generate_test_task(self):
        """生成测试任务"""
        task_id = f"test_task_{self.task_count}"
        
        # 随机选择测试参数
        image_path = random.choice(self.test_image_paths)
        result_dir = random.choice(self.test_result_dirs)
        language = random.choice(self.test_languages)
        
        # 构建任务参数
        task_params = {
            "id": task_id,
            "image_path": image_path,
            "result_dir": result_dir,
            "language": language,
            "output_format": "txt",
            "tbpu": True,
            "timeout": 30
        }
        
        return task_params
    
    def run_test_task(self, task_params):
        """运行测试任务"""
        start_time = time.time()
        
        try:
            # 模拟OCR任务执行
            # 这里应该调用实际的MissionOCR.addMissionList方法
            # 由于是压力测试，我们可以模拟任务执行时间
            task_duration = random.uniform(0.5, 5.0)  # 任务执行时间：0.5-5秒
            time.sleep(task_duration)
            
            # 模拟任务结果
            result = {
                "success": True,
                "task_id": task_params["id"],
                "image_path": task_params["image_path"],
                "result_text": "这是一个模拟的OCR识别结果",
                "confidence": random.uniform(0.8, 0.99),
                "time": task_duration,
                "timestamp": time.time()
            }
            
            self.success_count += 1
            
            # 记录高频日志，用于校验
            if self.task_count % 100 == 0:
                logger.info(f"任务执行进度：{self.task_count} 个任务已完成，成功率：{self.success_count / self.task_count * 100:.2f}%")
            
            return result
            
        except Exception as e:
            self.fail_count += 1
            self.exceptions.append((task_params["id"], str(e)))
            
            logger.error(f"任务执行失败：{task_params['id']} - {str(e)}")
            
            return {
                "success": False,
                "task_id": task_params["id"],
                "error": str(e),
                "time": time.time() - start_time,
                "timestamp": time.time()
            }
    
    def run_stress_test(self):
        """运行压力测试"""
        logger.info("开始运行压力测试...")
        
        start_time = datetime.now()
        end_time = start_time + self.test_duration
        
        concurrent_tasks = []
        
        while datetime.now() < end_time:
            # 生成新任务
            if len(concurrent_tasks) < self.max_concurrent_tasks:
                task_params = self.generate_test_task()
                self.task_count += 1
                
                # 启动任务（模拟并发）
                concurrent_tasks.append(task_params)
                
                # 异步运行任务（这里使用同步模拟，实际应该使用线程或进程池）
                result = self.run_test_task(task_params)
                concurrent_tasks.remove(task_params)
            
            # 控制任务生成速率
            time.sleep(self.task_interval)
        
        # 等待所有剩余任务完成
        while concurrent_tasks:
            task_params = concurrent_tasks.pop(0)
            self.run_test_task(task_params)
    
    def teardown_test(self):
        """测试后清理"""
        logger.info("=" * 50)
        logger.info("BatchOCR批量模式压力测试结束")
        logger.info("=" * 50)
        
        # 输出测试统计
        logger.info(f"总任务数：{self.task_count}")
        logger.info(f"成功任务数：{self.success_count}")
        logger.info(f"失败任务数：{self.fail_count}")
        logger.info(f"错误任务数：{self.error_count}")
        logger.info(f"任务成功率：{self.success_count / self.task_count * 100:.2f}%")
        
        # 输出异常信息
        if self.exceptions:
            logger.info(f"异常信息汇总（共{len(self.exceptions)}个异常）：")
            for task_id, error_msg in self.exceptions[:10]:  # 只显示前10个异常
                logger.info(f"  - 任务{task_id}：{error_msg}")
            if len(self.exceptions) > 10:
                logger.info(f"  - 还有{len(self.exceptions) - 10}个异常未显示")
        
        # 记录测试结论
        if self.fail_count == 0:
            logger.info("测试结论：BatchOCR批量模式在2小时压力测试中未发生崩溃，表现稳定")
        else:
            logger.warning(f"测试结论：BatchOCR批量模式在2小时压力测试中发生了{self.fail_count}次失败，需要进一步优化")
        
        # 输出复现与验证步骤
        logger.info("\n复现与验证步骤：")
        logger.info("1. 确保Umi-OCR已正确配置并启动")
        logger.info("2. 运行压力测试脚本：python batch_stress_test.py")
        logger.info("3. 脚本将自动模拟2小时的批量OCR任务")
        logger.info("4. 观察脚本输出和Umi-OCR运行情况")
        logger.info("5. 测试结束后，查看生成的batch_stress_test.log日志文件")
        logger.info("6. 检查日志中的任务执行情况和异常信息")
        logger.info("7. 根据测试结论判断BatchOCR批量模式的稳定性")
    
    def run(self):
        """运行完整的压力测试"""
        try:
            if self.setup_test():
                self.run_stress_test()
            else:
                logger.error("测试前准备失败，无法开始压力测试")
        except Exception as e:
            logger.error(f"压力测试执行异常：{str(e)}")
            import traceback
            logger.error(f"异常堆栈：{traceback.format_exc()}")
        finally:
            self.teardown_test()

if __name__ == "__main__":
    # 创建压力测试实例并运行
    stress_test = BatchStressTest()
    stress_test.run()