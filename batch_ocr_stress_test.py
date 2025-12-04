#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BatchOCR 压力测试脚本
用于验证修复后的BatchOCR在长时间运行下的稳定性
模拟2小时量级的任务量，通过循环任务和高频日志校验确保无崩溃
"""

import os
import time
import threading
import random
import sys
from umi_log import logger

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'UmiOCR-data', 'py_src'))

from tag_pages.BatchOCR import BatchOCR
from mission.mission_ocr import MissionOCR

class StressTest:
    def __init__(self):
        self.test_duration = 2 * 60 * 60  # 2小时测试时间
        self.tasks_per_minute = 100  # 每分钟任务数量
        self.concurrent_threads = 5  # 并发线程数
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = 0
        self.test_running = False
        self.batch_ocr = BatchOCR()
        
        # 测试图片路径（使用示例图片或生成测试图片）
        self.test_images = self._get_test_images()
        if not self.test_images:
            logger.error("未找到测试图片，请确保测试目录下有图片文件")
            sys.exit(1)
        
        logger.info(f"找到 {len(self.test_images)} 张测试图片")
        
    def _get_test_images(self):
        """获取测试图片列表"""
        test_dir = os.path.dirname(__file__)
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        images = []
        
        # 遍历目录找图片
        for root, _, files in os.walk(test_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    images.append(os.path.join(root, file))
                    if len(images) >= 10:  # 最多取10张测试图片循环使用
                        return images
        
        return images
    
    def _run_ocr_task(self, image_path, thread_id):
        """运行单个OCR任务"""
        try:
            # 创建任务信息
            msn_info = {
                "onStart": lambda info: logger.debug(f"线程 {thread_id}: 任务开始"),
                "onReady": lambda info, msn: logger.debug(f"线程 {thread_id}: 任务准备就绪"),
                "onGet": lambda info, msn, res: self._on_task_complete(thread_id, res),
                "onEnd": lambda info, msg: logger.debug(f"线程 {thread_id}: 任务结束 - {msg}"),
                "argd": {
                    "mission.dirType": "source",
                    "mission.dir": os.path.dirname(image_path),
                    "mission.ignoreBlank": True,
                    "mission.filesType.txt": True,
                    "mission.datetimeFormat": "%Y%m%d_%H%M%S",
                    "mission.fileNameFormat": "test_result_%date"
                }
            }
            
            # 添加任务
            msn_list = [{"path": image_path}]
            msn_id = MissionOCR.addMissionList(msn_info, msn_list)
            
            if msn_id.startswith("[Error]"):
                logger.error(f"线程 {thread_id}: 添加任务失败 - {msn_id}")
                self.failed_tasks += 1
                return False
            
            self.total_tasks += 1
            return True
            
        except Exception as e:
            logger.error(f"线程 {thread_id}: 任务执行异常 - {e}", exc_info=True)
            self.failed_tasks += 1
            return False
    
    def _on_task_complete(self, thread_id, result):
        """任务完成回调"""
        self.completed_tasks += 1
        
        # 每完成100个任务打印一次统计信息
        if self.completed_tasks % 100 == 0:
            elapsed = time.time() - self.start_time
            tasks_per_second = self.completed_tasks / elapsed if elapsed > 0 else 0
            logger.info(f"=== 任务统计 ===")
            logger.info(f"总任务数: {self.total_tasks}")
            logger.info(f"已完成: {self.completed_tasks}")
            logger.info(f"失败: {self.failed_tasks}")
            logger.info(f"成功率: {self.completed_tasks/self.total_tasks*100:.2f}%")
            logger.info(f"处理速度: {tasks_per_second:.2f} 任务/秒")
            logger.info(f"已运行时间: {elapsed/60:.1f} 分钟")
            logger.info(f"预计剩余时间: {(self.test_duration - elapsed)/60:.1f} 分钟")
    
    def _thread_worker(self, thread_id):
        """线程工作函数"""
        logger.info(f"线程 {thread_id} 启动")
        
        while self.test_running:
            # 随机选择一张测试图片
            image_path = random.choice(self.test_images)
            
            # 运行OCR任务
            self._run_ocr_task(image_path, thread_id)
            
            # 控制任务速率
            time.sleep(60 / self.tasks_per_minute / self.concurrent_threads)
        
        logger.info(f"线程 {thread_id} 停止")
    
    def run(self):
        """开始压力测试"""
        logger.info("=" * 60)
        logger.info("BatchOCR 压力测试开始")
        logger.info("=" * 60)
        logger.info(f"测试时间: {self.test_duration/3600:.1f} 小时")
        logger.info(f"任务速率: {self.tasks_per_minute} 任务/分钟")
        logger.info(f"并发线程: {self.concurrent_threads}")
        logger.info(f"预计总任务数: {self.tasks_per_minute * self.test_duration / 60}")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        self.test_running = True
        
        # 创建并启动线程
        threads = []
        for i in range(self.concurrent_threads):
            thread = threading.Thread(target=self._thread_worker, args=(i,))
            threads.append(thread)
            thread.start()
            time.sleep(1)  # 线程启动间隔
        
        # 监控测试进度
        try:
            while self.test_running:
                elapsed = time.time() - self.start_time
                
                if elapsed >= self.test_duration:
                    self.test_running = False
                    break
                
                # 每5分钟打印一次系统状态
                if int(elapsed) % 300 == 0:
                    logger.info(f"\n=== 系统状态 (运行 {elapsed/60:.1f} 分钟) ===")
                    logger.info(f"活跃线程数: {threading.active_count()}")
                    logger.info(f"当前任务统计: 总={self.total_tasks}, 完成={self.completed_tasks}, 失败={self.failed_tasks}")
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n用户中断测试")
            self.test_running = False
        
        # 等待所有线程完成
        logger.info("等待线程完成...")
        for thread in threads:
            thread.join(timeout=10)
        
        # 停止所有任务
        MissionOCR.stopAllMission()
        
        # 生成测试报告
        self._generate_report()
    
    def _generate_report(self):
        """生成测试报告"""
        elapsed = time.time() - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info("BatchOCR 压力测试完成")
        logger.info("=" * 60)
        logger.info(f"实际测试时间: {elapsed/3600:.2f} 小时 ({elapsed:.0f} 秒)")
        logger.info(f"总任务数: {self.total_tasks}")
        logger.info(f"已完成任务: {self.completed_tasks}")
        logger.info(f"失败任务: {self.failed_tasks}")
        logger.info(f"任务成功率: {self.completed_tasks/self.total_tasks*100:.2f}%")
        logger.info(f"平均处理速度: {self.completed_tasks/elapsed:.2f} 任务/秒")
        logger.info(f"最大并发线程数: {self.concurrent_threads}")
        logger.info(f"活跃线程峰值: {threading.active_count()}")
        
        if self.failed_tasks == 0:
            logger.info("\n✅ 测试通过: 无任务失败")
        else:
            logger.warning(f"\n⚠️ 测试警告: 有 {self.failed_tasks} 个任务失败")
        
        logger.info("=" * 60)
        
        # 保存报告到文件
        report_path = os.path.join(os.path.dirname(__file__), 'stress_test_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("BatchOCR 压力测试报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}\n")
            f.write(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write(f"实际测试时长: {elapsed/3600:.2f} 小时 ({elapsed:.0f} 秒)\n")
            f.write(f"总任务数: {self.total_tasks}\n")
            f.write(f"已完成任务: {self.completed_tasks}\n")
            f.write(f"失败任务: {self.failed_tasks}\n")
            f.write(f"任务成功率: {self.completed_tasks/self.total_tasks*100:.2f}%\n")
            f.write(f"平均处理速度: {self.completed_tasks/elapsed:.2f} 任务/秒\n")
            f.write(f"并发线程数: {self.concurrent_threads}\n")
            f.write("=" * 60 + "\n")
        
        logger.info(f"测试报告已保存到: {report_path}")

if __name__ == "__main__":
    test = StressTest()
    test.run()