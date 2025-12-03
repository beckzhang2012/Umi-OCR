# ===============================================
# =============== 多引擎OCR - 任务管理器 ===============
# ===============================================

"""
多引擎OCR任务管理器，支持同时运行多个OCR引擎进行对比
"""

import os
import threading
from typing import Dict, List, Any

from umi_log import logger
from .mission import Mission
from ..ocr.tbpu import getParser, IgnoreArea
from ..ocr.api import getApiOcr, getLocalOptions
from ..utils.utils import argdIntConvert

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


class __MissionMultiOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._apis: Dict[str, Any] = {}  # 多个引擎api对象，key: apiKey
        self._api_keys: List[str] = []  # 当前启用的引擎列表

    # ========================= 【重载】 =========================

    # msnInfo: { 回调函数"onXX", 参数"argd":{"tbpu.xx", "ocr.xx", "multi_engines": []} }
    # msnList: [ { "path", "bytes", "base64" } ]
    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 实例化 tbpu 文本后处理模块
        msnInfo["tbpu"] = []
        argd = msnInfo["argd"]
        
        # 获取多引擎配置
        if "multi_engines" not in argd or not isinstance(argd["multi_engines"], list):
            logger.error("多引擎OCR任务缺少引擎配置")
            return "[Error] 多引擎OCR任务缺少引擎配置"
        
        self._api_keys = argd["multi_engines"]
        if len(self._api_keys) == 0:
            logger.error("多引擎OCR任务未选择任何引擎")
            return "[Error] 多引擎OCR任务未选择任何引擎"
        
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
        # 初始化所有引擎API
        argd = msnInfo["argd"]
        
        for api_key in self._api_keys:
            if api_key not in self._apis:
                # 获取引擎配置
                engine_argd = {}
                for k, v in argd.items():
                    if k.startswith(f"ocr.{api_key}."):
                        engine_argd[k[len(f"ocr.{api_key}."):]] = v
                    elif k.startswith("ocr."):
                        # 通用OCR配置
                        engine_argd[k[4:]] = v
                
                # 创建引擎实例
                res = getApiOcr(api_key, engine_argd)
                if isinstance(res, str):
                    logger.error(f"初始化引擎 {api_key} 失败：{res}")
                    return f"[Error] 初始化引擎 {api_key} 失败：{res}"
                self._apis[api_key] = res
            else:
                # 更新引擎配置
                engine_argd = {}
                for k, v in argd.items():
                    if k.startswith(f"ocr.{api_key}."):
                        engine_argd[k[len(f"ocr.{api_key}."):]] = v
                    elif k.startswith("ocr."):
                        engine_argd[k[4:]] = v
                
                # 恢复int类型
                argdIntConvert(engine_argd)
                msg = self._apis[api_key].start(engine_argd)
                if msg.startswith("[Error]"):
                    logger.error(f"更新引擎 {api_key} 配置失败：{msg}")
                    return f"[Error] 更新引擎 {api_key} 配置失败：{msg}"
        
        return ""

    def msnTask(self, msnInfo, msn):  # 执行msn
        # 为每个引擎并行执行OCR
        results = {}
        lock = threading.Lock()
        
        def run_engine(api_key):
            try:
                api = self._apis[api_key]
                
                if "path" in msn:
                    res = api.runPath(msn["path"])
                    res["path"] = msn["path"]
                elif "bytes" in msn:
                    res = api.runBytes(msn["bytes"])
                elif "base64" in msn:
                    res = api.runBase64(msn["base64"])
                else:
                    res = {
                        "code": 901,
                        "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}"
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
                
                with lock:
                    results[api_key] = res
                    
            except Exception as e:
                logger.error(f"引擎 {api_key} 执行任务失败：{e}")
                with lock:
                    results[api_key] = {
                        "code": 902,
                        "data": f"[Error] 引擎 {api_key} 执行任务失败：{e}"
                    }
        
        # 并行执行所有引擎
        threads = []
        for api_key in self._api_keys:
            t = threading.Thread(target=run_engine, args=(api_key,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 合成最佳结果
        best_result = self._synthesize_best_result(results)
        
        return {
            "code": 100,
            "data": results,
            "best_result": best_result,
            "path": msn.get("path", "")
        }

    def _synthesize_best_result(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """合成最佳结果"""
        if not results:
            return {"code": 101, "data": ""}
        
        # 找到置信度最高的结果
        best_engine = None
        best_score = -1
        best_data = None
        
        for engine, res in results.items():
            if res["code"] == 100 and "score" in res and res["score"] > best_score:
                best_score = res["score"]
                best_engine = engine
                best_data = res["data"]
        
        if best_engine:
            return {
                "code": 100,
                "data": best_data,
                "engine": best_engine,
                "score": best_score
            }
        
        # 如果所有引擎都失败，返回第一个失败结果
        first_res = next(iter(results.values()))
        return {
            "code": first_res["code"],
            "data": first_res["data"]
        }

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKeys": self._api_keys,
            "missionListsLength": self.getMissionListsLength(),
            "availableEngines": list(self._apis.keys())
        }

    def setEngines(self, engine_keys: List[str], argd: Dict[str, Any]):
        """设置要使用的引擎"""
        self._api_keys = engine_keys
        
        # 初始化引擎
        for api_key in engine_keys:
            if api_key not in self._apis:
                # 获取引擎配置
                engine_argd = {}
                for k, v in argd.items():
                    if k.startswith(f"ocr.{api_key}."):
                        engine_argd[k[len(f"ocr.{api_key}."):]] = v
                    elif k.startswith("ocr."):
                        engine_argd[k[4:]] = v
                
                # 创建引擎实例
                res = getApiOcr(api_key, engine_argd)
                if isinstance(res, str):
                    logger.error(f"初始化引擎 {api_key} 失败：{res}")
                    return f"[Error] 初始化引擎 {api_key} 失败：{res}"
                self._apis[api_key] = res
        
        return "[Success]"

    def clearEngines(self):
        """清除所有引擎"""
        for api in self._apis.values():
            api.stop()
        self._apis.clear()
        self._api_keys = []
        return "[Success]"

    # ========================= 【工具方法】 =========================

    def getEngineResults(self, msn_result: Dict[str, Any]) -> Dict[str, Any]:
        """获取所有引擎的结果"""
        if msn_result.get("code") == 100 and "data" in msn_result:
            return msn_result["data"]
        return {}

    def getBestResult(self, msn_result: Dict[str, Any]) -> Dict[str, Any]:
        """获取最佳结果"""
        if msn_result.get("code") == 100 and "best_result" in msn_result:
            return msn_result["best_result"]
        return {}

    def compareResults(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """对比多个引擎的结果"""
        comparisons = []
        
        # 获取所有引擎的文本块
        engine_blocks = {}
        for engine, res in results.items():
            if res["code"] == 100:
                engine_blocks[engine] = res["data"]
        
        if not engine_blocks:
            return comparisons
        
        # 简单的对比：比较每个引擎的文本内容
        # TODO: 实现更智能的文本对比算法
        for i, (engine1, blocks1) in enumerate(engine_blocks.items()):
            for j, (engine2, blocks2) in enumerate(engine_blocks.items()):
                if i >= j:
                    continue
                
                text1 = "".join([block["text"] for block in blocks1])
                text2 = "".join([block["text"] for block in blocks2])
                
                # 计算相似度（简单的长度对比）
                similarity = min(len(text1), len(text2)) / max(len(text1), len(text2)) if max(len(text1), len(text2)) > 0 else 0
                
                comparisons.append({
                    "engine1": engine1,
                    "engine2": engine2,
                    "similarity": similarity,
                    "text1": text1,
                    "text2": text2,
                    "differences": self._find_differences(text1, text2)
                })
        
        return comparisons

    def _find_differences(self, text1: str, text2: str) -> List[Dict[str, Any]]:
        """查找两个文本之间的差异"""
        differences = []
        
        # 简单的差异查找：逐字符比较
        min_len = min(len(text1), len(text2))
        
        for i in range(min_len):
            if text1[i] != text2[i]:
                differences.append({
                    "position": i,
                    "char1": text1[i],
                    "char2": text2[i],
                    "type": "character_diff"
                })
        
        # 处理长度差异
        if len(text1) != len(text2):
            differences.append({
                "position": min_len,
                "length_diff": abs(len(text1) - len(text2)),
                "type": "length_diff",
                "longer_text": "text1" if len(text1) > len(text2) else "text2"
            })
        
        return differences


# 全局多引擎OCR任务管理器
MissionMultiOCR = __MissionMultiOcrClass()