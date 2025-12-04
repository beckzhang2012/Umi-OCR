# ==============================================
# =============== 任务管理器 基类 ===============
# ==============================================


from PySide2.QtCore import QMutex, QRunnable
from threading import Condition
from uuid import uuid4  # 唯一ID
import time
import traceback

from umi_log import logger
from ..utils.thread_pool import threadRun  # 异步执行函数
from .mission_snapshot import SnapshotManagerInstance


class Mission:
    def __init__(self):
        self._msnInfoDict = {}  # 任务信息的字典
        self._msnListDict = {}  # 任务队列的字典
        self._msnPausedDict = {}  # 已暂停的任务队列
        self._msnMutex = QMutex()  # 任务队列的锁
        self._task = None  # 异步任务对象
        self._taskMutex = QMutex()  # 任务对象的锁
        # 任务队列调度方式
        # 1111 : 轮询调度，轮流取每个队列的第1个任务
        # 1234 : 顺序调度，将首个队列所有任务处理完，再进入下一个队列
        self._schedulingMode = "1111"

    # ========================= 【调用接口】 =========================

    """
    添加任务队列的格式
    mission = {
        "onStart": 任务队列开始回调函数 , (msnInfo)
        "onReady": 一项任务准备开始 , (msnInfo, msn)
        "onGet": 一项任务获取结果 , (msnInfo, msn, res)
        "onEnd": 任务队列结束 , (msnInfo, msg) // msg可选前缀： [Success] [Warning] [Error]
    }
    MissionOCR.addMissionList(mission, paths)
    """

    # 【异步】添加一条任务队列。成功返回任务ID，失败返回 startswith("[Error]")
    # msnInfo: { 回调函数 "onStart", "onReady", "onGet", "onEnd"}
    # msnList: [ 任务1, 任务2 ]
    def addMissionList(self, msnInfo, msnList):
        if len(msnList) < 1:
            return "[Error] no valid mission in msnList!"
        msnID = str(uuid4())
        # 检查并补充回调函数
        # 队列开始，单个任务准备开始，单任务取得结果，队列结束
        cbKeys = ["onStart", "onReady", "onGet", "onEnd"]
        for k in cbKeys:
            if k not in msnInfo or not callable(msnInfo[k]):
                msnInfo[k] = lambda *e: None
        # 任务状态state:  waiting 等待开始， running 进行中， stop 要求停止
        msnInfo["state"] = "waiting"
        msnInfo["msnID"] = msnID
        # 添加到任务队列
        self._msnMutex.lock()  # 上锁
        self._msnInfoDict[msnID] = msnInfo  # 添加任务信息
        self._msnListDict[msnID] = msnList  # 添加任务队列
        self._msnMutex.unlock()  # 解锁
        # 启动任务
        self._startMsns()
        # 返回任务id
        return msnID

    # 停止一些任务队列
    def stopMissionList(self, msnIDs):
        if not isinstance(msnIDs, list):
            msnIDs = [msnIDs]
        self._msnMutex.lock()  # 上锁
        for msnID in msnIDs:
            # 将暂停中的任务恢复
            if msnID in self._msnPausedDict:
                info, list_ = self._msnPausedDict[msnID]
                self._msnInfoDict[msnID] = info
                self._msnListDict[msnID] = list_
            # 将进行中的任务置为停止状态
            if msnID in self._msnListDict:
                self._msnInfoDict[msnID]["state"] = "stop"  # 设为停止状态
        self._msnMutex.unlock()  # 解锁
        self._startMsns()  # 拉起工作线程，使已暂停的任务可以正常结束

    # 停止全部任务
    def stopAllMissions(self):
        self._msnMutex.lock()  # 上锁
        # 将暂停中的任务恢复
        for msnID in self._msnPausedDict:
            info, list_ = self._msnPausedDict[msnID]
            self._msnInfoDict[msnID] = info
            self._msnListDict[msnID] = list_
        # 将进行中的任务置为停止状态
        for msnID in self._msnListDict:
            self._msnInfoDict[msnID]["state"] = "stop"
        self._msnMutex.unlock()  # 解锁
        self._startMsns()

    # 暂停一些任务队列
    def pauseMissionList(self, msnIDs):
        if not isinstance(msnIDs, list):
            msnIDs = [msnIDs]
        self._msnMutex.lock()  # 上锁
        for msnID in msnIDs:
            if msnID in self._msnListDict:
                msn = (self._msnInfoDict[msnID], self._msnListDict[msnID])
                self._msnPausedDict[msnID] = msn
                del self._msnInfoDict[msnID]
                del self._msnListDict[msnID]
        self._msnMutex.unlock()  # 解锁
        logger.debug(f"任务暂停： {msnID}")

    # 恢复一些任务队列的运行
    def resumeMissionList(self, msnIDs):
        if not isinstance(msnIDs, list):
            msnIDs = [msnIDs]
        self._msnMutex.lock()  # 上锁
        for msnID in msnIDs:
            if msnID in self._msnPausedDict:
                info, list_ = self._msnPausedDict[msnID]
                self._msnInfoDict[msnID] = info
                self._msnListDict[msnID] = list_
                del self._msnPausedDict[msnID]
        self._msnMutex.unlock()  # 解锁
        self._startMsns()  # 拉起工作线程
        logger.debug(f"任务恢复： {msnID}")

    # 获取每一条任务队列长度
    def getMissionListsLength(self):
        lenDict = {}
        self._msnMutex.lock()
        for k in self._msnListDict:
            lenDict[str(k)] = len(self._msnListDict[k])
        self._msnMutex.unlock()
        return lenDict

    # 【同步】添加一个任务或队列，等待完成，返回任务结果列表。[i]["result"]为结果
    def addMissionWait(self, argd, msnList):
        if not isinstance(msnList, list):
            msnList = [msnList]
        resList = msnList[:]  # 浅拷贝出一条结果列表
        nowIndex = 0  # 当前处理的任务
        msnLen = len(msnList)
        condition = Condition()  # 线程同步器
        endMsg = ""  # 任务结束的消息

        def _onGet(msnInfo, msn, res):
            nonlocal nowIndex
            resList[nowIndex]["result"] = res
            nowIndex += 1

        def _onEnd(msnInfo, msg):
            nonlocal endMsg
            endMsg = msg
            with condition:  # 释放线程阻塞
                condition.notify()

        def _pass(*x):
            pass

        msnInfo = {
            "onStart": _pass,
            "onReady": _pass,
            "onGet": _onGet,
            "onEnd": _onEnd,
            "argd": argd,
        }
        msnID = self.addMissionList(msnInfo, msnList)
        if msnID.startswith("[Error]"):  # 添加任务失败
            endMsg = msnID
        else:  # 添加成功，线程阻塞，直到任务完成。
            with condition:
                condition.wait()
        # 补充未完成的任务
        for i in range(nowIndex, msnLen):
            if "result" not in resList[i]:
                resList[i]["result"] = {"code": 803, "data": f"任务提前结束。{endMsg}"}
        return resList

    # ========================= 【主线程 方法】 =========================

    def _startMsns(self):  # 启动异步任务，执行所有任务列表
        # 若当前异步任务对象为空，则创建工作线程
        self._taskMutex.lock()  # 上锁
        if self._task == None:
            self._task = threadRun(self._taskRun)
        self._taskMutex.unlock()  # 解锁

    # ========================= 【子线程 方法】 =========================

    def _taskRun(self):  # 异步执行任务字典的流程
        dictIndex = 0  # 当前取任务字典中的第几个任务队列
        restart_count = 0  # 线程重启次数
        max_restart_count = 5  # 最大重启次数
        
        # 循环，直到任务队列的列表为空或达到最大重启次数
        while restart_count < max_restart_count:
            try:
                # 1. 检查api和任务字典是否为空
                self._msnMutex.lock()  # 锁1 上锁
                dl = len(self._msnInfoDict)  # 任务字典长度
                if dl == 0:  # 任务字典已空
                    self._msnMutex.unlock()  # 锁1 解锁
                    logger.info("任务字典已空，任务执行结束")
                    break

                # 2. 任务调度，取一个任务
                if self._schedulingMode == "1111":  # 轮询
                    dictIndex = (dictIndex + 1) % dl
                elif self._schedulingMode == "1234":  # 顺序
                    dictIndex = 0  # 始终为首个队列
                dictKey = tuple(self._msnInfoDict.keys())[dictIndex]
                msnInfo = self._msnInfoDict[dictKey]
                msnList = self._msnListDict[dictKey]
                self._msnMutex.unlock()  # 锁1 解锁

                # 3. 检查任务是否要求停止
                if msnInfo["state"] == "stop":
                    logger.info(f"任务队列 {dictKey} 被要求停止")
                    self._msnDictDel(dictKey)
                    msnInfo["onEnd"](msnInfo, "[Warning] Task stop.")
                    continue

                # 4. 前处理，检查、更新参数
                try:
                    preFlag = self.msnPreTask(msnInfo)
                except Exception as e:
                    logger.error(f"任务队列 {dictKey} 前处理失败: {e}", exc_info=True, stack_info=True)
                    msnInfo["onEnd"](msnInfo, f"[Error] Pre-task failed: {e}")
                    self._msnDictDel(dictKey)
                    dictIndex -= 1  # 字典下标回退1位，下次执行正确的下一项
                    continue
                
                if preFlag == "continue":  # 跳过本次
                    logger.debug(f"任务队列 {dictKey} 跳过本次执行")
                    continue
                elif preFlag.startswith("[Error]"):  # 异常，结束该队列
                    logger.error(f"任务队列 {dictKey} 前处理异常: {preFlag}")
                    msnInfo["onEnd"](msnInfo, preFlag)
                    self._msnDictDel(dictKey)
                    dictIndex -= 1  # 字典下标回退1位，下次执行正确的下一项
                    continue

                # 5. 首次任务
                if msnInfo["state"] == "waiting":
                    try:
                        msnInfo["state"] = "running"
                        msnInfo["onStart"](msnInfo)
                        logger.info(f"任务队列 {dictKey} 开始执行，共 {len(msnList)} 个任务")
                        
                        # 创建任务快照
                        self._create_snapshot(dictKey, msnInfo, msnList)
                        logger.debug(f"任务队列 {dictKey} 快照已创建")
                    except Exception as e:
                        logger.error(f"任务队列 {dictKey} 启动失败: {e}", exc_info=True, stack_info=True)
                        msnInfo["onEnd"](msnInfo, f"[Error] Task start failed: {e}")
                        self._msnDictDel(dictKey)
                        dictIndex -= 1  # 字典下标回退1位，下次执行正确的下一项
                        continue

                # 6. 执行任务，并记录时间
                try:
                    msn = msnList[0]
                    msnInfo["onReady"](msnInfo, msn)
                    logger.debug(f"任务队列 {dictKey} 开始执行任务: {msn}")
                    
                    t1 = time.time()
                    res = self.msnTask(msnInfo, msn)
                    t2 = time.time()
                    
                    if isinstance(res, dict):  # 补充耗时和时间戳
                        res["time"] = t2 - t1
                        res["timestamp"] = t2
                    
                    logger.debug(f"任务队列 {dictKey} 任务执行完成，耗时: {t2 - t1:.2f}秒")
                except Exception as e:
                    logger.error(f"任务队列 {dictKey} 任务执行失败: {e}", exc_info=True, stack_info=True)
                    # 记录失败的任务
                    self._update_snapshot(dictKey, msn, None, is_failed=True, error=str(e))
                    # 继续下一个任务
                    continue

                # 7. 再次检查任务是否要求停止，或者已暂停
                self._msnMutex.lock()  # 锁2 上锁
                if msnInfo["state"] == "stop":
                    logger.info(f"任务队列 {dictKey} 在任务执行后被要求停止")
                    self._msnDictDel(dictKey)
                    self._msnMutex.unlock()  # 锁2 解锁
                    msnInfo["onEnd"](msnInfo, "[Warning] Task stop.")
                    continue
                if dictKey not in self._msnInfoDict:
                    logger.debug(f"任务队列 {dictKey} 已被移除，跳过后续处理")
                    self._msnMutex.unlock()  # 锁2 解锁
                    continue

                # 8. 不停止，则处理任务结果
                try:
                    # 检查是否是恢复标记
                    if isinstance(res, dict) and res.get("code") == 904:
                        logger.info(f"任务队列 {dictKey} 收到恢复标记，将重新执行当前任务")
                        self._msnMutex.unlock()  # 锁2 解锁
                        # 不弹出任务，继续执行当前任务
                        continue
                    
                    # 正常处理任务结果
                    msnList.pop(0)  # 弹出该任务
                    self._msnMutex.unlock()  # 锁2 解锁
                    
                    # 回调。注意：回调函数执行时间长时，可能用户再次提交了任务暂停，需要后续继续判断。
                    msnInfo["onGet"](msnInfo, msn, res)
                    logger.debug(f"任务队列 {dictKey} 任务结果已上报")
                    
                    # 更新任务快照
                    self._update_snapshot(dictKey, msn, res)
                except Exception as e:
                    logger.error(f"任务队列 {dictKey} 结果处理失败: {e}", exc_info=True, stack_info=True)
                    self._msnMutex.unlock()  # 确保解锁
                    # 继续下一个任务
                    continue

                # 9. 这条任务队列完成
                if len(msnList) == 0:
                    logger.info(f"任务队列 {dictKey} 所有任务执行完成")
                    msnInfo["onEnd"](msnInfo, "[Success]")
                    self._msnMutex.lock()  # 锁3 上锁
                    self._msnDictDel(dictKey)
                    self._msnMutex.unlock()  # 锁3 解锁
                    dictIndex -= 1  # 字典下标回退1位，下次执行正确的下一项
                    
                    # 移除任务快照
                    self._remove_snapshot(dictKey)
                    logger.debug(f"任务队列 {dictKey} 快照已移除")

            except Exception as e:
                logger.error(f"任务执行过程中发生未捕获异常: {e}", exc_info=True, stack_info=True)
                logger.error(f"当前上下文信息: dictIndex={dictIndex}, dictKey={dictKey if 'dictKey' in locals() else 'N/A'}")
                if 'msnInfo' in locals():
                    logger.error(f"任务信息: {msnInfo}")
                if 'msnList' in locals():
                    logger.error(f"任务队列长度: {len(msnList)}")
                
                # 尝试恢复任务
                if 'dictKey' in locals() and 'msnInfo' in locals() and 'msnList' in locals():
                    self._try_recover_task(dictKey, msnInfo, msnList, e)
                
                # 增加重启计数
                restart_count += 1
                logger.warning(f"线程异常退出，正在尝试重启... (第 {restart_count}/{max_restart_count} 次)")
                
                # 等待一段时间后重启
                time.sleep(1)
                
                # 继续下一个任务
                continue

        # 完成
        self._taskFinish()
        
        # 如果达到最大重启次数，记录错误日志
        if restart_count >= max_restart_count:
            logger.error(f"线程已达到最大重启次数 ({max_restart_count})，任务执行终止")
            # 通知UI线程已终止
            if hasattr(self, 'callQmlInMain'):
                self.callQmlInMain("onTaskThreadTerminated", max_restart_count)

    def _msnDictDel(self, dictKey):  # 停止一组任务队列
        try:
            # 正常 删除任务队列项
            if dictKey in self._msnInfoDict:
                del self._msnInfoDict[dictKey]
                del self._msnListDict[dictKey]
                logger.debug(f"已移除任务队列： {dictKey}")
            # 如果该任务在暂停中，则移除暂停队列中的项
            if dictKey in self._msnPausedDict:
                del self._msnPausedDict[dictKey]
                logger.debug(f"已移除暂停任务： {dictKey}")
        except Exception as e:
            logger.error(f"移除任务队列 {dictKey} 失败: {e}", exc_info=True, stack_info=True)

    def _taskFinish(self):  # 任务结束
        try:
            self._taskMutex.lock()  # 上锁
            self._task = None
            self._taskMutex.unlock()  # 解锁
            logger.info("任务执行线程已结束")
        except Exception as e:
            logger.error(f"任务结束处理失败: {e}", exc_info=True, stack_info=True)
        
    def _create_snapshot(self, msnID, msnInfo, msnList):
        """创建任务快照"""
        try:
            # 获取API信息（如果有）
            apiKey = getattr(self, '_apiKey', '')
            apiInfo = getattr(self, '_api', None)
            
            # 创建快照
            SnapshotManagerInstance.create_snapshot(msnID, msnInfo.copy(), msnList.copy(), apiKey, apiInfo)
            logger.info(f"已为任务 {msnID} 创建快照，共 {len(msnList)} 个任务")
        except Exception as e:
            logger.error(f"为任务 {msnID} 创建快照失败: {e}", exc_info=True, stack_info=True)
            
    def _update_snapshot(self, msnID, msn, res, is_failed=False, error=None):
        """更新任务快照"""
        try:
            # 获取当前任务在队列中的位置
            self._msnMutex.lock()
            if msnID in self._msnListDict:
                msnList = self._msnListDict[msnID]
                # 计算已完成的任务数
                original_length = len(msnList) + 1  # 因为已经弹出了一个任务
                completed_count = original_length - len(msnList)
                self._msnMutex.unlock()
                
                # 更新快照
                SnapshotManagerInstance.update_snapshot(msnID, completed_count - 1, msn, res, is_failed, error)
                logger.debug(f"已更新任务 {msnID} 的快照，已完成 {completed_count} 个任务")
            else:
                self._msnMutex.unlock()
                logger.warning(f"任务 {msnID} 已不存在，无法更新快照")
        except Exception as e:
            logger.error(f"更新任务 {msnID} 的快照失败: {e}", exc_info=True, stack_info=True)
            if self._msnMutex.tryLock():
                self._msnMutex.unlock()
            
    def _remove_snapshot(self, msnID):
        """移除任务快照"""
        try:
            SnapshotManagerInstance.remove_snapshot(msnID)
            logger.info(f"已移除任务 {msnID} 的快照")
        except Exception as e:
            logger.error(f"移除任务 {msnID} 的快照失败: {e}", exc_info=True, stack_info=True)
            
    def _try_recover_task(self, msnID, msnInfo, msnList, exception):
        """尝试恢复任务"""
        try:
            logger.error(f"任务 {msnID} 执行失败，尝试恢复...")
            logger.error(f"失败原因: {exception}")
            
            # 获取任务快照
            snapshot = SnapshotManagerInstance.get_snapshot(msnID)
            
            if snapshot:
                # 获取剩余任务
                remaining_tasks = snapshot.get_remaining_tasks()
                
                if remaining_tasks:
                    logger.info(f"任务 {msnID} 恢复成功，剩余 {len(remaining_tasks)} 个任务需要处理")
                    
                    # 重新添加任务队列
                    new_msnID = self.addMissionList(msnInfo, remaining_tasks)
                    
                    if new_msnID.startswith("[Error]"):
                        logger.error(f"重新添加任务队列失败: {new_msnID}")
                        msnInfo["onEnd"](msnInfo, f"[Error] Task recovery failed: {new_msnID}")
                    else:
                        logger.info(f"任务 {msnID} 已恢复，新任务ID: {new_msnID}")
                        
                        # 更新快照中的任务ID
                        SnapshotManagerInstance.remove_snapshot(msnID)
                        SnapshotManagerInstance.create_snapshot(new_msnID, msnInfo, remaining_tasks, 
                                                               snapshot.apiKey, snapshot.apiInfo)
                        
                        # 通知UI任务已恢复
                        if hasattr(self, 'callQmlInMain'):
                            self.callQmlInMain("onTaskRecovered", msnID, new_msnID, len(remaining_tasks))
                        logger.info(f"任务恢复完成，新任务 {new_msnID} 已开始执行")
                else:
                    logger.info(f"任务 {msnID} 已完成，无需恢复")
                    msnInfo["onEnd"](msnInfo, "[Success] Task completed after recovery.")
            else:
                logger.error(f"无法找到任务 {msnID} 的快照，无法恢复")
                msnInfo["onEnd"](msnInfo, f"[Error] Task recovery failed: No snapshot found.")
                
            # 清理原任务
            self._msnDictDel(msnID)
            logger.debug(f"已清理原任务 {msnID}")
            
        except Exception as e:
            logger.error(f"任务恢复过程中发生异常: {e}", exc_info=True, stack_info=True)
            msnInfo["onEnd"](msnInfo, f"[Error] Task recovery failed: {e}")

    # ========================= 【继承重载】 =========================

    def msnPreTask(self, msnInfo):  # 任务前处理，用于更新api和参数。
        """返回值可选：
        "" ：空字符串表示正常继续。
        "continue" ：跳过本次任务
        "[Error] xxxx" ：终止这条任务队列，返回异常信息
        """
        # return "[Error] No overloaded msnPreTask. \n【异常】未重载msnPreTask。"
        return ""

    def msnTask(self, msnInfo, msn):  # 执行任务msn，返回结果字典。
        logger.debug("mission 未重载 msnTask")
        return {"error": "[Error] No overloaded msnTask. \n【异常】未重载msnTask。"}

    def getStatus(self):  # 返回当前状态
        return "Mission 基类 返回空状态"
