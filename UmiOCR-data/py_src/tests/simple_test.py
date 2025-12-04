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
from utils.safe_file_ops import safe_write, ensure_directory_exists

class SimpleHighConcurrencyTest:
    """简单的高并发文件写入测试"""
    
    def __init__(self, test_dir=None):
        if test_dir is None:
            self.test_dir = tempfile.mkdtemp(prefix="simple_test_")
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
    
    def worker(self, file_path, thread_id, num_writes):
        """线程工作函数，执行多次文件写入"""
        logger.info(f"Thread {thread_id} started, writing to {file_path}")
        
        for i in range(num_writes):
            try:
                content = f"Thread {thread_id}, write {i + 1}/{num_writes}: {time.time()}\n"
                safe_write(file_path, content, mode="a", encoding="utf-8", description=f"test_thread_{thread_id}")
                
                with self._lock:
                    self.results.append((thread_id, i))
                
                # 模拟OCR处理时间
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Thread {thread_id}, write {i + 1} failed: {e}")
                with self._lock:
                    self.errors.append((thread_id, i, str(e)))
        
        logger.info(f"Thread {thread_id} completed")
    
    def run_test(self, num_threads=10, num_writes_per_thread=20, output_file="test_output.txt"):
        """运行高并发写入测试"""
        logger.info(f"Starting high concurrency test: {num_threads} threads, {num_writes_per_thread} writes each")
        
        output_path = os.path.join(self.test_dir, output_file)
        ensure_directory_exists(output_path)
        
        # 创建初始文件
        safe_write(output_path, "Test started at: {}\n\n".format(time.time()), mode="w", encoding="utf-8", description="test_init")
        
        # 创建并启动线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=self.worker, args=(output_path, i, num_writes_per_thread), daemon=True)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 完成测试
        safe_write(output_path, "\n\nTest completed at: {}\n".format(time.time()), mode="a", encoding="utf-8", description="test_complete")
        
        # 验证文件内容
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                logger.info(f"File contains {len(lines)} lines")
        except Exception as e:
            logger.error(f"Failed to read test output file: {e}")
        
        # 记录统计信息
        stats = file_handle_manager.get_stats()
        logger.info(f"Test completed")
        logger.info(f"  Total writes attempted: {num_threads * num_writes_per_thread}")
        logger.info(f"  Successful writes: {len(self.results)}")
        logger.info(f"  Failed writes: {len(self.errors)}")
        logger.info(f"  File handle stats: {stats}")
        
        return len(self.errors) == 0
    
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
    test = SimpleHighConcurrencyTest()
    
    try:
        # 测试1: 10线程，每线程20次写入
        logger.info("\nTest 1: 10 threads, 20 writes each")
        success1 = test.run_test(num_threads=10, num_writes_per_thread=20)
        
        # 等待一下让系统稳定
        time.sleep(2)
        
        # 测试2: 15线程，每线程30次写入
        logger.info("\nTest 2: 15 threads, 30 writes each")
        success2 = test.run_test(num_threads=15, num_writes_per_thread=30, output_file="test_output2.txt")
        
        # 等待一下让句柄管理器完成最后的检查
        time.sleep(3)
        
        # 打印最终统计
        final_stats = file_handle_manager.get_stats()
        logger.info("\nFinal statistics:")
        logger.info(f"  Total handles created: {final_stats['total_handles']}")
        logger.info(f"  Active handles: {final_stats['active_handles']}")
        logger.info(f"  Pending writes: {final_stats['pending_writes']}")
        logger.info(f"  Write successes: {final_stats['write_successes']}")
        logger.info(f"  Write failures: {final_stats['write_failures']}")
        
        if success1 and success2:
            logger.info("\n✅ All tests passed successfully!")
            sys.exit(0)
        else:
            logger.error("\n❌ Some tests failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    
    finally:
        test.cleanup()
