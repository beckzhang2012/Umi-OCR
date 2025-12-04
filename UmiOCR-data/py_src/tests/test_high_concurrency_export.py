import os
import sys
import time
import threading
import tempfile
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.file_handle_manager import file_handle_manager
from utils.ui_notifier import ui_notifier
from ocr.output.output_txt import OutputTxt
from ocr.output.output_csv import OutputCsv
from ocr.output.output_jsonl import OutputJsonl

class HighConcurrencyTest:
    """高并发导出测试类"""
    
    def __init__(self, test_dir=None):
        if test_dir is None:
            self.test_dir = tempfile.mkdtemp(prefix="umi_ocr_test_")
        else:
            self.test_dir = test_dir
            os.makedirs(self.test_dir, exist_ok=True)
        
        self.results = []
        self.errors = []
        self._lock = threading.Lock()
        
        # 启动句柄管理器和UI通知器
        file_handle_manager.start_monitoring(interval=2)
        ui_notifier.start_auto_notification(interval=3)
        
        logger.info(f"Test directory: {self.test_dir}")
    
    def create_test_result(self, index, output_type="txt"):
        """创建测试用的OCR结果"""
        return {
            'path': f"test_image_{index}.png",
            'fileName': f"test_image_{index}",
            'code': 100,  # 成功状态码
            'data': [
                {'text': f"测试文本内容 {index}", 'confidence': 0.95},
                {'text': f"第二行测试文本 {index}", 'confidence': 0.92}
            ]
        }
    
    def test_output_module(self, output_class, output_args, num_tasks=100, thread_count=10):
        """测试指定的输出模块"""
        logger.info(f"Testing {output_class.__name__} with {num_tasks} tasks and {thread_count} threads")
        
        # 创建输出实例
        try:
            output = output_class(output_args)
        except Exception as e:
            logger.error(f"Failed to create output instance: {e}")
            return False
        
        # 定义线程工作函数
        def worker(task_ids):
            for task_id in task_ids:
                try:
                    result = self.create_test_result(task_id)
                    output.print(result)
                    with self._lock:
                        self.results.append(task_id)
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    with self._lock:
                        self.errors.append((task_id, str(e)))
        
        # 将任务分配给线程
        tasks_per_thread = num_tasks // thread_count
        threads = []
        
        for i in range(thread_count):
            start = i * tasks_per_thread
            end = (i + 1) * tasks_per_thread if i < thread_count - 1 else num_tasks
            task_ids = range(start, end)
            
            thread = threading.Thread(target=worker, args=(task_ids,), daemon=True)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 调用结束方法
        try:
            if hasattr(output, 'onEnd'):
                output.onEnd()
        except Exception as e:
            logger.error(f"onEnd method failed: {e}")
            self.errors.append(('onEnd', str(e)))
        
        # 记录统计信息
        stats = file_handle_manager.get_stats()
        logger.info(f"Test completed for {output_class.__name__}")
        logger.info(f"  Total tasks: {num_tasks}")
        logger.info(f"  Successful: {len(self.results)}")
        logger.info(f"  Failed: {len(self.errors)}")
        logger.info(f"  File handle stats: {stats}")
        
        return len(self.errors) == 0
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        logger.info("Starting comprehensive high concurrency test")
        
        test_configs = [
            # (输出类, 配置参数, 任务数量, 线程数量, 测试名称)
            (OutputTxt, {
                "outputDir": os.path.join(self.test_dir, "txt_output"),
                "outputFileName": "test_output",
                "ignoreBlank": False,
                "startDatetime": "2023-01-01 12:00:00"
            }, 200, 15, "TXT Output"),
            
            (OutputCsv, {
                "outputDir": os.path.join(self.test_dir, "csv_output"),
                "outputFileName": "test_output",
                "ignoreBlank": False
            }, 150, 10, "CSV Output"),
            
            (OutputJsonl, {
                "outputDir": os.path.join(self.test_dir, "jsonl_output"),
                "outputFileName": "test_output",
                "ignoreBlank": False
            }, 180, 12, "JSONL Output"),
        ]
        
        all_passed = True
        
        for output_class, config, num_tasks, thread_count, test_name in test_configs:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running test: {test_name}")
            logger.info(f"{'='*60}")
            
            # 重置结果
            self.results.clear()
            self.errors.clear()
            
            # 运行测试
            start_time = time.time()
            passed = self.test_output_module(output_class, config, num_tasks, thread_count)
            end_time = time.time()
            
            logger.info(f"Test '{test_name}' completed in {end_time - start_time:.2f} seconds")
            
            if passed:
                logger.info(f"Test '{test_name}' PASSED")
            else:
                logger.error(f"Test '{test_name}' FAILED with {len(self.errors)} errors")
                all_passed = False
            
            # 等待一下让系统稳定
            time.sleep(2)
        
        # 最终统计
        final_stats = file_handle_manager.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Comprehensive test completed")
        logger.info(f"{'='*60}")
        logger.info(f"Final file handle stats: {final_stats}")
        
        if all_passed:
            logger.info("ALL TESTS PASSED!")
        else:
            logger.error("SOME TESTS FAILED!")
        
        return all_passed
    
    def cleanup(self):
        """清理测试资源"""
        file_handle_manager.stop_monitoring()
        ui_notifier.stop_auto_notification()
        
        try:
            shutil.rmtree(self.test_dir)
            logger.info(f"Cleaned up test directory: {self.test_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup test directory: {e}")

if __name__ == "__main__":
    # 运行测试
    test = HighConcurrencyTest()
    
    try:
        success = test.run_comprehensive_test()
        
        # 等待一下让句柄管理器完成最后的检查
        time.sleep(3)
        
        # 打印最终统计
        final_stats = file_handle_manager.get_stats()
        logger.info(f"\nFinal statistics:")
        logger.info(f"  Total handles created: {final_stats['total_handles']}")
        logger.info(f"  Active handles: {final_stats['active_handles']}")
        logger.info(f"  Pending writes: {final_stats['pending_writes']}")
        logger.info(f"  Write successes: {final_stats['write_successes']}")
        logger.info(f"  Write failures: {final_stats['write_failures']}")
        
        if success:
            logger.info("\n✅ All tests passed successfully!")
            sys.exit(0)
        else:
            logger.error("\n❌ Some tests failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    
    finally:
        test.cleanup()
