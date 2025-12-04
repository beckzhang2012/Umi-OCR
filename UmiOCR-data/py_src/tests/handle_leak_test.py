#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句柄泄漏回归测试脚本
用于模拟高并发导出场景，验证修复效果
"""

import os
import sys
import time
import threading
import tempfile
import shutil
from typing import List, Dict, Optional

# 添加项目路径到Python路径
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 添加imports目录到Python路径
imports_path = os.path.join(project_path, "imports")
if imports_path not in sys.path:
    sys.path.insert(0, imports_path)

from umi_log import logger

from utils.handle_pool import HandlePoolInstance
from utils.handle_scanner import HandleScannerInstance
from utils.file_writer import SafeFileWriter

class HandleLeakTest:
    """句柄泄漏测试类"""
    
    def __init__(self):
        self._test_dir = tempfile.mkdtemp(prefix="UmiOCR_Test_")
        self._threads: List[threading.Thread] = []
        self._running = False
        self._test_results: List[Dict] = []
        self._lock = threading.Lock()
        
        # 测试配置
        self._config = {
            "duration": 120,  # 测试持续时间（秒）
            "concurrent_threads": 3,  # 并发线程数
            "tasks_per_thread": 100,  # 每个线程的任务数
            "files_per_task": 10,  # 每个任务的文件数
            "file_size": 1024,  # 每个文件的大小（字节）
        }
        
        logger.info(f"测试目录: {self._test_dir}")
    
    def setup(self):
        """测试设置"""
        logger.info("=== 测试设置 ===")
        
        # 启动句柄扫描器
        HandleScannerInstance.start(scan_interval=10, timeout_threshold=30)
        
        # 创建测试文件
        self._create_test_files()
        
        logger.info("测试设置完成")
    
    def _create_test_files(self):
        """创建测试文件"""
        logger.info(f"创建 {self._config['concurrent_threads'] * self._config['tasks_per_thread'] * self._config['files_per_task']} 个测试文件...")
        
        for thread_idx in range(self._config['concurrent_threads']):
            thread_dir = os.path.join(self._test_dir, f"thread_{thread_idx}")
            os.makedirs(thread_dir, exist_ok=True)
            
            for task_idx in range(self._config['tasks_per_thread']):
                task_dir = os.path.join(thread_dir, f"task_{task_idx}")
                os.makedirs(task_dir, exist_ok=True)
                
                for file_idx in range(self._config['files_per_task']):
                    file_path = os.path.join(task_dir, f"file_{file_idx}.txt")
                    
                    # 创建测试文件
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("X" * self._config['file_size'])
        
        logger.info("测试文件创建完成")
    
    def run(self):
        """运行测试"""
        logger.info("=== 开始测试 ===")
        logger.info(f"测试配置: {self._config}")
        
        self._running = True
        
        # 启动测试线程
        for thread_idx in range(self._config['concurrent_threads']):
            thread = threading.Thread(
                target=self._thread_test,
                args=(thread_idx,),
                name=f"TestThread_{thread_idx}"
            )
            self._threads.append(thread)
            thread.start()
        
        # 监控测试进度
        self._monitor_test()
        
        # 等待所有线程完成
        for thread in self._threads:
            thread.join()
        
        self._running = False
        
        logger.info("=== 测试完成 ===")
    
    def _thread_test(self, thread_idx: int):
        """线程测试函数"""
        thread_name = threading.current_thread().name
        logger.info(f"线程 {thread_name} 开始运行")
        
        thread_dir = os.path.join(self._test_dir, f"thread_{thread_idx}")
        
        for task_idx in range(self._config['tasks_per_thread']):
            if not self._running:
                break
                
            task_dir = os.path.join(thread_dir, f"task_{task_idx}")
            output_file = os.path.join(task_dir, f"output_{task_idx}.txt")
            
            try:
                # 模拟OCR导出过程
                self._simulate_ocr_export(output_file, task_dir)
                
                with self._lock:
                    self._test_results.append({
                        "thread_idx": thread_idx,
                        "task_idx": task_idx,
                        "status": "success",
                        "timestamp": time.time()
                    })
                
                if (task_idx + 1) % 10 == 0:
                    logger.info(f"线程 {thread_name} 已完成 {task_idx + 1}/{self._config['tasks_per_thread']} 个任务")
                    
            except Exception as e:
                logger.error(f"线程 {thread_name} 任务 {task_idx} 失败: {e}")
                
                with self._lock:
                    self._test_results.append({
                        "thread_idx": thread_idx,
                        "task_idx": task_idx,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": time.time()
                    })
        
        logger.info(f"线程 {thread_name} 运行结束")
    
    def _simulate_ocr_export(self, output_file: str, input_dir: str):
        """模拟OCR导出过程"""
        # 使用安全文件写入器
        with SafeFileWriter(output_file, "w", encoding="utf-8") as writer:
            writer.write(f"OCR导出结果\n导出时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n")
            
            # 读取输入目录下的所有文件
            for filename in os.listdir(input_dir):
                if filename.endswith(".txt") and not filename.startswith("output_"):
                    file_path = os.path.join(input_dir, filename)
                    
                    # 模拟OCR识别过程
                    time.sleep(0.01)  # 模拟识别延迟
                    
                    # 写入结果
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()[:100]  # 只取前100个字符
                    
                    writer.write(f"文件: {filename}\n")
                    writer.write(f"识别文本: {content}\n")
                    writer.write("\n")
    
    def _monitor_test(self):
        """监控测试进度"""
        start_time = time.time()
        
        while self._running:
            elapsed_time = time.time() - start_time
            
            if elapsed_time >= self._config['duration']:
                logger.info("测试时间已到，停止测试")
                self._running = False
                break
            
            # 每10秒打印一次进度
            if int(elapsed_time) % 10 == 0:
                with self._lock:
                    completed_tasks = len(self._test_results)
                    success_tasks = len([r for r in self._test_results if r['status'] == 'success'])
                    failed_tasks = len([r for r in self._test_results if r['status'] == 'failed'])
                
                progress = (completed_tasks / (self._config['concurrent_threads'] * self._config['tasks_per_thread'])) * 100
                logger.info(f"测试进度: {progress:.1f}% ({completed_tasks}/{self._config['concurrent_threads'] * self._config['tasks_per_thread']} 个任务)")
                logger.info(f"成功: {success_tasks}, 失败: {failed_tasks}")
                
                # 打印句柄统计信息
                handles = HandlePoolInstance.get_all_handles()
                logger.info(f"当前句柄数: {len(handles)}")
            
            time.sleep(1)
    
    def generate_report(self):
        """生成测试报告"""
        logger.info("=== 生成测试报告 ===")
        
        total_tasks = len(self._test_results)
        success_tasks = len([r for r in self._test_results if r['status'] == 'success'])
        failed_tasks = len([r for r in self._test_results if r['status'] == 'failed'])
        
        success_rate = (success_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        report = f"句柄泄漏回归测试报告\n"
        report += "=" * 50 + "\n"
        report += f"测试配置:\n"
        report += f"  持续时间: {self._config['duration']}秒\n"
        report += f"  并发线程数: {self._config['concurrent_threads']}\n"
        report += f"  每个线程任务数: {self._config['tasks_per_thread']}\n"
        report += f"  每个任务文件数: {self._config['files_per_task']}\n"
        report += f"  文件大小: {self._config['file_size']}字节\n"
        report += "=" * 50 + "\n"
        report += f"测试结果:\n"
        report += f"  总任务数: {total_tasks}\n"
        report += f"  成功任务数: {success_tasks}\n"
        report += f"  失败任务数: {failed_tasks}\n"
        report += f"  成功率: {success_rate:.2f}%\n"
        report += "=" * 50 + "\n"
        
        # 打印句柄统计信息
        handles = HandlePoolInstance.get_all_handles()
        report += f"句柄统计:\n"
        report += f"  当前句柄数: {len(handles)}\n"
        
        if handles:
            report += "  句柄详情:\n"
            for handle in handles[:10]:  # 只显示前10个
                report += f"    - {handle['path']} (模式: {handle['mode']}, 访问时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(handle['access_time']))})\n"
            
            if len(handles) > 10:
                report += f"    ... 还有 {len(handles) - 10} 个句柄\n"
        
        # 打印失败任务详情
        if failed_tasks > 0:
            report += "=" * 50 + "\n"
            report += "失败任务详情:\n"
            for result in self._test_results[:10]:  # 只显示前10个
                if result['status'] == 'failed':
                    report += f"  线程 {result['thread_idx']} 任务 {result['task_idx']}: {result['error']}\n"
            
            if failed_tasks > 10:
                report += f"  ... 还有 {failed_tasks - 10} 个失败任务\n"
        
        # 保存报告文件
        report_file = os.path.join(self._test_dir, "test_report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info(f"测试报告已保存到: {report_file}")
        logger.info(report)
    
    def cleanup(self):
        """测试清理"""
        logger.info("=== 测试清理 ===")
        
        # 停止句柄扫描器
        HandleScannerInstance.stop()
        
        # 关闭所有文件写入器
        from utils.file_writer import FileWriterFactory
        FileWriterFactory.close_all_writers()
        
        # 清理测试目录
        if os.path.exists(self._test_dir):
            try:
                shutil.rmtree(self._test_dir)
                logger.info(f"测试目录已删除: {self._test_dir}")
            except Exception as e:
                logger.error(f"删除测试目录失败: {e}")
        
        logger.info("测试清理完成")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()

def main():
    """主函数"""
    test = HandleLeakTest()
    
    try:
        test.setup()
        test.run()
        test.generate_report()
        
        # 检查是否有句柄泄漏
        handles = HandlePoolInstance.get_all_handles()
        if handles:
            logger.error(f"测试结束后发现 {len(handles)} 个未关闭句柄，可能存在泄漏")
            return 1
        else:
            logger.info("测试结束后未发现未关闭句柄，句柄管理正常")
            return 0
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return 1
    finally:
        test.cleanup()

if __name__ == "__main__":
    sys.exit(main())