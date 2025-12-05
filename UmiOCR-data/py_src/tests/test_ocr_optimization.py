# ===============================================
# =============== OCR优化测试脚本 ===============
# ===============================================

import os
import time
import sys
import tempfile
from PIL import Image
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from umi_log import logger
from mission.mission_ocr import MissionOCR
from optimization.ocr_optimization import (
    InputSlicer,
    MemoryPool,
    TextureCache,
    TaskScheduler,
    ThroughputMonitor,
    get_memory_pool,
    get_texture_cache,
    get_task_scheduler,
    get_throughput_monitor
)


class OCROptimizationTest:
    """OCR优化测试类"""
    
    def __init__(self):
        self.test_images_dir = self._create_test_images()
        self.test_image_paths = self._get_test_image_paths()
        
    def _create_test_images(self) -> str:
        """创建测试图片"""
        temp_dir = tempfile.mkdtemp()
        
        # 创建不同分辨率的测试图片
        resolutions = [
            (512, 512),    # 小图
            (1024, 1024),  # 中图
            (2048, 2048),  # 大图
            (4096, 4096),  # 超大图
            (8192, 8192),  # 特大图
        ]
        
        for i, (width, height) in enumerate(resolutions):
            for j in range(2):  # 每种分辨率创建2张图片
                img = Image.new('RGB', (width, height), color='white')
                img_path = os.path.join(temp_dir, f"test_{i}_{j}.png")
                img.save(img_path)
                img.close()
        
        logger.info(f"创建了 {len(resolutions)*2} 张测试图片在: {temp_dir}")
        return temp_dir
    
    def _get_test_image_paths(self) -> list:
        """获取测试图片路径"""
        paths = []
        for filename in os.listdir(self.test_images_dir):
            if filename.endswith('.png'):
                paths.append(os.path.join(self.test_images_dir, filename))
        return paths
    
    def test_input_slicer(self):
        """测试输入切片编排器"""
        logger.info("=== 测试输入切片编排器 ===")
        
        slicer = InputSlicer(max_segments=6)
        
        for img_path in self.test_image_paths:
            segments = slicer.slice_image(img_path)
            logger.info(f"图片 {os.path.basename(img_path)} 被分割为 {len(segments)} 个区域")
            
            for i, segment in enumerate(segments):
                logger.info(f"  区域 {i+1}: 坐标={segment['coords']}")
        
        logger.info("输入切片编排器测试完成")
        return True
    
    def test_memory_pool(self):
        """测试内存池"""
        logger.info("=== 测试内存池 ===")
        
        memory_pool = MemoryPool(max_buffers=5, buffer_size=1024 * 1024 * 10)  # 10MB per buffer
        
        # 测试获取和释放buffer
        buffers = []
        for i in range(5):
            buffer = memory_pool.acquire()
            if buffer:
                buffers.append(buffer)
                logger.info(f"获取buffer {i+1}, 大小: {buffer.nbytes / 1024 / 1024:.2f}MB")
        
        logger.info(f"内存池状态: 空闲={len(memory_pool.free_buffers)}, 使用中={len(memory_pool.used_buffers)}")
        
        # 测试释放buffer
        for i, buffer in enumerate(buffers):
            memory_pool.release(buffer)
            logger.info(f"释放buffer {i+1}")
        
        logger.info(f"内存池状态: 空闲={len(memory_pool.free_buffers)}, 使用中={len(memory_pool.used_buffers)}")
        
        # 测试获取超过最大数量的buffer
        buffers = []
        for i in range(6):
            buffer = memory_pool.acquire()
            if buffer:
                buffers.append(buffer)
                logger.info(f"获取buffer {i+1}")
            else:
                logger.warning(f"无法获取buffer {i+1} (已达到最大数量)")
        
        logger.info("内存池测试完成")
        return True
    
    def test_task_scheduler(self):
        """测试任务调度器"""
        logger.info("=== 测试任务调度器 ===")
        
        scheduler = TaskScheduler(small_image_threshold=1024*1024)  # 1MP
        
        # 添加测试任务
        for img_path in self.test_image_paths:
            # 估算图片大小
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    size = width * height
            except:
                size = 0
            
            task = {
                "path": img_path,
                "width": width,
                "height": height,
                "size": size
            }
            
            scheduler.add_task(task)
            logger.info(f"添加任务: {os.path.basename(img_path)}, 大小: {size:,} 像素")
        
        logger.info(f"任务队列状态: 大图={len(scheduler.large_image_queue)}, 小图={len(scheduler.small_image_queue)}")
        
        # 测试获取任务
        logger.info("\n测试获取任务:")
        for i in range(5):
            task = scheduler.get_task(prefer_small=True)
            if task:
                logger.info(f"  获取任务 {i+1}: {os.path.basename(task['path'])}, 大小: {task['size']:,} 像素")
        
        logger.info("任务调度器测试完成")
        return True
    
    def test_throughput_monitor(self):
        """测试吞吐监测器"""
        logger.info("=== 测试吞吐监测器 ===")
        
        monitor = ThroughputMonitor()
        
        # 模拟一些批次数据
        for i in range(5):
            batch_size = np.random.randint(1, 10)
            processing_time = np.random.uniform(0.1, 2.0)
            waiting_time = np.random.uniform(0.01, 0.5)
            memory_usage = np.random.uniform(100, 500)
            
            monitor.record_batch(batch_size, processing_time, waiting_time, memory_usage)
            logger.info(f"记录批次 {i+1}: 大小={batch_size}, 处理时间={processing_time:.2f}s, 内存={memory_usage:.2f}MB")
            time.sleep(0.1)
        
        # 获取性能指标
        metrics = monitor.get_metrics()
        logger.info("\n性能指标:")
        logger.info(f"  总任务数: {metrics['total_tasks']}")
        logger.info(f"  完成任务数: {metrics['completed_tasks']}")
        logger.info(f"  总处理时间: {metrics['total_processing_time']:.2f}s")
        logger.info(f"  平均处理时间: {metrics['avg_processing_time']:.2f}s")
        logger.info(f"  总体吞吐率: {metrics['overall_throughput']:.2f} 任务/秒")
        logger.info(f"  峰值内存: {metrics['peak_memory']:.2f}MB")
        
        logger.info("吞吐监测器测试完成")
        return True
    
    def test_end_to_end_performance(self):
        """测试端到端性能"""
        logger.info("=== 测试端到端性能 ===")
        
        # 重置性能指标
        MissionOCR.resetPerformanceMetrics()
        
        # 准备测试任务
        test_tasks = [{'path': path} for path in self.test_image_paths[:8]]  # 使用前8张图片
        
        logger.info(f"开始测试 {len(test_tasks)} 个任务")
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行OCR任务
        results = MissionOCR.addMissionWait({}, test_tasks)
        
        # 记录结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计结果
        successful_tasks = sum(1 for res in results if res.get('result', {}).get('code') == 100)
        
        logger.info(f"\n测试完成:")
        logger.info(f"  总任务数: {len(test_tasks)}")
        logger.info(f"  成功任务数: {successful_tasks}")
        logger.info(f"  总耗时: {total_time:.2f}s")
        logger.info(f"  平均耗时: {total_time / len(test_tasks):.2f}s/任务")
        logger.info(f"  吞吐率: {len(test_tasks) / total_time:.2f} 任务/秒")
        
        # 获取性能指标
        metrics = MissionOCR.getPerformanceMetrics()
        logger.info("\n详细性能指标:")
        logger.info(f"  平均处理时间: {metrics['avg_processing_time']:.2f}s")
        logger.info(f"  平均等待时间: {metrics['avg_waiting_time']:.2f}s")
        logger.info(f"  峰值内存: {metrics['peak_memory']:.2f}MB")
        
        # 获取内存池状态
        memory_pool_status = MissionOCR.getMemoryPoolStatus()
        logger.info("\n内存池状态:")
        logger.info(f"  空闲buffer: {memory_pool_status['free_buffers']}")
        logger.info(f"  使用中buffer: {memory_pool_status['used_buffers']}")
        logger.info(f"  最大buffer数: {memory_pool_status['max_buffers']}")
        
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("="*50)
        logger.info("开始OCR优化模块测试")
        logger.info("="*50)
        
        tests = [
            ("输入切片编排器", self.test_input_slicer),
            ("内存池", self.test_memory_pool),
            ("任务调度器", self.test_task_scheduler),
            ("吞吐监测器", self.test_throughput_monitor),
            ("端到端性能", self.test_end_to_end_performance),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info("\n" + "="*50)
                if test_func():
                    logger.info(f"✅ {test_name} 测试通过")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name} 测试失败")
                    failed += 1
            except Exception as e:
                logger.error(f"❌ {test_name} 测试异常: {e}")
                failed += 1
        
        logger.info("\n" + "="*50)
        logger.info(f"测试完成: 通过 {passed} 个, 失败 {failed} 个")
        logger.info("="*50)
        
        return passed == len(tests)
    
    def cleanup(self):
        """清理测试资源"""
        import shutil
        if os.path.exists(self.test_images_dir):
            shutil.rmtree(self.test_images_dir)
            logger.info(f"清理测试图片目录: {self.test_images_dir}")


if __name__ == "__main__":
    # 配置日志
    logger.setLevel(logger.INFO)
    
    test = OCROptimizationTest()
    
    try:
        success = test.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        test.cleanup()
