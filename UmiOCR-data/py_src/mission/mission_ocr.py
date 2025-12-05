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
from ..ocr.api.hardware_manager import HardwareManagerGlobal, BackendType
from ..utils.utils import argdIntConvert
from ..scheduler.optimized_scheduler import OptimizedTaskSchedulerGlobal
from ..scheduler.cpu_optimized_scheduler import CPUOptimizedSchedulerGlobal
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
        
        # 优化组件初始化
        self.optimized_scheduler = OptimizedTaskSchedulerGlobal
        self.cpu_optimized_scheduler = CPUOptimizedSchedulerGlobal
        self.throughput_monitor = ThroughputMonitorGlobal
        self.hardware_manager = HardwareManagerGlobal
        
        # 启动GPU监控
        self.hardware_manager.start_gpu_monitoring()
        
        # 启动CPU优化调度器
        self.cpu_optimized_scheduler.start()

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
        # 获取当前后端
        current_backend = self.hardware_manager.get_current_backend()
        
        if "path" in msn:
            data = msn["path"]
            run_func = self._api.runPath
        elif "bytes" in msn:
            data = msn["bytes"]
            run_func = self._api.runBytes
        elif "base64" in msn:
            data = msn["base64"]
            run_func = self._api.runBase64
        else:
            res = {
                "code": 901,
                "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
            }
            return res
        
        # 记录线程等待时间（开始）
        thread_start_time = time.time()
        
        # 根据当前后端选择不同的调度器
        if current_backend == BackendType.GPU:
            # GPU模式：使用优化调度器
            res = self.optimized_scheduler.submit_task(run_func, data)
        else:
            # CPU模式：使用CPU优化调度器
            res = self.cpu_optimized_scheduler.submit_task(run_func, data)
        
        # 记录线程等待时间（结束）
        thread_wait_time = time.time() - thread_start_time
        self.throughput_monitor.record_thread_wait_time(thread_wait_time)
        
        # 补充路径参数
        if "path" in msn:
            res["path"] = msn["path"]
        
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
            
            # 添加硬件和优化信息到结果
            switch_reason = self.hardware_manager.get_switch_reason()
            
            res["hardware_info"] = {
                "current_backend": current_backend.value,
                "switch_reason": switch_reason.value if switch_reason else None,
                "expected_recovery_time": self.hardware_manager.get_expected_recovery_time(),
            }
            
            res["optimization_info"] = {
                "used_slices": 0,  # 暂时未实现切片功能
                "max_memory": 0,  # 暂时未实现内存监控
            }
        
        return res

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
