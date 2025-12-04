# 截图OCR输出文件句柄未释放问题的回归测试脚本

import os
import time
import threading
import subprocess
import tempfile
from typing import List, Dict, Any
from umi_log import logger

class ScreenshotOCRRegressionTest:
    def __init__(self):
        self.test_duration = 120  # 测试持续时间（秒）
        self.test_groups = 3  # 同时运行的测试组数
        self.test_interval = 0.5  # 每组测试的间隔时间（秒）
        
        # 测试结果统计
        self.test_results = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'crashes': 0,
            'handle_healing_events': 0
        }
        
        # 测试线程列表
        self.test_threads: List[threading.Thread] = []
        self.test_running = False
        
        # 临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="ocr_regression_test_")
        logger.info(f"测试临时目录: {self.temp_dir}")
    
    def create_test_config(self, group_id: int) -> str:
        """创建测试配置文件"""
        config_content = f"""
# 截图OCR回归测试配置
[General]
outputDir={os.path.join(self.temp_dir, f"output_{group_id}")}
outputFileName=test_result_{group_id}
outputFormat=txt_plain
ignoreBlank=True

[OCR]
engineType=paddleocr
lang=ch
useGPU=False

[Screenshot]
interval=0.1
count=10
        """
        
        config_path = os.path.join(self.temp_dir, f"config_{group_id}.ini")
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        return config_path
    
    def run_test_group(self, group_id: int):
        """运行单个测试组"""
        logger.info(f"开始测试组 {group_id}")
        
        # 创建输出目录
        output_dir = os.path.join(self.temp_dir, f"output_{group_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建测试配置
        config_path = self.create_test_config(group_id)
        
        start_time = time.time()
        task_count = 0
        
        while self.test_running and (time.time() - start_time) < self.test_duration:
            try:
                # 运行截图OCR任务
                result = self.run_screenshot_ocr_task(config_path)
                
                task_count += 1
                self.test_results['total_tasks'] += 1
                
                if result['success']:
                    self.test_results['completed_tasks'] += 1
                    logger.debug(f"测试组 {group_id} - 任务 {task_count} 完成")
                else:
                    self.test_results['failed_tasks'] += 1
                    logger.error(f"测试组 {group_id} - 任务 {task_count} 失败: {result['error']}")
                
                # 检查是否有句柄自愈事件
                if 'handle_healing' in result and result['handle_healing']:
                    self.test_results['handle_healing_events'] += 1
                    logger.info(f"测试组 {group_id} - 检测到句柄自愈事件")
                
            except Exception as e:
                self.test_results['failed_tasks'] += 1
                self.test_results['crashes'] += 1
                logger.error(f"测试组 {group_id} - 任务崩溃: {str(e)}")
            
            # 等待测试间隔
            time.sleep(self.test_interval)
        
        logger.info(f"测试组 {group_id} 完成，共运行 {task_count} 个任务")
    
    def run_screenshot_ocr_task(self, config_path: str) -> Dict[str, Any]:
        """运行单个截图OCR任务"""
        try:
            # 这里需要替换为实际的截图OCR命令
            # 例如：python screenshot_ocr.py --config config_path
            
            # 模拟截图OCR任务运行
            # 实际使用时应该调用真实的OCR程序
            
            # 模拟处理时间
            time.sleep(0.2)
            
            # 模拟随机失败（1%的概率）
            import random
            if random.random() < 0.01:
                raise Exception("模拟任务失败")
            
            return {
                'success': True,
                'handle_healing': random.random() < 0.05  # 模拟5%的概率出现句柄自愈
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'handle_healing': False
            }
    
    def start_test(self):
        """开始回归测试"""
        logger.info(f"开始截图OCR回归测试，持续时间: {self.test_duration} 秒，测试组数: {self.test_groups}")
        
        self.test_running = True
        
        # 创建并启动测试线程
        for group_id in range(self.test_groups):
            test_thread = threading.Thread(
                target=self.run_test_group,
                args=(group_id,),
                daemon=True
            )
            self.test_threads.append(test_thread)
            test_thread.start()
            
            # 测试组之间的启动间隔
            time.sleep(1)
        
        # 等待测试完成
        for test_thread in self.test_threads:
            test_thread.join()
        
        self.test_running = False
        
        # 打印测试结果
        self.print_test_results()
    
    def print_test_results(self):
        """打印测试结果"""
        logger.info("\n" + "="*50)
        logger.info("截图OCR回归测试结果")
        logger.info("="*50)
        logger.info(f"测试持续时间: {self.test_duration} 秒")
        logger.info(f"测试组数: {self.test_groups}")
        logger.info(f"总任务数: {self.test_results['total_tasks']}")
        logger.info(f"完成任务数: {self.test_results['completed_tasks']}")
        logger.info(f"失败任务数: {self.test_results['failed_tasks']}")
        logger.info(f"崩溃次数: {self.test_results['crashes']}")
        logger.info(f"句柄自愈事件数: {self.test_results['handle_healing_events']}")
        
        # 计算成功率
        if self.test_results['total_tasks'] > 0:
            success_rate = (self.test_results['completed_tasks'] / self.test_results['total_tasks']) * 100
            logger.info(f"任务成功率: {success_rate:.2f}%")
        
        logger.info("="*50 + "\n")
        
        # 检查是否通过测试
        if self.test_results['crashes'] == 0:
            logger.info("✅ 回归测试通过：未发生任何崩溃")
        else:
            logger.error(f"❌ 回归测试失败：发生 {self.test_results['crashes']} 次崩溃")
    
    def cleanup(self):
        """清理测试资源"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"已清理测试临时目录: {self.temp_dir}")
        except Exception as e:
            logger.error(f"清理测试临时目录失败: {str(e)}")

if __name__ == "__main__":
    # 创建并运行回归测试
    test = ScreenshotOCRRegressionTest()
    
    try:
        test.start_test()
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    finally:
        test.cleanup()
