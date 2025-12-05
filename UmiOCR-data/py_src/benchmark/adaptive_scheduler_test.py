# ===============================================
# =============== 自适应调度器回归测试 ===============
# ===============================================

import time
import threading
import random
from umi_log import logger
from ..scheduler.adaptive_inference_scheduler import AdaptiveInferenceSchedulerInstance, InferenceBackend
from ..monitoring.gpu_monitor import GPUMonitorInstance


class MockOCRAPI:
    """模拟OCR API，用于测试"""

    def __init__(self):
        self.backend = "CPU"
        self.config = {}
        self._lock = threading.Lock()

    def switch_backend(self, backend, config):
        """切换后端"""
        with self._lock:
            self.backend = backend
            self.config = config
            logger.info(f"模拟OCR API已切换到{backend}模式，配置: {config}")
            time.sleep(1)  # 模拟切换延迟

    def update_cpu_config(self, config):
        """更新CPU配置"""
        with self._lock:
            self.config.update(config)
            logger.info(f"模拟OCR API已更新CPU配置: {config}")

    def run_ocr(self, image_data):
        """模拟OCR处理"""
        with self._lock:
            # 模拟处理时间，GPU模式更快
            processing_time = 0.1 if self.backend == "GPU" else 0.3
            time.sleep(processing_time)

            # 生成模拟结果
            result = {
                "code": 100,
                "data": [
                    {
                        "text": f"测试文本 {random.randint(1, 1000)}",
                        "score": 0.95,
                        "box": [[10, 10], [100, 10], [100, 30], [10, 30]]
                    }
                ],
                "backend": self.backend,
                "processing_time": processing_time
            }

            return result


class AdaptiveSchedulerTester:
    """自适应调度器测试器"""

    def __init__(self):
        self.mock_ocr = MockOCRAPI()
        self.test_results = []
        self._test_running = False
        self._lock = threading.Lock()

        # 注册回调
        AdaptiveInferenceSchedulerInstance.on_backend_switch = self._on_backend_switch
        AdaptiveInferenceSchedulerInstance.on_status_update = self._on_status_update

    def _on_backend_switch(self, backend, reason):
        """后端切换回调"""
        logger.info(f"[测试] 后端切换: {backend.value}，原因: {reason}")
        with self._lock:
            self.test_results.append({
                "type": "backend_switch",
                "timestamp": time.time(),
                "backend": backend.value,
                "reason": reason
            })

    def _on_status_update(self, status):
        """状态更新回调"""
        logger.info(f"[测试] 状态更新: {status}")

    def _simulate_ocr_tasks(self, duration):
        """模拟OCR任务流"""
        end_time = time.time() + duration
        task_count = 0
        successful_tasks = 0

        while time.time() < end_time and self._test_running:
            try:
                # 模拟OCR任务
                result = self.mock_ocr.run_ocr(f"image_{task_count}")
                successful_tasks += 1

                with self._lock:
                    self.test_results.append({
                        "type": "ocr_task",
                        "timestamp": time.time(),
                        "task_id": task_count,
                        "backend": result["backend"],
                        "processing_time": result["processing_time"],
                        "success": True
                    })

                task_count += 1
                time.sleep(0.5)  # 任务间隔

            except Exception as e:
                logger.error(f"[测试] OCR任务失败: {e}")
                with self._lock:
                    self.test_results.append({
                        "type": "ocr_task",
                        "timestamp": time.time(),
                        "task_id": task_count,
                        "backend": self.mock_ocr.backend,
                        "processing_time": 0,
                        "success": False,
                        "error": str(e)
                    })
                task_count += 1

        logger.info(f"[测试] OCR任务模拟完成，总任务数: {task_count}，成功数: {successful_tasks}")

    def _simulate_gpu_exception(self, delay=5):
        """模拟GPU异常"""
        time.sleep(delay)
        logger.info("[测试] 开始模拟GPU异常...")

        # 模拟GPU驱动错误
        def mock_update_gpu_status():
            GPUMonitorInstance.utilization = 100
            GPUMonitorInstance.temperature = 100
            GPUMonitorInstance.memory_utilization = 100
            GPUMonitorInstance.driver_error = True

        # 连续更新GPU状态以触发异常检测
        for _ in range(10):
            mock_update_gpu_status()
            GPUMonitorInstance._check_gpu_exception()
            time.sleep(1)

        logger.info("[测试] GPU异常模拟完成")

    def _simulate_gpu_recovery(self, delay=20):
        """模拟GPU恢复"""
        time.sleep(delay)
        logger.info("[测试] 开始模拟GPU恢复...")

        # 恢复GPU状态
        def mock_recover_gpu_status():
            GPUMonitorInstance.utilization = 30
            GPUMonitorInstance.temperature = 60
            GPUMonitorInstance.memory_utilization = 40
            GPUMonitorInstance.driver_error = False
            GPUMonitorInstance._utilization_exceeded_since = None
            GPUMonitorInstance._temperature_exceeded_since = None
            GPUMonitorInstance._memory_exceeded_since = None
            GPUMonitorInstance._driver_error_since = None

        mock_recover_gpu_status()
        GPUMonitorInstance._check_gpu_exception()

        logger.info("[测试] GPU恢复模拟完成")

    def run_full_test(self, test_duration=60):
        """运行完整测试"""
        logger.info("=" * 60)
        logger.info("[测试] 开始自适应调度器回归测试")
        logger.info("=" * 60)

        self._test_running = True
        self.test_results.clear()

        try:
            # 1. 启动自适应调度器
            logger.info("[测试] 步骤1: 启动自适应调度器")
            AdaptiveInferenceSchedulerInstance.start(self.mock_ocr, "test_ocr_api")
            time.sleep(3)

            # 2. 启动OCR任务模拟
            logger.info("[测试] 步骤2: 启动OCR任务模拟")
            ocr_thread = threading.Thread(target=self._simulate_ocr_tasks, args=(test_duration,))
            ocr_thread.start()

            # 3. 模拟GPU异常
            logger.info("[测试] 步骤3: 计划模拟GPU异常")
            gpu_exception_thread = threading.Thread(target=self._simulate_gpu_exception, args=(10,))
            gpu_exception_thread.start()

            # 4. 模拟GPU恢复
            logger.info("[测试] 步骤4: 计划模拟GPU恢复")
            gpu_recovery_thread = threading.Thread(target=self._simulate_gpu_recovery, args=(30,))
            gpu_recovery_thread.start()

            # 5. 等待测试完成
            logger.info("[测试] 步骤5: 等待测试完成")
            ocr_thread.join()
            gpu_exception_thread.join()
            gpu_recovery_thread.join()

            # 6. 停止自适应调度器
            logger.info("[测试] 步骤6: 停止自适应调度器")
            AdaptiveInferenceSchedulerInstance.stop()
            time.sleep(2)

        except Exception as e:
            logger.error(f"[测试] 测试过程中发生错误: {e}")
            self._test_running = False
            AdaptiveInferenceSchedulerInstance.stop()
            raise

        finally:
            self._test_running = False

        # 7. 分析测试结果
        logger.info("[测试] 步骤7: 分析测试结果")
        self._analyze_test_results()

        logger.info("=" * 60)
        logger.info("[测试] 自适应调度器回归测试完成")
        logger.info("=" * 60)

    def _analyze_test_results(self):
        """分析测试结果"""
        logger.info("\n" + "=" * 60)
        logger.info("[测试结果分析]")
        logger.info("=" * 60)

        with self._lock:
            # 统计后端切换次数
            backend_switches = [r for r in self.test_results if r["type"] == "backend_switch"]
            logger.info(f"后端切换次数: {len(backend_switches)}")
            for switch in backend_switches:
                logger.info(f"  {time.strftime('%H:%M:%S', time.localtime(switch['timestamp']))} - {switch['backend']}: {switch['reason']}")

            # 统计OCR任务
            ocr_tasks = [r for r in self.test_results if r["type"] == "ocr_task"]
            successful_tasks = [r for r in ocr_tasks if r["success"]]
            failed_tasks = [r for r in ocr_tasks if not r["success"]]

            logger.info(f"\nOCR任务统计:")
            logger.info(f"  总任务数: {len(ocr_tasks)}")
            logger.info(f"  成功任务数: {len(successful_tasks)} ({len(successful_tasks)/len(ocr_tasks)*100:.2f}%)")
            logger.info(f"  失败任务数: {len(failed_tasks)} ({len(failed_tasks)/len(ocr_tasks)*100:.2f}%)")

            # 按后端统计任务
            if successful_tasks:
                gpu_tasks = [r for r in successful_tasks if r["backend"] == "GPU"]
                cpu_tasks = [r for r in successful_tasks if r["backend"] == "CPU"]

                logger.info(f"\n按后端统计成功任务:")
                logger.info(f"  GPU模式任务数: {len(gpu_tasks)}")
                if gpu_tasks:
                    avg_gpu_time = sum(r["processing_time"] for r in gpu_tasks) / len(gpu_tasks)
                    logger.info(f"  GPU模式平均处理时间: {avg_gpu_time:.3f}秒")

                logger.info(f"  CPU模式任务数: {len(cpu_tasks)}")
                if cpu_tasks:
                    avg_cpu_time = sum(r["processing_time"] for r in cpu_tasks) / len(cpu_tasks)
                    logger.info(f"  CPU模式平均处理时间: {avg_cpu_time:.3f}秒")

                # 检查任务连续性
                logger.info(f"\n任务连续性检查:")
                task_ids = [r["task_id"] for r in ocr_tasks]
                if task_ids == list(range(len(task_ids))):
                    logger.info("  ✅ 任务ID连续，无任务丢失")
                else:
                    logger.error("  ❌ 任务ID不连续，存在任务丢失")

                # 检查切换期间任务是否成功
                if backend_switches:
                    logger.info(f"\n切换期间任务检查:")
                    for switch in backend_switches:
                        switch_time = switch["timestamp"]
                        # 检查切换前后10秒内的任务
                        tasks_around_switch = [
                            r for r in ocr_tasks
                            if abs(r["timestamp"] - switch_time) <= 10
                        ]
                        successful_around_switch = [r for r in tasks_around_switch if r["success"]]

                        if tasks_around_switch:
                            success_rate = len(successful_around_switch) / len(tasks_around_switch) * 100
                            logger.info(f"  {switch['backend']}切换前后10秒内: {len(tasks_around_switch)}个任务，成功率: {success_rate:.2f}%")
                            if success_rate == 100:
                                logger.info("    ✅ 切换期间任务全部成功")
                            else:
                                logger.error("    ❌ 切换期间存在任务失败")

            # 检查是否满足要求
            logger.info(f"\n测试要求验证:")
            
            # 1. 任务不中断
            if len(failed_tasks) == 0:
                logger.info("  ✅ 所有任务成功完成，无中断")
            else:
                logger.error("  ❌ 存在任务失败")

            # 2. 结果一致（模拟任务无法验证实际结果一致性，这里只验证任务成功）
            if len(successful_tasks) > 0:
                logger.info("  ✅ 任务成功执行，结果生成正常")
            else:
                logger.error("  ❌ 无成功任务")

            # 3. 自动切换功能
            if len(backend_switches) >= 2:  # 至少切换两次（GPU→CPU→GPU）
                logger.info("  ✅ 自动切换功能正常工作")
            else:
                logger.warning("  ⚠️ 自动切换次数不足")

        logger.info("=" * 60)

    def generate_test_report(self, filename="adaptive_scheduler_test_report.json"):
        """生成测试报告"""
        import json

        report = {
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_duration": 60,  # 测试持续时间
            "results": self.test_results
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"测试报告已生成: {filename}")


if __name__ == "__main__":
    # 运行测试
    tester = AdaptiveSchedulerTester()
    tester.run_full_test(test_duration=60)
    tester.generate_test_report()