#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# =============== 性能测试脚本 ===================
# ===============================================

import os
import time
import random
import cv2
import numpy as np
from typing import List, Dict, Any

# 添加项目路径
project_path = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(project_path, "UmiOCR-data")
py_src_path = os.path.join(data_path, "py_src")

import sys
sys.path.insert(0, py_src_path)

# 导入优化模块
from ocr.api.slice_orchestrator import SliceOrchestratorGlobal
from utils.memory_pool import MemoryPoolGlobal
from scheduler.optimized_scheduler import OptimizedTaskSchedulerGlobal
from monitor.throughput_monitor import ThroughputMonitorGlobal

# 导入OCR模块
from mission.mission_ocr import MissionOCR
from ocr.api import getApiOcr, getLocalOptions


class PerformanceTest:
    """性能测试类"""
    
    def __init__(self):
        self._test_images: List[np.ndarray] = []
        self._test_results: Dict[str, Any] = {}
        
        # 初始化OCR引擎
        self._init_ocr_engine()
    
    def _init_ocr_engine(self):
        """初始化OCR引擎"""
        # 获取可用的OCR引擎
        from plugins_controller import PluginsController
        
        plugins_controller = PluginsController()
        ocr_plugins = plugins_controller.getPlugins("ocr")
        
        if not ocr_plugins:
            raise Exception("没有找到OCR引擎插件")
        
        # 选择第一个可用的OCR引擎
        ocr_plugin = ocr_plugins[0]
        api_key = ocr_plugin['key']
        
        # 获取OCR引擎的默认配置
        local_options = getLocalOptions(api_key)
        
        # 设置OCR引擎
        result = MissionOCR.setApi(api_key, local_options)
        if not result.startswith("[Success]"):
            raise Exception(f"设置OCR引擎失败: {result}")
        
        print(f"OCR引擎初始化成功: {api_key}")
    
    def generate_test_images(self, count: int = 500):
        """
        生成测试图像
        
        Args:
            count: 测试图像数量
        """
        print(f"生成 {count} 张测试图像...")
        
        self._test_images.clear()
        
        for i in range(count):
            # 随机生成图像分辨率
            # 小图: 640x480 到 1280x720
            # 中图: 1920x1080 到 2560x1440
            # 大图: 3840x2160 到 7680x4320
            
            image_type = random.choice(["small", "medium", "large"])
            
            if image_type == "small":
                width = random.randint(640, 1280)
                height = random.randint(480, 720)
            elif image_type == "medium":
                width = random.randint(1920, 2560)
                height = random.randint(1080, 1440)
            else:  # large
                width = random.randint(3840, 7680)
                height = random.randint(2160, 4320)
            
            # 生成随机图像
            image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            
            # 添加一些随机文本（模拟真实场景）
            if random.random() > 0.5:
                # 在图像上添加随机文本
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = random.uniform(0.5, 2.0)
                font_thickness = random.randint(1, 4)
                
                # 生成随机文本
                text = f"Test Image {i+1}"
                
                # 计算文本大小
                text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
                
                # 随机选择文本位置
                x = random.randint(0, width - text_size[0])
                y = random.randint(text_size[1], height)
                
                # 随机选择文本颜色
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                
                # 添加文本到图像
                cv2.putText(image, text, (x, y), font, font_scale, color, font_thickness)
            
            self._test_images.append(image)
        
        print(f"测试图像生成完成: {len(self._test_images)} 张")
    
    def run_optimized_test(self) -> Dict[str, Any]:
        """
        运行优化后的性能测试
        
        Returns:
            测试结果字典
        """
        print("\n" + "="*50)
        print("运行优化后的性能测试...")
        print("="*50)
        
        # 清空之前的监测数据
        ThroughputMonitorGlobal.clear_monitor_data()
        
        # 开始时间
        start_time = time.time()
        
        # 执行OCR任务
        results = []
        
        def _onStart(msnInfo):
            print(f"任务队列开始: {msnInfo['msnID']}")
        
        def _onReady(msnInfo, msn):
            pass
        
        def _onGet(msnInfo, msn, res):
            results.append(res)
            print(f"任务完成: {len(results)}/{len(self._test_images)}")
        
        def _onEnd(msnInfo, msg):
            print(f"任务队列结束: {msnInfo['msnID']}, 消息: {msg}")
        
        # 准备任务列表
        msnList = []
        for i, image in enumerate(self._test_images):
            # 将图像转换为bytes
            _, image_bytes = cv2.imencode(".jpg", image)
            msnList.append({"bytes": image_bytes.tobytes()})
        
        # 添加任务队列
        msnInfo = {
            "onStart": _onStart,
            "onReady": _onReady,
            "onGet": _onGet,
            "onEnd": _onEnd,
            "argd": {},
        }
        
        msnID = MissionOCR.addMissionList(msnInfo, msnList)
        if msnID.startswith("[Error]"):
            raise Exception(f"添加任务队列失败: {msnID}")
        
        # 等待任务完成
        while True:
            time.sleep(1)
            mission_lengths = MissionOCR.getMissionListsLength()
            if msnID not in mission_lengths or mission_lengths[msnID] == 0:
                break
        
        # 结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        # 获取监测数据
        monitor_data = ThroughputMonitorGlobal.get_monitor_data()
        peak_resources = ThroughputMonitorGlobal.get_peak_resources()
        
        # 计算平均处理时间
        if monitor_data:
            avg_processing_time = sum(data['total_processing_time'] for data in monitor_data) / len(monitor_data)
        else:
            avg_processing_time = 0.0
        
        # 计算吞吐量
        throughput = len(results) / total_time  # 张/秒
        
        # 统计结果
        success_count = 0
        error_count = 0
        
        for res in results:
            if res.get('code') == 100:
                success_count += 1
            else:
                error_count += 1
        
        test_results = {
            "test_type": "optimized",
            "total_images": len(self._test_images),
            "total_time": total_time,
            "avg_processing_time": avg_processing_time,
            "throughput": throughput,
            "success_count": success_count,
            "error_count": error_count,
            "peak_memory": peak_resources['memory_peak'],
            "peak_cpu": peak_resources['cpu_peak'],
        }
        
        self._test_results['optimized'] = test_results
        
        # 打印测试结果
        self._print_test_results(test_results)
        
        return test_results
    
    def run_baseline_test(self) -> Dict[str, Any]:
        """
        运行基线性能测试（未优化）
        
        Returns:
            测试结果字典
        """
        print("\n" + "="*50)
        print("运行基线性能测试（未优化）...")
        print("="*50)
        
        # 开始时间
        start_time = time.time()
        
        # 执行OCR任务
        results = []
        
        def _onStart(msnInfo):
            print(f"任务队列开始: {msnInfo['msnID']}")
        
        def _onReady(msnInfo, msn):
            pass
        
        def _onGet(msnInfo, msn, res):
            results.append(res)
            print(f"任务完成: {len(results)}/{len(self._test_images)}")
        
        def _onEnd(msnInfo, msg):
            print(f"任务队列结束: {msnInfo['msnID']}, 消息: {msg}")
        
        # 准备任务列表
        msnList = []
        for i, image in enumerate(self._test_images):
            # 将图像转换为bytes
            _, image_bytes = cv2.imencode(".jpg", image)
            msnList.append({"bytes": image_bytes.tobytes()})
        
        # 添加任务队列
        msnInfo = {
            "onStart": _onStart,
            "onReady": _onReady,
            "onGet": _onGet,
            "onEnd": _onEnd,
            "argd": {},
        }
        
        # 保存原始的msnTask方法
        original_msn_task = MissionOCR._msnTask
        
        try:
            # 临时替换为未优化的msnTask方法
            def unoptimized_msn_task(msnInfo, msn):
                if "path" in msn:
                    res = MissionOCR._api.runPath(msn["path"])
                    res["path"] = msn["path"]
                elif "bytes" in msn:
                    res = MissionOCR._api.runBytes(msn["bytes"])
                elif "base64" in msn:
                    res = MissionOCR._api.runBase64(msn["base64"])
                else:
                    res = {
                        "code": 901,
                        "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
                    }
                
                if res["code"] == 100:
                    # 计算平均置信度
                    score, num = 0, 0
                    for r in res["data"]:
                        score += r["score"]
                        num += 1
                    if num > 0:
                        score /= num
                    res["score"] = score
                    
                    # 执行 tbpu
                    if msnInfo["tbpu"]:
                        for tbpu in msnInfo["tbpu"]:
                            res["data"] = tbpu.run(res["data"])
                            if not res["data"]:
                                res["code"] = 101
                                res["data"] = ""
                                break
                
                return res
            
            MissionOCR._msnTask = unoptimized_msn_task
            
            # 添加任务队列
            msnID = MissionOCR.addMissionList(msnInfo, msnList)
            if msnID.startswith("[Error]"):
                raise Exception(f"添加任务队列失败: {msnID}")
            
            # 等待任务完成
            while True:
                time.sleep(1)
                mission_lengths = MissionOCR.getMissionListsLength()
                if msnID not in mission_lengths or mission_lengths[msnID] == 0:
                    break
        
        finally:
            # 恢复原始的msnTask方法
            MissionOCR._msnTask = original_msn_task
        
        # 结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        # 计算平均处理时间
        avg_processing_time = total_time / len(self._test_images)
        
        # 计算吞吐量
        throughput = len(results) / total_time  # 张/秒
        
        # 统计结果
        success_count = 0
        error_count = 0
        
        for res in results:
            if res.get('code') == 100:
                success_count += 1
            else:
                error_count += 1
        
        # 获取资源使用情况
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage = memory_info.rss / (1024 * 1024 * 1024)  # 转换为GB
        cpu_usage = process.cpu_percent(interval=1) / psutil.cpu_count()  # 平均到每个CPU核心
        
        test_results = {
            "test_type": "baseline",
            "total_images": len(self._test_images),
            "total_time": total_time,
            "avg_processing_time": avg_processing_time,
            "throughput": throughput,
            "success_count": success_count,
            "error_count": error_count,
            "peak_memory": memory_usage,
            "peak_cpu": cpu_usage,
        }
        
        self._test_results['baseline'] = test_results
        
        # 打印测试结果
        self._print_test_results(test_results)
        
        return test_results
    
    def _print_test_results(self, test_results: Dict[str, Any]):
        """
        打印测试结果
        
        Args:
            test_results: 测试结果字典
        """
        print(f"\n测试类型: {test_results['test_type']}")
        print(f"总图像数量: {test_results['total_images']}")
        print(f"总处理时间: {test_results['total_time']:.2f} 秒")
        print(f"平均处理时间: {test_results['avg_processing_time']:.2f} 秒/张")
        print(f"吞吐量: {test_results['throughput']:.2f} 张/秒")
        print(f"成功数量: {test_results['success_count']}")
        print(f"错误数量: {test_results['error_count']}")
        print(f"峰值内存: {test_results['peak_memory']:.2f} GB")
        print(f"峰值CPU: {test_results['peak_cpu']:.2f}%")
    
    def compare_results(self):
        """
        比较优化前后的测试结果
        """
        print("\n" + "="*50)
        print("比较优化前后的测试结果")
        print("="*50)
        
        if 'baseline' not in self._test_results or 'optimized' not in self._test_results:
            print("请先运行基线测试和优化测试")
            return
        
        baseline = self._test_results['baseline']
        optimized = self._test_results['optimized']
        
        # 计算优化比例
        time_reduction = (baseline['total_time'] - optimized['total_time']) / baseline['total_time'] * 100
        throughput_increase = (optimized['throughput'] - baseline['throughput']) / baseline['throughput'] * 100
        memory_change = (optimized['peak_memory'] - baseline['peak_memory']) / baseline['peak_memory'] * 100
        
        print(f"总处理时间减少: {time_reduction:.2f}%")
        print(f"吞吐量提升: {throughput_increase:.2f}%")
        print(f"峰值内存变化: {memory_change:.2f}%")
        
        # 验证验收标准
        print(f"\n验收标准验证:")
        
        # 1. 整体耗时 ≤ 当前基准的 70%
        time_threshold = baseline['total_time'] * 0.7
        time_pass = optimized['total_time'] ≤ time_threshold
        print(f"1. 整体耗时 ≤ 当前基准的 70%: {'通过' if time_pass else '未通过'}")
        print(f"   基准时间: {baseline['total_time']:.2f} 秒")
        print(f"   优化时间: {optimized['total_time']:.2f} 秒")
        print(f"   阈值: {time_threshold:.2f} 秒")
        
        # 2. 峰值内存上涨不超过 5%
        memory_threshold = 5.0
        memory_pass = memory_change ≤ memory_threshold
        print(f"2. 峰值内存上涨不超过 5%: {'通过' if memory_pass else '未通过'}")
        print(f"   基准内存: {baseline['peak_memory']:.2f} GB")
        print(f"   优化内存: {optimized['peak_memory']:.2f} GB")
        print(f"   内存变化: {memory_change:.2f}%")
        print(f"   阈值: {memory_threshold:.2f}%")
        
        # 总验收结果
        overall_pass = time_pass and memory_pass
        print(f"\n总验收结果: {'通过' if overall_pass else '未通过'}")


if __name__ == "__main__":
    # 创建性能测试实例
    performance_test = PerformanceTest()
    
    # 生成测试图像
    performance_test.generate_test_images(count=500)
    
    # 运行基线测试
    performance_test.run_baseline_test()
    
    # 运行优化测试
    performance_test.run_optimized_test()
    
    # 比较测试结果
    performance_test.compare_results()
