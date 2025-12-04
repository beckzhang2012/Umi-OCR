# ===============================================
# =============== OCR - 任务管理器 ===============
# ===============================================

"""
一种任务管理器为全局单例，不同标签页要执行同一种任务，要访问对应的任务管理器。
任务管理器中有一个引擎API实例，所有任务均使用该API。
标签页可以向任务管理器提交一组任务队列，其中包含了每一项任务的信息，及总体的参数和回调。
"""

import os
import threading
from typing import Optional, Dict, List

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


class __MissionOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._apiKey = ""  # 当前api类型
        self._api = None  # 当前引擎api对象
        self._threadLock = threading.Lock()  # 线程安全锁
        self._threadId: Optional[int] = None  # 当前运行的线程ID
        self._isRunning = False  # 任务运行状态
        self._missionContext: Dict = {}  # 任务上下文，确保线程生命周期和上下文一致
        self._recoveryAttempts: Dict[str, int] = {}  # 任务恢复尝试次数，防止无限重试
        self._maxRecoveryAttempts = 3  # 最大恢复尝试次数

    # ========================= 【重载】 =========================

    def _validate_thread_context(self, msnID: str) -> bool:
        """
        原子校验：验证线程ID和任务上下文是否一致
        
        Args:
            msnID (str): 任务ID
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        current_thread_id = threading.get_ident()
        
        with self._threadLock:
            # 检查线程ID是否匹配
            if self._threadId is not None and self._threadId != current_thread_id:
                logger.error(f"线程上下文不匹配: 当前线程ID={current_thread_id}, 预期线程ID={self._threadId}")
                return False
            
            # 检查任务上下文是否存在
            if msnID not in self._missionContext:
                logger.error(f"任务上下文不存在: msnID={msnID}")
                return False
            
            # 检查API对象是否有效
            if self._api is None:
                logger.error(f"API对象为空: msnID={msnID}")
                return False
            
            return True
    
    def _set_thread_context(self, msnID: str, thread_id: int) -> None:
        """
        设置线程上下文
        
        Args:
            msnID (str): 任务ID
            thread_id (int): 线程ID
        """
        with self._threadLock:
            self._threadId = thread_id
            self._isRunning = True
            self._missionContext[msnID] = {
                'thread_id': thread_id,
                'api_key': self._apiKey,
                'api_info': self._api.__dict__ if self._api else None,
                'timestamp': threading.get_ident()
            }
            logger.info(f"线程上下文已设置: msnID={msnID}, thread_id={thread_id}")
    
    def _clear_thread_context(self, msnID: str) -> None:
        """
        清除线程上下文
        
        Args:
            msnID (str): 任务ID
        """
        with self._threadLock:
            if msnID in self._missionContext:
                del self._missionContext[msnID]
            
            # 如果没有正在运行的任务，清除线程ID
            if not self._missionContext:
                self._threadId = None
                self._isRunning = False
            
            # 清除恢复尝试次数记录
            if msnID in self._recoveryAttempts:
                del self._recoveryAttempts[msnID]
            
            logger.info(f"线程上下文已清除: msnID={msnID}")
    
    def _is_thread_valid(self) -> bool:
        """
        检查当前线程是否有效
        
        Returns:
            bool: 有效返回True，否则返回False
        """
        current_thread_id = threading.get_ident()
        
        with self._threadLock:
            return self._threadId == current_thread_id
    
    def _handle_thread_exception(self, msnID: str, exception: Exception) -> bool:
        """
        处理线程异常，尝试恢复任务
        
        Args:
            msnID (str): 任务ID
            exception (Exception): 异常对象
            
        Returns:
            bool: 恢复成功返回True，否则返回False
        """
        logger.error(f"线程异常发生: msnID={msnID}, error={exception}", exc_info=True)
        
        with self._threadLock:
            # 检查恢复尝试次数
            attempt_count = self._recoveryAttempts.get(msnID, 0) + 1
            self._recoveryAttempts[msnID] = attempt_count
            
            if attempt_count > self._maxRecoveryAttempts:
                logger.error(f"恢复尝试次数已达上限: msnID={msnID}, attempt_count={attempt_count}, max_attempts={self._maxRecoveryAttempts}")
                return False
        
        try:
            # 尝试从最近的快照恢复任务
            logger.info(f"尝试恢复任务: msnID={msnID}, attempt={attempt_count}/{self._maxRecoveryAttempts}")
            
            # 清除当前线程上下文
            self._clear_thread_context(msnID)
            
            # 调用父类的恢复方法
            success = self._try_recover_task(msnID)
            
            if success:
                logger.info(f"任务恢复成功: msnID={msnID}, attempt={attempt_count}")
                
                # 重置恢复尝试次数
                with self._threadLock:
                    if msnID in self._recoveryAttempts:
                        del self._recoveryAttempts[msnID]
                
                return True
            else:
                logger.error(f"任务恢复失败: msnID={msnID}, attempt={attempt_count}")
                return False
                
        except Exception as recovery_error:
            logger.error(f"恢复过程发生异常: msnID={msnID}, error={recovery_error}", exc_info=True)
            return False
    
    def _reset_api(self) -> bool:
        """
        重置API对象，用于异常恢复
        
        Returns:
            bool: 重置成功返回True，否则返回False
        """
        try:
            with self._threadLock:
                # 重新初始化API
                if self._apiKey:
                    self._api = getApiOcr(self._apiKey)
                    logger.info(f"API对象已重置: apiKey={self._apiKey}")
                    return True
                else:
                    logger.error("无法重置API: apiKey为空")
                    return False
        except Exception as e:
            logger.error(f"重置API失败: error={e}", exc_info=True)
            return False
    
    # msnInfo: { 回调函数"onXX", 参数"argd":{"tbpu.xx", "ocr.xx"} }
    # msnList: [ { "path", "bytes", "base64" } ]
    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 原子校验：确保在添加任务时API对象有效
        with self._threadLock:
            if self._api is None:
                error_msg = "[Error] MissionOCR: Cannot add mission list - API object is None."
                logger.error(error_msg)
                return error_msg
        
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
        
        # 调用父类方法添加任务列表
        result = super().addMissionList(msnInfo, msnList)
        
        # 如果添加成功，设置任务上下文
        if not result.startswith("[Error]"):
            msnID = result  # 假设父类返回任务ID
            current_thread_id = threading.get_ident()
            self._set_thread_context(msnID, current_thread_id)
        
        return result

    def msnPreTask(self, msnInfo):  # 用于更新api和参数
        # 原子校验：验证线程上下文
        msnID = msnInfo.get("msnID", "unknown")
        if not self._validate_thread_context(msnID):
            return f"[Error] MissionOCR: Thread context validation failed for msnID={msnID}."
        
        # 检查API对象
        if not self._api:
            error_msg = "[Error] MissionOCR: API object is None."
            logger.error(error_msg)
            return error_msg
        
        try:
            # 检查参数更新
            startInfo = self._dictShortKey(msnInfo["argd"])
            # 恢复int类型
            argdIntConvert(startInfo)
            msg = self._api.start(startInfo)
            
            if msg.startswith("[Error]"):
                logger.error(f"OCR引擎启动失败： {msg}")
                return msg  # 更新失败，结束该队列
            else:
                logger.info(f"OCR引擎启动成功: msnID={msnID}")
                return ""  # 更新成功
        except Exception as e:
            logger.error(f"msnPreTask执行异常: msnID={msnID}, error={e}", exc_info=True)
            return f"[Error] MissionOCR: msnPreTask failed - {str(e)}"

    def msnTask(self, msnInfo, msn):  # 执行msn
        msnID = msnInfo.get("msnID", "unknown")
        
        # 原子校验：验证线程上下文
        if not self._validate_thread_context(msnID):
            return {
                "code": 902,
                "data": f"[Error] Thread context validation failed.\n【异常】线程上下文校验失败。\nmsnID={msnID}",
            }
        
        try:
            if "path" in msn:
                res = self._api.runPath(msn["path"])
                res["path"] = msn["path"]  # 结果字典中补充参数
                logger.debug(f"OCR任务执行中: path={msn['path']}")
            elif "bytes" in msn:
                res = self._api.runBytes(msn["bytes"])
                logger.debug("OCR任务执行中: bytes数据")
            elif "base64" in msn:
                res = self._api.runBase64(msn["base64"])
                logger.debug("OCR任务执行中: base64数据")
            else:
                error_msg = f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}"
                logger.error(error_msg)
                return {
                    "code": 901,
                    "data": error_msg,
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
            
            logger.debug(f"OCR任务执行完成: code={res['code']}")
            return res
            
        except Exception as e:
            error_msg = f"[Error] msnTask failed.\n【异常】任务执行失败。\nmsnID={msnID}, error={str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # 尝试恢复任务
            if self._handle_thread_exception(msnID, e):
                # 恢复成功，返回特殊标记表示需要重新执行
                return {
                    "code": 904,
                    "data": "[Recovery] MissionOCR: Task recovered, need to re-execute.",
                }
            else:
                return {
                    "code": 903,
                    "data": error_msg,
                }

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKey": self._apiKey,
            "missionListsLength": self.getMissionListsLength(),
        }

    def setApi(self, apiKey, info):  # 设置api
        # 原子校验：确保在设置API时没有任务正在运行
        with self._threadLock:
            if self._isRunning:
                error_msg = "[Error] MissionOCR: Cannot set API while missions are running."
                logger.error(error_msg)
                return error_msg
        
        try:
            self._apiKey = apiKey
            info = self._dictShortKey(info)
            
            # 如果api对象已启动，则先停止
            if self._api:
                logger.info(f"正在停止旧的API: {self._apiKey}")
                self._api.stop()
            
            # 获取新api对象
            res = getApiOcr(apiKey, info)
            
            # 失败
            if isinstance(res, str):
                self._apiKey = ""
                self._api = None
                logger.error(f"API设置失败: {res}")
                return res
            # 成功
            else:
                self._api = res
                logger.info(f"API设置成功: {apiKey}")
                return "[Success]"
                
        except Exception as e:
            self._apiKey = ""
            self._api = None
            error_msg = f"[Error] MissionOCR: setApi failed - {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

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
        try:
            if self._apiKey:
                return getLocalOptions(self._apiKey)
            else:
                return {}
        except Exception as e:
            logger.error(f"getLocalOptions执行异常: {e}", exc_info=True)
            return {}
    
    # ========================= 【线程状态查询】 =========================
    
    def is_mission_running(self) -> bool:
        """
        检查是否有任务正在运行
        
        Returns:
            bool: 有任务运行返回True，否则返回False
        """
        with self._threadLock:
            return self._isRunning
    
    def get_thread_id(self) -> Optional[int]:
        """
        获取当前运行的线程ID
        
        Returns:
            Optional[int]: 线程ID，没有运行的任务返回None
        """
        with self._threadLock:
            return self._threadId
    
    def get_mission_context(self, msnID: str) -> Optional[Dict]:
        """
        获取任务上下文
        
        Args:
            msnID (str): 任务ID
            
        Returns:
            Optional[Dict]: 任务上下文，不存在返回None
        """
        with self._threadLock:
            return self._missionContext.get(msnID)


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
