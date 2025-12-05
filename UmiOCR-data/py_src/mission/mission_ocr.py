# ===============================================
# =============== OCR - 任务管理器 ===============
# ===============================================

"""
一种任务管理器为全局单例，不同标签页要执行同一种任务，要访问对应的任务管理器。
任务管理器中有一个引擎API实例，所有任务均使用该API。
标签页可以向任务管理器提交一组任务队列，其中包含了每一项任务的信息，及总体的参数和回调。
"""

import os
import time

from umi_log import logger
from .mission import Mission
from ..ocr.tbpu import getParser, IgnoreArea
from ..ocr.api import getApiOcr, getLocalOptions
from ..ocr.api.slice_orchestrator import SliceOrchestratorGlobal
from ..utils.utils import argdIntConvert
from ..utils.memory_pool import MemoryPoolGlobal
from ..scheduler.optimized_scheduler import OptimizedTaskSchedulerGlobal
from ..monitor.throughput_monitor import ThroughputMonitorGlobal

# 合法文件后缀
ImageSuf = [
    ".jpg",
    ".jpe",
    ".jpeg",
    ".jfif",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
]


class __MissionOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._apiKey = ""  # 当前api类型
        self._api = None  # 当前引擎api对象
        
        # 优化模块
        self._slice_orchestrator = SliceOrchestratorGlobal
        self._memory_pool = MemoryPoolGlobal
        self._optimized_scheduler = OptimizedTaskSchedulerGlobal
        self._throughput_monitor = ThroughputMonitorGlobal

    # ========================= 【重载】 =========================

    # msnInfo: { 回调函数"onXX", 参数"argd":{"tbpu.xx", "ocr.xx"} }
    # msnList: [ { "path", "bytes", "base64" } ]
    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 实例化 tbpu 文本后处理模块
        msnInfo["tbpu"] = []
        argd = msnInfo["argd"]
        # 忽略区域
        if "tbpu.ignoreArea" in argd:
            iArea = argd["tbpu.ignoreArea"]
            if isinstance(iArea, list) and len(iArea) > 0:
                msnInfo["tbpu"].append(IgnoreArea(iArea))
        # 获取排版解析器对象
        if "tbpu.parser" in argd:
            msnInfo["tbpu"].append(getParser(argd["tbpu.parser"]))
        # 检查任务合法性
        for i in range(len(msnList) - 1, -1, -1):
            if "path" in msnList[i]:
                p = msnList[i]["path"]
                if os.path.splitext(p)[-1].lower() not in ImageSuf:
                    logger.warning(f"添加OCR任务时，第{i}项的路径path不是图片：{p}")
                    del msnList[i]
            elif "bytes" not in msnList[i] and "base64" not in msnList[i]:
                logger.warning(f"添加OCR任务时，第{i}项不含 path、bytes、base64")
                del msnList[i]
        return super().addMissionList(msnInfo, msnList)

    def msnPreTask(self, msnInfo):  # 用于更新api和参数
        # 检查API对象
        if not self._api:
            return "[Error] MissionOCR: API object is None."
        # 检查参数更新
        startInfo = self._dictShortKey(msnInfo["argd"])
        # 恢复int类型
        argdIntConvert(startInfo)
        msg = self._api.start(startInfo)
        if msg.startswith("[Error]"):
            logger.error(f"OCR引擎启动失败： {msg}")
            return msg  # 更新失败，结束该队列
        else:
            return ""  # 更新成功 TODO: continue

    def msnTask(self, msnInfo, msn):  # 执行msn
        # 开始任务监测
        task_id = f"{msnInfo['msnID']}_{int(time.time())}"
        self._throughput_monitor.start_task_monitoring(task_id)
        
        try:
            # 加载图像
            if "path" in msn:
                image_path = msn["path"]
                slices = self._slice_orchestrator.slice_image(image_path=image_path)
            elif "bytes" in msn:
                image_bytes = msn["bytes"]
                slices = self._slice_orchestrator.slice_image(image_bytes=image_bytes)
            elif "base64" in msn:
                image_base64 = msn["base64"]
                slices = self._slice_orchestrator.slice_image(image_base64=image_base64)
            else:
                res = {
                    "code": 901,
                    "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
                }
                return res
            
            # 计算图像大小
            if slices:
                first_slice = slices[0]['image_np']
                image_size = first_slice.shape[0] * first_slice.shape[1] * len(slices)
            else:
                image_size = 0
            
            # 处理所有切片
            slice_results = []
            
            def _slice_task(slice_data):
                """切片处理任务"""
                try:
                    # 从内存池获取buffer
                    slice_np = slice_data['image_np']
                    buffer = self._memory_pool.get_cpu_buffer(slice_np.shape)
                    
                    # 复制图像数据到buffer
                    buffer[:] = slice_np[:]
                    
                    # 执行OCR
                    res = self._api.runBytes(buffer.tobytes())
                    
                    # 释放buffer回内存池
                    self._memory_pool.release_cpu_buffer(buffer)
                    
                    # 添加切片信息到结果
                    res['offset'] = slice_data['offset']
                    res['slice_index'] = slice_data.get('slice_index', 0)
                    
                    return res
                    
                except Exception as e:
                    logger.error(f"切片处理失败: {e}")
                    return {
                        "code": 902,
                        "data": f"[Error] Slice processing failed: {e}",
                    }
            
            # 使用优化的任务调度器处理切片
            from concurrent.futures import Future
            import psutil
            
            futures: List[Future] = []
            max_memory = 0
            
            for i, slice_data in enumerate(slices):
                slice_data['slice_index'] = i
                
                # 记录线程等待时间
                wait_start_time = time.time()
                
                # 添加任务到调度器
                future = Future()
                futures.append(future)
                
                def _task_callback(result, future=future):
                    nonlocal max_memory
                    # 记录内存使用峰值
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    if current_memory > max_memory:
                        max_memory = current_memory
                    future.set_result(result)
                
                self._optimized_scheduler.add_task(
                    _slice_task,
                    args=[slice_data],
                    callback=_task_callback,
                    image_size=image_size
                )
                
                # 记录线程等待时间
                wait_time = time.time() - wait_start_time
                self._throughput_monitor.record_thread_wait_time(wait_time)
            
            # 等待所有切片处理完成
            for future in futures:
                slice_res = future.result()
                slice_results.append(slice_res)
            
            # 合并切片结果
            if slices:
                first_slice = slices[0]['image_np']
                image_shape = (first_slice.shape[0] * len(slices), first_slice.shape[1])
            else:
                image_shape = (0, 0)
            
            merged_data = self._slice_orchestrator.merge_results(slice_results, image_shape)
            
            # 生成最终结果
            res = {
                "code": 100,
                "data": merged_data,
            }
            
            # 任务成功时的后处理
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
                        # 如果忽略区域等处理将所有文本删除，则结束tbpu
                        if not res["data"]:
                            res["code"] = 101
                            res["data"] = ""
                            break
            
            # 补充路径信息和内存峰值
            if "path" in msn:
                res["path"] = msn["path"]
            res["max_memory"] = max_memory  # MB
            
            # 记录内存峰值到吞吐量监测器
            ThroughputMonitorGlobal.update_peak_resources(memory_peak=max_memory / 1024)  # 转换为GB
            
            return res
            
        finally:
            # 停止任务监测
            self._throughput_monitor.stop_task_monitoring()

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKey": self._apiKey,
            "missionListsLength": self.getMissionListsLength(),
        }

    def setApi(self, apiKey, info):  # 设置api
        # 成功返回 [Success] ，失败返回 [Error] 开头的字符串
        self._apiKey = apiKey
        info = self._dictShortKey(info)
        # 如果api对象已启动，则先停止
        if self._api:
            self._api.stop()
        # 获取新api对象
        res = getApiOcr(apiKey, info)
        # 失败
        if isinstance(res, str):
            self._apiKey = ""
            self._api = None
            return res
        # 成功
        else:
            self._api = res
            return "[Success]"

    # 将字典中配置项的长key转为短key
    # 如： ocr.win32_PaddleOCR-json.path → path
    def _dictShortKey(self, d):
        newD = {}
        key1 = "ocr."
        key2 = key1 + self._apiKey + "."
        for k in d:
            if k.startswith(key2):
                newD[k[len(key2) :]] = d[k]
            elif k.startswith(key1):
                newD[k[len(key1) :]] = d[k]
        return newD

    # ========================= 【qml接口】 =========================

    def getLocalOptions(self):
        if self._apiKey:
            return getLocalOptions(self._apiKey)
        else:
            return {}


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
