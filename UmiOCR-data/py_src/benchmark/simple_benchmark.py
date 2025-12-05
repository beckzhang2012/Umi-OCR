import os
import sys
import time
import random
import threading
import argparse
import json
from typing import List, Dict, Any
from PIL import Image, ImageDraw

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 先设置环境变量确保能找到模块
os.environ['PYTHONPATH'] = project_root + os.pathsep + os.environ.get('PYTHONPATH', '')

# 导入模块
from imports.umi_log import logger
from monitoring import get_performance_monitor, MetricType

# 模拟OCR处理函数
def mock_ocr_process(image: Image.Image, task_id: str) -> Dict[str, Any]:
    """模拟OCR处理过程"""
    start_time = time.time()
    
    # 模拟处理时间（随机0.1-0.5秒）
    processing_time = random.uniform(0.1, 0.5)
    time.sleep(processing_time)
    
    # 模拟OCR结果
    result = {
        'task_id': task_id,
        'text': f'Sample text from image {task_id}',
        'confidence': random.uniform(0.8, 0.95),
        'processing_time': processing_time,
        'success': True
    }
    
    return result

# 生成测试图片
def generate_test_image(image_id: int, width: int = 800, height: int = 600) -> Image.Image:
    """生成测试用的随机图片"""
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # 添加一些随机线条和文字
    for i in range(10):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    
    return image

# 单线程测试
def run_single_thread_test(image_count: int) -> Dict[str, Any]:
    """运行单线程测试"""
    logger.info(f"Running single-thread test with {image_count} images...")
    
    monitor = get_performance_monitor()
    batch_id = monitor.start_batch(image_count)
    
    start_time = time.time()
    
    for i in range(image_count):
        task_id = f"task_{i}"
        image = generate_test_image(i)
        
        # 记录开始时间
        task_start = time.time()
        
        # 处理图片
        result = mock_ocr_process(image, task_id)
        
        # 记录结束时间
        task_end = time.time()
        
        # 记录性能指标
        monitor.record_task_metric(
            task_id=task_id,
            metric_type=MetricType.PROCESSING_TIME,
            value=result['processing_time'],
            unit="秒"
        )
        
        if i % 50 == 0:
            logger.info(f"Processed {i}/{image_count} images...")
    
    total_time = time.time() - start_time
    monitor.end_batch(batch_id)
    
    # 获取性能指标
    metrics = monitor.get_batch_metrics(batch_id)
    
    # 计算平均、最大、最小处理时间
    processing_times = [m.value for m in metrics if m.metric_type == MetricType.PROCESSING_TIME]
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    max_processing_time = max(processing_times) if processing_times else 0
    min_processing_time = min(processing_times) if processing_times else 0
    
    logger.info(f"Single-thread test completed in {total_time:.2f} seconds")
    logger.info(f"Average processing time: {avg_processing_time:.4f} seconds")
    logger.info(f"Max processing time: {max_processing_time:.4f} seconds")
    logger.info(f"Min processing time: {min_processing_time:.4f} seconds")
    
    return {
        'test_type': 'single_thread',
        'image_count': image_count,
        'total_time': total_time,
        'avg_processing_time': avg_processing_time,
        'max_processing_time': max_processing_time,
        'min_processing_time': min_processing_time
    }

# 多线程测试
def run_multi_thread_test(image_count: int, max_concurrent: int = 4) -> Dict[str, Any]:
    """运行多线程测试"""
    logger.info(f"Running multi-thread test with {image_count} images and {max_concurrent} threads...")
    
    monitor = get_performance_monitor()
    batch_id = monitor.start_batch(image_count)
    
    start_time = time.time()
    
    # 任务队列
    tasks = []
    
    # 处理函数
    def process_image(i: int):
        task_id = f"task_{i}"
        image = generate_test_image(i)
        
        # 记录开始时间
        task_start = time.time()
        
        # 处理图片
        result = mock_ocr_process(image, task_id)
        
        # 记录结束时间
        task_end = time.time()
        
        # 记录性能指标
        monitor.record_task_metric(
            task_id=task_id,
            metric_type=MetricType.PROCESSING_TIME,
            value=result['processing_time'],
            unit="秒"
        )
        
        if i % 50 == 0:
            logger.info(f"Processed {i}/{image_count} images...")
    
    # 创建线程池
    threads = []
    for i in range(image_count):
        thread = threading.Thread(target=process_image, args=(i,))
        threads.append(thread)
        thread.start()
        
        # 控制并发数
        while len(threads) >= max_concurrent:
            for t in threads:
                if not t.is_alive():
                    threads.remove(t)
            time.sleep(0.01)
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    monitor.end_batch(batch_id)
    
    # 获取性能摘要
    batch_metrics = monitor.get_batch_metrics(batch_id)
    
    # 计算处理时间指标
    if batch_metrics:
        processing_times = [m.value for m in batch_metrics if m.metric_type == MetricType.PROCESSING_TIME]
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            min_processing_time = min(processing_times)
        else:
            avg_processing_time = 0
            max_processing_time = 0
            min_processing_time = 0
    else:
        avg_processing_time = 0
        max_processing_time = 0
        min_processing_time = 0
    
    logger.info(f"Multi-thread test completed in {total_time:.2f} seconds")
    logger.info(f"Average processing time: {avg_processing_time:.4f} seconds")
    logger.info(f"Max processing time: {max_processing_time:.4f} seconds")
    logger.info(f"Min processing time: {min_processing_time:.4f} seconds")
    
    return {
        'test_type': 'multi_thread',
        'image_count': image_count,
        'max_concurrent': max_concurrent,
        'total_time': total_time,
        'summary': {
            'avg_processing_time': avg_processing_time,
            'max_processing_time': max_processing_time,
            'min_processing_time': min_processing_time
        }
    }

# 主函数
def main():
    parser = argparse.ArgumentParser(description='Performance benchmark for OCR optimization')
    parser.add_argument('--image-count', type=int, default=500, help='Number of test images')
    parser.add_argument('--max-concurrent', type=int, default=6, help='Maximum concurrent threads')
    parser.add_argument('--output', type=str, default='benchmark_results.json', help='Output file path')
    
    args = parser.parse_args()
    
    logger.info("Starting performance benchmark...")
    logger.info(f"Image count: {args.image_count}")
    logger.info(f"Max concurrent threads: {args.max_concurrent}")
    
    # 运行单线程测试
    single_thread_result = run_single_thread_test(args.image_count)
    
    # 运行多线程测试
    multi_thread_result = run_multi_thread_test(args.image_count, args.max_concurrent)
    
    # 比较结果
    speedup = single_thread_result['total_time'] / multi_thread_result['total_time']
    
    logger.info("\n=== Benchmark Results ===")
    logger.info(f"Single-thread time: {single_thread_result['total_time']:.2f} seconds")
    logger.info(f"Multi-thread time: {multi_thread_result['total_time']:.2f} seconds")
    logger.info(f"Speedup: {speedup:.2f}x")
    
    # 保存结果
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'image_count': args.image_count,
        'max_concurrent': args.max_concurrent,
        'single_thread': single_thread_result,
        'multi_thread': multi_thread_result,
        'speedup': speedup
    }
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {args.output}")
    logger.info("Benchmark completed successfully!")

if __name__ == "__main__":
    main()