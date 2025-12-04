#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 批量模式压力测试脚本
模拟长时间运行的批量OCR任务，测试稳定性和崩溃恢复能力
"""

import os
import sys
import time
import random
import threading
import logging
import queue
import site
from datetime import datetime

# 初始化运行环境
def initRuntimeEnvironment():
    """初始化运行环境"""
    # 初始化工作目录和Python搜索路径
    script = os.path.abspath(__file__)  # 启动脚本.py的路径
    umi_ocr_root_path = os.path.dirname(script)  # Umi-OCR根目录
    cwd = os.path.join(umi_ocr_root_path, 'UmiOCR-data')  # 工作目录
    os.chdir(cwd)  # 重新设定工作目录（在 UmiOCR-data 文件夹下）
    for n in ['.', 'site-packages', 'py_src', os.path.join('py_src', 'imports')]:  # 将模块目录添加到 Python 搜索路径中
        path = os.path.abspath(os.path.join(cwd, n))
        if os.path.exists(path):
            site.addsitedir(path)

if __name__ == "__main__":
    try:
        initRuntimeEnvironment()  # 初始化运行环境
    except Exception as e:
        print(f"初始化运行环境失败: {e}")
        sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5s %(name)-15s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'stress_test_batch_ocr.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 导入Umi-OCR模块
try:
    from py_src.mission.mission_ocr import MissionOCR
    from py_src.ocr.api import getApiOcr, getLocalOptions
    from py_src.imports.umi_log import logger
    from py_src.plugins_controller.plugins_controller import PluginsController
    logger.setLevel(logging.DEBUG)
    
    # 设置所有Umi-OCR模块的日志级别为DEBUG
    for name in logging.root.manager.loggerDict:
        if name.startswith('py_src') or name.startswith('plugins'):
            logging.getLogger(name).setLevel(logging.DEBUG)
    
    # 初始化插件控制器
    logger.info("正在初始化插件控制器...")
    plugins_result = PluginsController.init()
    logger.info(f"插件控制器初始化结果: {plugins_result}")
except ImportError as e:
    print(f"导入Umi-OCR模块失败: {e}")
    print("请确保脚本位于Umi-OCR根目录下")
    sys.exit(1)

# 测试配置
TEST_DURATION = 7200  # 测试持续时间（秒），2小时
TEST_INTERVAL = 0.1   # 任务间隔时间（秒）
MAX_CONCURRENT_TASKS = 5  # 最大并发任务数
TASK_TIMEOUT = 30  # 单个任务超时时间（秒）

# 测试图片路径（使用项目中的示例图片或创建临时图片）
TEST_IMAGE_PATH = None

# 查找测试图片
def find_test_image():
    """查找项目中的测试图片"""
    # 检查常见图片目录
    test_dirs = [
        os.path.join(os.path.dirname(__file__), "test_images"),
        os.path.join(os.path.dirname(__file__), "docs", "images"),
        os.path.join(os.path.dirname(__file__), "UmiOCR-data", "qt_res", "images"),
    ]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for root, _, files in os.walk(test_dir):
                for file in files:
                    if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")):
                        return os.path.join(root, file)
    
    return None

# 创建临时测试图片
def create_temp_test_image():
    """创建临时测试图片"""
    from PIL import Image, ImageDraw, ImageFont
    
    temp_image_path = os.path.join(os.path.dirname(__file__), "temp_test_image.png")
    
    # 创建一个简单的测试图片
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # 添加一些文本
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    d.text((10, 10), "Umi-OCR 压力测试", font=font, fill=(0, 0, 0))
    d.text((10, 40), f"测试时间: {datetime.now()}", font=font, fill=(0, 0, 0))
    d.text((10, 70), "这是一张用于压力测试的临时图片。", font=font, fill=(0, 0, 0))
    d.text((10, 100), "BatchOCR 压力测试脚本正在运行...", font=font, fill=(0, 0, 0))
    
    # 保存图片
    img.save(temp_image_path)
    return temp_image_path

# 初始化OCR引擎
def init_ocr_engine():
    """初始化OCR引擎"""
    logger.info("正在初始化OCR引擎...")
    
    # 获取可用的OCR引擎
    try:
        # 获取可用的OCR引擎列表
        from py_src.ocr.api import ApiDict
        logger.info("可用的OCR引擎: %s", list(ApiDict.keys()))
        
        # 使用第一个可用的引擎
        if not ApiDict:
            logger.error("没有可用的OCR引擎")
            return False
            
        api_key = list(ApiDict.keys())[0]
        local_options = getLocalOptions(api_key)
        
        # 使用默认配置
        info = {"numThread": 1}
        for key, value in local_options.items():
            if "default" in value:
                info[key] = value["default"]
        
        # 设置OCR引擎
        result = MissionOCR.setApi(api_key, info)
        
        if result.startswith("[Success]"):
            logger.info(f"OCR引擎初始化成功: {api_key}")
            return True
        else:
            logger.error(f"OCR引擎初始化失败: {result}")
            return False
    except Exception as e:
        logger.error(f"OCR引擎初始化异常: {str(e)}", exc_info=True)
        return False

# 执行OCR任务

def run_ocr_task(task_id, image_path):
    """执行OCR任务"""
    try:
        start_time = time.time()
        logger.debug(f"任务 {task_id} 开始执行")
        
        # 任务完成标志
        task_completed = False
        task_success = False
        
        # 任务配置
        argd = {
            "mission.dirType": "source",
            "mission.ignoreBlank": True,
            "tbpu.parser": "默认段落合并",
            "language": "简体中文",
            "angle": False,
            "maxSideLen": 1024,
            "numThread": 4,
        }
        
        # 任务回调
        def on_start(msn_info):
            logger.debug(f"任务队列 {msn_info['msnID']} 开始")
            
        def on_ready(msn_info, msn):
            logger.debug(f"任务 {msn_info['msnID']} - {msn['path']} 准备开始")
            
        def on_get(msn_info, msn, res):
            nonlocal task_success
            logger.debug(f"任务 {msn_info['msnID']} - {msn['path']} 完成，耗时: {res.get('time', 0):.2f}秒")
            
            # 检查OCR结果
            if res and res.get('code') == 0:
                text = res.get('text', '')
                if text.strip():
                    task_success = True
                    logger.debug(f"任务 {msn_info['msnID']} - OCR识别成功，识别文本长度: {len(text)}")
                else:
                    task_success = False
                    logger.warning(f"任务 {msn_info['msnID']} - OCR识别成功但结果为空")
            else:
                task_success = False
                logger.error(f"任务 {msn_info['msnID']} - OCR识别失败，错误码: {res.get('code', -1)}")
            
        def on_end(msn_info, msg):
            nonlocal task_completed
            logger.debug(f"任务队列 {msn_info['msnID']} 结束: {msg}")
            task_completed = True
            
        # 创建任务信息
        msn_info = {
            "onStart": on_start,
            "onReady": on_ready,
            "onGet": on_get,
            "onEnd": on_end,
            "argd": argd,
        }
        
        # 添加任务
        msn_list = [{"path": image_path}]
        msn_id = MissionOCR.addMissionList(msn_info, msn_list)
        
        if msn_id.startswith("[Error]"):
            logger.error(f"任务 {task_id} 添加失败: {msn_id}")
            return False
        
        logger.debug(f"任务 {task_id} 添加成功，任务ID: {msn_id}")
        
        # 等待任务完成
        while not task_completed:
            # 超时检查
            if time.time() - start_time > TASK_TIMEOUT:
                logger.error(f"任务 {task_id} 超时")
                # 尝试停止任务
                try:
                    MissionOCR.stopMissionList(msn_id)
                except Exception as e:
                    logger.error(f"任务 {task_id} 停止失败: {str(e)}")
                return False
            
            time.sleep(0.5)
        
        # 任务完成后的结果检查
        if task_success:
            logger.debug(f"任务 {task_id} 执行成功")
            return True
        else:
            logger.error(f"任务 {task_id} 执行失败")
            return False
        
    except Exception as e:
        logger.error(f"任务 {task_id} 执行异常: {str(e)}", exc_info=True)
        return False

# 任务上下文快照
class TaskContextSnapshot:
    """任务上下文快照"""
    def __init__(self, thread_id, task_id, image_path, start_time):
        self.thread_id = thread_id
        self.task_id = task_id
        self.image_path = image_path
        self.start_time = start_time
        self.ocr_status = MissionOCR.getStatus() if hasattr(MissionOCR, 'getStatus') else 'Unknown'
        self.mission_lengths = MissionOCR.getMissionListsLength() if hasattr(MissionOCR, 'getMissionListsLength') else {}
    
    def to_dict(self):
        return {
            'thread_id': self.thread_id,
            'task_id': self.task_id,
            'image_path': self.image_path,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'ocr_status': self.ocr_status,
            'mission_lengths': self.mission_lengths
        }

# 压力测试线程
def stress_test_thread(thread_id, image_path, stop_event, result_queue):
    """压力测试线程"""
    task_count = 0
    success_count = 0
    fail_count = 0
    crash_count = 0
    recovery_count = 0
    last_task_time = time.time()
    last_snapshot = None
    
    logger.info(f"压力测试线程 {thread_id} 启动")
    
    while not stop_event.is_set():
        task_count += 1
        current_time = time.time()
        
        try:
            # 创建任务上下文快照
            snapshot = TaskContextSnapshot(thread_id, task_count, image_path, datetime.now())
            last_snapshot = snapshot
            logger.debug(f"线程 {thread_id} - 任务 {task_count} 上下文快照: {snapshot.to_dict()}")
            
            # 原子校验：检查OCR引擎状态
            if hasattr(MissionOCR, 'getStatus'):
                status = MissionOCR.getStatus()
                if status.get('status') == 'error':
                    logger.error(f"线程 {thread_id} - OCR引擎状态异常: {status}")
                    # 尝试恢复
                    if attempt_recovery(thread_id):
                        recovery_count += 1
                        continue
                    else:
                        fail_count += 1
                        continue
            
            # 执行OCR任务
            success = run_ocr_task(f"{thread_id}-{task_count}", image_path)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # 输出统计信息（每100个任务）
            if task_count % 100 == 0:
                logger.info(f"线程 {thread_id} - 已执行 {task_count} 个任务，成功: {success_count}, 失败: {fail_count}, 崩溃: {crash_count}, 恢复: {recovery_count}")
            
            # 随机等待一段时间，模拟真实使用场景
            time.sleep(random.uniform(TEST_INTERVAL * 0.5, TEST_INTERVAL * 1.5))
            
            last_task_time = current_time
            
        except Exception as e:
            crash_count += 1
            fail_count += 1
            logger.error(f"线程 {thread_id} - 任务 {task_count} 执行异常: {str(e)}", exc_info=True)
            
            # 输出最后一条处理记录与上下文信息
            if last_snapshot:
                logger.error(f"线程 {thread_id} - 最后任务上下文: {last_snapshot.to_dict()}")
            
            # 尝试自动恢复
            if attempt_recovery(thread_id):
                recovery_count += 1
                logger.info(f"线程 {thread_id} - 任务执行已恢复，继续运行")
            else:
                logger.error(f"线程 {thread_id} - 任务执行恢复失败，线程将结束")
                break
            
            # 等待更长时间，避免频繁错误
            time.sleep(random.uniform(1, 3))
    
    # 收集线程结果
    result = {
        "thread_id": thread_id,
        "task_count": task_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "crash_count": crash_count,
        "recovery_count": recovery_count
    }
    
    result_queue.put(result)
    logger.info(f"压力测试线程 {thread_id} 结束 - 总计执行 {task_count} 个任务，成功: {success_count}, 失败: {fail_count}, 崩溃: {crash_count}, 恢复: {recovery_count}")

# 尝试恢复OCR引擎
def attempt_recovery(thread_id):
    """尝试恢复OCR引擎"""
    logger.info(f"线程 {thread_id} - 正在尝试恢复OCR引擎...")
    
    try:
        # 1. 停止所有任务
        if hasattr(MissionOCR, 'stopAllMissions'):
            MissionOCR.stopAllMissions()
            logger.info(f"线程 {thread_id} - 已停止所有任务")
        
        # 2. 等待一段时间
        time.sleep(3)
        
        # 3. 重新初始化OCR引擎
        if init_ocr_engine():
            logger.info(f"线程 {thread_id} - OCR引擎恢复成功")
            return True
        else:
            logger.error(f"线程 {thread_id} - OCR引擎重新初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"线程 {thread_id} - OCR引擎恢复异常: {str(e)}", exc_info=True)
        return False

# 主测试函数
def main():
    """主测试函数"""
    global TEST_IMAGE_PATH
    
    logger.info("=" * 60)
    logger.info("Umi-OCR 批量OCR压力测试")
    logger.info("=" * 60)
    
    # 查找或创建测试图片
    TEST_IMAGE_PATH = find_test_image()
    if not TEST_IMAGE_PATH:
        logger.info("未找到测试图片，正在创建临时测试图片...")
        TEST_IMAGE_PATH = create_temp_test_image()
        
    if not TEST_IMAGE_PATH or not os.path.exists(TEST_IMAGE_PATH):
        logger.error("无法找到或创建测试图片")
        return
    
    logger.info(f"使用测试图片: {TEST_IMAGE_PATH}")
    
    # 初始化OCR引擎
    if not init_ocr_engine():
        logger.error("OCR引擎初始化失败，测试无法继续")
        return
    
    # 启动压力测试线程
    stop_event = threading.Event()
    result_queue = queue.Queue()
    threads = []
    
    logger.info(f"正在启动 {MAX_CONCURRENT_TASKS} 个压力测试线程...")
    
    for i in range(MAX_CONCURRENT_TASKS):
        thread = threading.Thread(
            target=stress_test_thread,
            args=(i + 1, TEST_IMAGE_PATH, stop_event, result_queue)
        )
        threads.append(thread)
        thread.start()
        
        # 稍微延迟一下，避免同时启动所有线程
        time.sleep(0.5)
    
    # 运行测试指定的时间
    logger.info(f"压力测试开始，将持续运行 {TEST_DURATION // 3600} 小时 {TEST_DURATION % 3600 // 60} 分钟")
    
    start_time = time.time()
    
    try:
        # 等待测试结束
        while time.time() - start_time < TEST_DURATION:
            # 输出总体统计信息（每5分钟）
            elapsed = time.time() - start_time
            if elapsed % 300 == 0:
                remaining = TEST_DURATION - elapsed
                logger.info(f"测试已运行 {int(elapsed) // 3600:.0f}:{int(elapsed) % 3600 // 60:02d}:{int(elapsed) % 60:02d}")
                logger.info(f"剩余时间 {int(remaining) // 3600:.0f}:{int(remaining) % 3600 // 60:02d}:{int(remaining) % 60:02d}")
                
                # 获取当前任务队列长度
                mission_lengths = MissionOCR.getMissionListsLength()
                logger.info(f"当前任务队列长度: {sum(mission_lengths.values())}")
                
                # 获取OCR引擎状态
                status = MissionOCR.getStatus()
                logger.info(f"OCR引擎状态: {status}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止测试...")
        
    finally:
        # 停止所有线程
        stop_event.set()
        
        # 等待所有线程结束
        logger.info("正在等待所有测试线程结束...")
        for thread in threads:
            thread.join(timeout=10)  # 设置超时时间
            
            if thread.is_alive():
                logger.warning(f"线程 {thread.ident} 无法正常结束，强制终止")
    
    # 收集线程结果
    thread_results = []
    while not result_queue.empty():
        try:
            result = result_queue.get(timeout=1)
            thread_results.append(result)
        except queue.Empty:
            break
    
    # 输出测试结果
    logger.info("=" * 60)
    logger.info("压力测试结束")
    logger.info("=" * 60)
    
    total_tasks = 0
    total_success = 0
    total_fail = 0
    total_crashes = 0
    total_recoveries = 0
    
    for result in thread_results:
        logger.info(f"线程 {result['thread_id']} - 执行 {result['task_count']} 个任务，成功: {result['success_count']}, 失败: {result['fail_count']}, 崩溃: {result.get('crash_count', 0)}, 恢复: {result.get('recovery_count', 0)}")
        total_tasks += result['task_count']
        total_success += result['success_count']
        total_fail += result['fail_count']
        total_crashes += result.get('crash_count', 0)
        total_recoveries += result.get('recovery_count', 0)
    
    if total_tasks > 0:
        logger.info(f"总计执行任务: {total_tasks}")
        logger.info(f"成功任务: {total_success} ({total_success / total_tasks * 100:.2f}%)")
        logger.info(f"失败任务: {total_fail} ({total_fail / total_tasks * 100:.2f}%)")
        logger.info(f"崩溃次数: {total_crashes}")
        logger.info(f"恢复次数: {total_recoveries}")
        logger.info(f"平均每个线程执行任务: {total_tasks / MAX_CONCURRENT_TASKS:.2f}")
        if total_crashes > 0:
            logger.info(f"崩溃恢复率: {total_recoveries / total_crashes * 100:.2f}%")
    else:
        logger.warning("没有执行任何任务")
    
    # 获取最终的OCR引擎状态
    status = MissionOCR.getStatus()
    logger.info(f"最终OCR引擎状态: {status}")
    
    # 清理临时图片
    if TEST_IMAGE_PATH and "temp_test_image" in TEST_IMAGE_PATH:
        try:
            os.remove(TEST_IMAGE_PATH)
            logger.info("临时测试图片已清理")
        except Exception as e:
            logger.warning(f"清理临时测试图片失败: {str(e)}")
    
    logger.info("压力测试完成")

if __name__ == "__main__":
    main()
