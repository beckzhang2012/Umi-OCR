# ========================================
# =============== 批量OCR页 ===============
# ========================================

import os
import time

from umi_log import logger
from .page import Page  # 页基类
from ..mission.mission_ocr import MissionOCR  # 任务管理器
from ..mission.mission_multi_ocr import MissionMultiOCR  # 多引擎OCR任务管理器
from ..multi_ocr_bridge import MultiOCRBridgeInstance  # 多引擎桥接
from ..utils.utils import allowedFileName
from ..ocr.output import Output  # 输出器


class BatchOCR(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.argd = None
        self.msnID = ""
        self.outputList = []  # 输出器列表
        self.is_multi_engine_mode = False  # 是否启用多引擎模式
        self.multi_ocr_result = None  # 多引擎OCR结果

    # ========================= 【qml调用python】 =========================

    def msnPaths(self, paths, argd):  # 接收路径列表和配置参数字典，开始OCR任务
        # 检查是否启用多引擎模式
        self.is_multi_engine_mode = argd.get("mission.multiEngineMode", False)
        
        if self.is_multi_engine_mode:
            # 使用多引擎OCR
            return self._msnMultiEnginePaths(paths, argd)
        else:
            # 使用单引擎OCR
            return self._msnSingleEnginePaths(paths, argd)
    
    def _msnSingleEnginePaths(self, paths, argd):
        """单引擎OCR任务处理"""
        # 任务信息
        msnInfo = {
            "onStart": self._onStart,
            "onReady": self._onReady,
            "onGet": self._onGet,
            "onEnd": self._onEnd,
            "argd": argd,
        }
        # 预处理参数字典
        if not self._preprocessArgd(argd, paths[0]):
            return ""
        # 构造输出器
        if not self._initOutputList(argd):
            return ""
        # 路径转为任务列表格式，加载进任务管理器
        msnList = [{"path": x} for x in paths]
        self.msnID = MissionOCR.addMissionList(msnInfo, msnList)
        if self.msnID.startswith("[Error]"):  # 添加任务失败
            self._onEnd(None, f"{self.msnID}\n添加任务失败。")
        else:  # 添加成功，通知前端刷新UI
            logger.debug(f"添加单引擎任务成功 {self.msnID}")
        return self.msnID
    
    def _msnMultiEnginePaths(self, paths, argd):
        """多引擎OCR任务处理"""
        # 预处理参数字典
        if not self._preprocessArgd(argd, paths[0]):
            return ""
        
        # 使用多引擎桥接执行任务
        MultiOCRBridgeInstance.startMultiOCRComparison(paths, argd["mission.dir"])
        
        # 连接多引擎结果信号
        MultiOCRBridgeInstance.comparisonResultReady.connect(self._onMultiOCRResultReady)
        MultiOCRBridgeInstance.progressUpdated.connect(self._onMultiOCRProgress)
        MultiOCRBridgeInstance.messageReady.connect(self._onMultiOCRMessage)
        
        self.msnID = "multi_engine_task"
        logger.debug("添加多引擎任务成功")
        return self.msnID

    def _preprocessArgd(self, argd, path0):  # 预处理参数字典，无异常返回True
        self.argd = None
        if argd["mission.dirType"] == "source":  # 若保存到原目录
            # 则保存路径设为第1张图片的目录
            argd["mission.dir"] = os.path.dirname(path0)
        else:  # 若保存到用户指定目录
            d = os.path.abspath(argd["mission.dir"])  # 转绝对地址
            if not os.path.exists(d):  # 检查地址是否存在
                try:  # 不存在，尝试创建地址
                    os.makedirs(d)
                except OSError:  # 创建地址失败，报错
                    logger.warning(f"批量OCR无法创建目录： {d}", exc_info=True)
                    self._onEnd(
                        None,
                        f'[Error] Failed to create directory: "{d}"\n【异常】无法创建目录。',
                    )
                    return False
            argd["mission.dir"] = d  # 写回字典
        startTimestamp = time.time()  # 开始时间戳
        argd["startTimestamp"] = startTimestamp
        # 格式化日期时间（标准格式）
        argd["startDatetime"] = time.strftime(
            r"%Y-%m-%d %H:%M:%S", time.localtime(startTimestamp)
        )
        # 添加格式化日期时间（用户指定格式）：先替换时间戳，再strftime
        startDatetimeUser = argd["mission.datetimeFormat"].replace(
            r"%unix", str(startTimestamp)
        )
        startDatetimeUser = time.strftime(
            startDatetimeUser, time.localtime(startTimestamp)
        )
        # 处理文件名
        fileName = argd["mission.fileNameFormat"]
        fileName = fileName.replace(r"%date", startDatetimeUser)  # 替换时间
        fileNameEle = os.path.basename(os.path.dirname(path0))
        fileName = fileName.replace("%name", fileNameEle)  # 替换名称元素
        if not allowedFileName(fileName):  # 文件名不合法
            self._onEnd(
                None,
                f'[Error] The file name is illegal.\n【错误】文件名【{fileName}】含有不允许的字符。\n不允许含有下列字符： \  /  :  *  ?  "  <  >  |',
            )
            return False
        argd["mission.fileName"] = fileName  # 回填文件名
        self.argd = argd
        return True

    def _initOutputList(self, argd):  # 初始化输出器列表，无异常返回True
        self.outputList = []
        outputArgd = {  # 数据转换，封装有需要的值
            "outputDir": argd["mission.dir"],  # 输出目录
            # 输出目录类型，"source" 为原文件目录
            "outputDirType": argd["mission.dirType"],
            "outputFileName": argd["mission.fileName"],  # 输出文件名（前缀）
            "startDatetime": argd["startDatetime"],  # 开始日期
            "ignoreBlank": argd["mission.ignoreBlank"],  # 忽略空白文件
        }
        try:
            for key in argd.keys():
                if "mission.filesType" in key and argd[key]:
                    self.outputList.append(Output[key[18:]](outputArgd))
        except Exception as e:
            self._onEnd(
                None,
                f"[Error] Failed to initialize output file.\n【错误】初始化输出文件失败。\n{e}",
            )
            return False
        return True

    def msnStop(self):  # 任务停止
        if self.is_multi_engine_mode:
            MissionMultiOCR.stopMissionList(self.msnID)
        else:
            MissionOCR.stopMissionList(self.msnID)

    def msnPause(self):  # 任务暂停
        if self.is_multi_engine_mode:
            MissionMultiOCR.pauseMissionList(self.msnID)
        else:
            MissionOCR.pauseMissionList(self.msnID)

    def msnResume(self):  # 任务恢复
        if self.is_multi_engine_mode:
            MissionMultiOCR.resumeMissionList(self.msnID)
        else:
            MissionOCR.resumeMissionList(self.msnID)

    def msnPreview(self, path, argd):  # 快速进行一次任务，主要用于预览
        msnInfo = {
            "onGet": self._onPreview,
            "argd": argd,
        }
        msnList = [{"path": path}]
        self.msnID = MissionOCR.addMissionList(msnInfo, msnList)

    # ========================= 【任务控制器的异步回调】 =========================

    def _onStart(self, msnInfo):  # 任务队列开始
        pass

    def _onReady(self, msnInfo, msn):  # 单个任务准备
        msnID = msnInfo["msnID"]
        if msnID != self.msnID:
            logger.warning(f"_onReady 任务ID未在记录。{msnID}")
            return
        self.callQmlInMain("onOcrReady", msn["path"])

    def _onGet(self, msnInfo, msn, res):  # 单个任务完成
        msnID = msnInfo["msnID"]
        if msnID != self.msnID:
            logger.warning(f"_onGet 任务ID未在记录。{msnID}")
            return
        # 补充参数
        res["fileName"] = os.path.basename(msn["path"])
        res["dir"] = os.path.dirname(msn["path"])
        # 输出器输出
        for o in self.outputList:
            try:
                o.print(res)
            except Exception:
                logger.error(f"结果输出失败：{o}", exc_info=True, stack_info=True)
        # 通知qml更新UI
        self.callQmlInMain("onOcrGet", msn["path"], res)  # 在主线程中调用qml

    def _onEnd(self, msnInfo, msg):  # 任务队列完成或失败
        if self.is_multi_engine_mode:
            # 多引擎模式下的结束处理
            self._onMultiOCREnd(msnInfo, msg)
        else:
            # 单引擎模式下的结束处理
            self._onSingleOCREnd(msnInfo, msg)
    
    def _onSingleOCREnd(self, msnInfo, msg):
        """单引擎OCR任务结束处理"""
        if msnInfo:
            msnID = msnInfo["msnID"]
            if msnID != self.msnID:
                logger.warning(f"_onSingleOCREnd 任务ID未在记录。{msnID}")
                return
        else:
            msnID = ""
        # 结束输出器，保存文件。
        for o in self.outputList:
            try:
                o.onEnd()
            except Exception as e:
                msg = f"[Error] 输出器异常：{e}" + msg
        # msg: [Success] [Warning] [Error]
        self.callQmlInMain("onOcrEnd", msg, msnID)
    
    def _onMultiOCREnd(self, msnInfo, msg):
        """多引擎OCR任务结束处理"""
        # 断开多引擎信号连接
        MultiOCRBridgeInstance.comparisonResultReady.disconnect(self._onMultiOCRResultReady)
        MultiOCRBridgeInstance.progressUpdated.disconnect(self._onMultiOCRProgress)
        MultiOCRBridgeInstance.messageReady.disconnect(self._onMultiOCRMessage)
        
        # 通知前端任务结束
        self.callQmlInMain("onOcrEnd", msg, self.msnID)
    
    def _onMultiOCRResultReady(self, result):
        """多引擎OCR结果准备就绪"""
        self.multi_ocr_result = result
        
        # 通知前端显示多引擎对比结果
        self.callQmlInMain("onMultiOCRResultReady", result)
        
        # 如果需要，输出多引擎对比报告
        if self.argd.get("mission.exportComparisonReport", False):
            report_format = self.argd.get("mission.comparisonReportFormat", "json")
            report_path = os.path.join(
                self.argd["mission.dir"],
                f"{self.argd['mission.fileName']}_comparison_report.{report_format}"
            )
            MultiOCRBridgeInstance.generateComparisonReport(report_path, report_format)
    
    def _onMultiOCRProgress(self, current, total, status):
        """多引擎OCR进度更新"""
        self.callQmlInMain("onMultiOCRProgress", current, total, status)
    
    def _onMultiOCRMessage(self, message):
        """多引擎OCR消息通知"""
        self.callQmlInMain("onMultiOCRMessage", message)

    def _onPreview(self, msnInfo, msn, res):
        self.callQmlInMain("onPreview", msn["path"], res)
    
    # ========================= 【多引擎相关方法】 =========================
    
    def getMultiOCRResult(self):
        """获取多引擎OCR结果"""
        return self.multi_ocr_result
    
    def getBestResult(self):
        """获取最佳结果"""
        if not self.multi_ocr_result:
            return ""
        return MultiOCRBridgeInstance.getBestResult()
    
    def exportComparisonReport(self, report_path, report_format="json"):
        """导出对比报告"""
        MultiOCRBridgeInstance.generateComparisonReport(report_path, report_format)
    
    def setMultiEngineMode(self, enabled):
        """设置多引擎模式"""
        self.is_multi_engine_mode = enabled
        MultiOCRBridgeInstance.setMultiEngineMode(enabled)
    
    def selectEngines(self, engines):
        """选择OCR引擎"""
        MultiOCRBridgeInstance.selectEngines(engines)
    
    def selectProfile(self, profile_name):
        """选择多引擎方案"""
        MultiOCRBridgeInstance.selectProfile(profile_name)
    
    def setComparisonStrategy(self, strategy):
        """设置对比策略"""
        MultiOCRBridgeInstance.setComparisonStrategy(strategy)
