# ========================================
# =============== 截图OCR页 ===============
# ========================================

from PySide2.QtGui import QClipboard  # 截图 剪贴板

from umi_log import logger
from .page import Page  # 页基类
from ..image_controller.image_provider import PixmapProvider  # 图片提供器
from ..mission.mission_ocr import MissionOCR  # 任务管理器
from ..mission.mission_multi_ocr import MissionMultiOCR  # 多引擎OCR任务管理器
from ..multi_ocr_bridge import MultiOCRBridgeInstance  # 多引擎桥接
from ..event_bus.pubsub_service import PubSubService  # 发布/订阅管理器

# 只要触发了截图/粘贴/图片识图任务，并结束任务（无论是否成功），都发送 <<ScreenshotOcrEnd>> 事件。

Clipboard = QClipboard()  # 剪贴板


class ScreenshotOCR(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.msnDict = {}
        self.recentResult = []  # 缓存本轮任务的识别结果，提交给 <<ScreenshotOcrEnd>>
        self.is_multi_engine_mode = False  # 是否启用多引擎模式
        self.multi_ocr_result = None  # 多引擎OCR结果

    # ========================= 【qml调用python】 =========================

    # 对一个imgID进行OCR
    def ocrImgID(self, imgID, configDict):
        self.recentResult = []
        
        # 检查是否启用多引擎模式
        self.is_multi_engine_mode = configDict.get("multiEngineMode", False)
        
        if not imgID or not configDict:  # 截图取消
            PubSubService.publish("<<ScreenshotOcrEnd>>", [])
            return
        if imgID.startswith("["):  # 截图失败
            PubSubService.publish(
                "<<ScreenshotOcrEnd>>", [{"code": 301, "data": imgID}]
            )
            return
        
        pixmap = PixmapProvider.getPixmap(imgID)
        if not pixmap:
            logger.error(f'ScreenshotOCR: imgID "{imgID}" 不存在 PixmapProvider 中')
            return
        
        if self.is_multi_engine_mode:
            # 使用多引擎OCR
            self._msnMultiEngineImage(pixmap, imgID, configDict)
        else:
            # 使用单引擎OCR
            self._msnImage(pixmap, imgID, configDict)

    # 对一批路径进行OCR
    def ocrPaths(self, paths, configDict):
        self.recentResult = []
        
        # 检查是否启用多引擎模式
        self.is_multi_engine_mode = configDict.get("multiEngineMode", False)
        
        if self.is_multi_engine_mode:
            # 使用多引擎OCR
            self._msnMultiEnginePaths(paths, configDict)
        else:
            # 使用单引擎OCR
            self._msnPaths(paths, configDict)

    # 停止全部任务
    def msnStop(self):
        self.callQml("setMsnState", "none")
        for i in self.msnDict:
            if self.is_multi_engine_mode:
                MissionMultiOCR.stopMissionList(i)
            else:
                MissionOCR.stopMissionList(i)
        self.msnDict = {}
        PubSubService.publish("<<ScreenshotOcrEnd>>", self.recentResult)

    # ========================= 【OCR 任务控制】 =========================

    # 传入 QImage或QPixmap图片， 图片id， 配置字典。 提交单引擎OCR任务。
    def _msnImage(self, img, imgID, configDict):
        # 图片转字节，构造任务队列
        bytesData = PixmapProvider.toBytes(img)
        msnList = [{"bytes": bytesData, "imgID": imgID}]
        self._msn(msnList, configDict)

    # 传入路径列表，提交单引擎OCR任务，返回图片缓存ID
    def _msnPaths(self, paths, configDict):
        msnList = [{"path": x} for x in paths]
        self._msn(msnList, configDict)

    # 传入 QImage或QPixmap图片， 图片id， 配置字典。 提交多引擎OCR任务。
    def _msnMultiEngineImage(self, img, imgID, configDict):
        # 图片转base64
        base64_data = PixmapProvider.toBase64(img)
        
        # 使用多引擎桥接执行任务
        MultiOCRBridgeInstance.performScreenshotOCRComparison(base64_data)
        
        # 连接多引擎结果信号
        MultiOCRBridgeInstance.comparisonResultReady.connect(self._onMultiOCRResultReady)
        MultiOCRBridgeInstance.progressUpdated.connect(self._onMultiOCRProgress)
        MultiOCRBridgeInstance.messageReady.connect(self._onMultiOCRMessage)
        
        msnID = "multi_engine_screenshot_task"
        self.msnDict[msnID] = None
        self.callQml("setMsnState", "run")

    # 传入路径列表，提交多引擎OCR任务，返回图片缓存ID
    def _msnMultiEnginePaths(self, paths, configDict):
        # 使用多引擎桥接执行任务
        MultiOCRBridgeInstance.startMultiOCRComparison(paths)
        
        # 连接多引擎结果信号
        MultiOCRBridgeInstance.comparisonResultReady.connect(self._onMultiOCRResultReady)
        MultiOCRBridgeInstance.progressUpdated.connect(self._onMultiOCRProgress)
        MultiOCRBridgeInstance.messageReady.connect(self._onMultiOCRMessage)
        
        msnID = "multi_engine_paths_task"
        self.msnDict[msnID] = None
        self.callQml("setMsnState", "run")

    # 开始单引擎任务
    def _msn(self, msnList, configDict):
        # 任务信息
        msnInfo = {
            "onStart": self._onStart,
            "onReady": self._onReady,
            "onGet": self._onGet,
            "onEnd": self._onEnd,
            "argd": configDict,
        }
        msnID = MissionOCR.addMissionList(msnInfo, msnList)
        if msnID.startswith("[Error]"):  # 添加任务失败
            self._onEnd(None, f"{self.msnID}\n添加任务失败。")
        else:  # 添加成功
            self.msnDict[msnID] = None
            self.callQml("setMsnState", "run")

    def _onStart(self, msnInfo):  # 任务队列开始
        pass

    def _onReady(self, msnInfo, msn):  # 单个任务准备
        pass

    def _onGet(self, msnInfo, msn, res):  # 单个任务完成
        # 补充平均置信度
        score = 0
        num = 0
        if res["code"] == 100:
            for r in res["data"]:
                score += r["score"]
                num += 1
            if num > 0:
                score /= num
        res["score"] = score
        # 通知qml更新UI
        imgID = msn.get("imgID", "")
        imgPath = msn.get("path", "")
        self.recentResult.append(res)  # 记录结果
        self.callQmlInMain("onOcrGet", res, imgID, imgPath)  # 在主线程中调用qml
    
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

    def _onEnd(self, msnInfo, msg):  # 任务队列完成或失败
        if self.is_multi_engine_mode:
            # 多引擎模式下的结束处理
            self._onMultiOCREnd(msnInfo, msg)
        else:
            # 单引擎模式下的结束处理
            self._onSingleOCREnd(msnInfo, msg)
    
    def _onSingleOCREnd(self, msnInfo, msg):
        """单引擎OCR任务结束处理"""
        # msg: [Success] [Warning] [Error]
        PubSubService.publish("<<ScreenshotOcrEnd>>", self.recentResult)

        def update():
            # 清除任务id
            if msnInfo and msnInfo["msnID"] in self.msnDict:
                del self.msnDict[msnInfo["msnID"]]
            # 所有任务都完成了
            if not self.msnDict:
                # 停止前端显示
                self.callQml("setMsnState", "none")
            self.callQml("onOcrEnd", msg)

        self.callFunc(update)  # 在主线程中执行
    
    def _onMultiOCREnd(self, msnInfo, msg):
        """多引擎OCR任务结束处理"""
        # 断开多引擎信号连接
        MultiOCRBridgeInstance.comparisonResultReady.disconnect(self._onMultiOCRResultReady)
        MultiOCRBridgeInstance.progressUpdated.disconnect(self._onMultiOCRProgress)
        MultiOCRBridgeInstance.messageReady.disconnect(self._onMultiOCRMessage)
        
        # 发布多引擎结果
        multi_result = {}
        if self.multi_ocr_result:
            multi_result = {
                "code": 100,
                "data": self.multi_ocr_result,
                "best_result": MultiOCRBridgeInstance.getBestResult()
            }
        
        PubSubService.publish("<<ScreenshotOcrEnd>>", [multi_result])

        def update():
            # 清除任务id
            if msnInfo and msnInfo["msnID"] in self.msnDict:
                del self.msnDict[msnInfo["msnID"]]
            # 所有任务都完成了
            if not self.msnDict:
                # 停止前端显示
                self.callQml("setMsnState", "none")
            self.callQml("onOcrEnd", msg)

        self.callFunc(update)  # 在主线程中执行
    
    def _onMultiOCRResultReady(self, result):
        """多引擎OCR结果准备就绪"""
        self.multi_ocr_result = result
        
        # 通知前端显示多引擎对比结果
        self.callQmlInMain("onMultiOCRResultReady", result)
        
        # 将最佳结果添加到最近结果中
        best_result = {
            "code": 100,
            "data": result.get('best_result', {}).get('text', ''),
            "score": result.get('statistics', {}).get('average_confidence', 0),
            "multi_ocr_result": result
        }
        self.recentResult.append(best_result)
    
    def _onMultiOCRProgress(self, current, total, status):
        """多引擎OCR进度更新"""
        self.callQmlInMain("onMultiOCRProgress", current, total, status)
    
    def _onMultiOCRMessage(self, message):
        """多引擎OCR消息通知"""
        self.callQmlInMain("onMultiOCRMessage", message)
