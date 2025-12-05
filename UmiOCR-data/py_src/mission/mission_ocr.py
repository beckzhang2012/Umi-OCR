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
import threading
from typing import List, Dict

from umi_log import logger
from .mission import Mission
from ..ocr.tbpu import getParser, IgnoreArea
from ..ocr.api import getApiOcr, getLocalOptions
from ..utils.utils import argdIntConvert
from ..optimization.ocr_optimization import InputSlicer, get_throughput_monitor, get_memory_pool

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
        self._slicer = InputSlicer(max_segments=6)  # 输入切片编排器
        self._throughput_monitor = get_throughput_monitor()
        self._memory_pool = get_memory_pool()
        self._task_semaphore = threading.Semaphore(6)  # 控制最大并发段数

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
        start_time = time.time()
        
        try:
            # 检查是否需要切片处理
            if "path" in msn and self._should_slice(msn["path"]):
                res = self._process_with_slicing(msnInfo, msn)
            else:
                # 常规处理
                if "path" in msn:
                    res = self._api.runPath(msn["path"])
                    res["path"] = msn["path"]  # 结果字典中补充参数
                elif "bytes" in msn:
                    res = self._api.runBytes(msn["bytes"])
                elif "base64" in msn:
                    res = self._api.runBase64(msn["base64"])
                else:
                    res = {
                        "code": 901,
                        "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
                    }
                
                # 任务成功时的后处理
                if res["code"] == 100:
                    res = self._post_process_result(res, msnInfo)
        
        except Exception as e:
            logger.error(f"OCR任务执行失败: {msn.get('path', 'unknown')}, error: {e}")
            res = {
                "code": 902,
                "data": f"[Error] Task execution failed.\n【异常】任务执行失败。\n{str(e)}",
            }
        
        # 记录性能指标
        processing_time = time.time() - start_time
        self._record_performance(1, processing_time, 0.0)
        
        return res
    
    def _should_slice(self, image_path: str) -> bool:
        """判断是否需要对图片进行切片处理"""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                width, height = img.size
                area = width * height
                return area > 1024 * 1024  # 大于100万像素的图片需要切片
        except Exception:
            return False
    
    def _process_with_slicing(self, msnInfo: Dict, msn: Dict) -> Dict:
        """使用切片方式处理大图片"""
        image_path = msn["path"]
        segments = self._slicer.slice_image(image_path)
        
        if len(segments) == 1:
            # 不需要切片，直接处理
            res = self._api.runPath(image_path)
            res["path"] = image_path
            if res["code"] == 100:
                res = self._post_process_result(res, msnInfo)
            return res
        
        # 使用内存池获取buffer
        buffer = self._memory_pool.acquire()
        
        try:
            # 并行处理各个区域
            results = []
            threads = []
            lock = threading.Lock()
            
            def process_segment(segment: Dict):
                with self._task_semaphore:
                    segment_start = time.time()
                    
                    # 这里需要OCR API支持区域识别
                    # 暂时使用完整图片识别，后续需要API支持区域参数
                    res = self._api.runPath(segment["path"])
                    res["segment_coords"] = segment["coords"]
                    
                    with lock:
                        results.append(res)
                    
                    # 记录单个区域的性能
                    segment_time = time.time() - segment_start
                    self._record_performance(1, segment_time, 0.0, is_segment=True)
            
            # 创建线程处理每个区域
            for segment in segments:
                thread = threading.Thread(target=process_segment, args=(segment,))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 合并结果
            merged_res = self._slicer.merge_results(results)
            merged_res["path"] = image_path
            
            # 执行 tbpu
            if merged_res["code"] == 100 and msnInfo["tbpu"]:
                for tbpu in msnInfo["tbpu"]:
                    merged_res["data"] = tbpu.run(merged_res["data"])
                    if not merged_res["data"]:
                        merged_res["code"] = 101
                        merged_res["data"] = ""
                        break
            
            return merged_res
            
        finally:
            if buffer:
                self._memory_pool.release(buffer)
    
    def _post_process_result(self, res: Dict, msnInfo: Dict) -> Dict:
        """后处理OCR结果"""
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
        
        return res
    
    def _record_performance(self, batch_size: int, processing_time: float, 
                           waiting_time: float, is_segment: bool = False) -> None:
        """记录性能指标"""
        try:
            import psutil
            memory_usage = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        except Exception:
            memory_usage = 0.0
        
        self._throughput_monitor.record_batch(
            batch_size=batch_size,
            processing_time=processing_time,
            waiting_time=waiting_time,
            memory_usage=memory_usage
        )
        
        if not is_segment:
            logger.debug(f"任务完成: 大小={batch_size}, 处理时间={processing_time:.2f}s, 内存={memory_usage:.2f}MB")

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
    
    def getPerformanceMetrics(self) -> Dict:
        """获取性能指标"""
        return self._throughput_monitor.get_metrics()
    
    def resetPerformanceMetrics(self) -> None:
        """重置性能指标"""
        self._throughput_monitor.reset()
    
    def getMemoryPoolStatus(self) -> Dict:
        """获取内存池状态"""
        return {
            "free_buffers": len(self._memory_pool.free_buffers),
            "used_buffers": len(self._memory_pool.used_buffers),
            "max_buffers": self._memory_pool.max_buffers,
            "buffer_size": self._memory_pool.buffer_size
        }


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
