# ========================================
# =============== 截图OCR页 ===============
# ========================================

from PySide2.QtGui import QClipboard  # 截图 剪贴板

from umi_log import logger
from .page import Page  # 页基类
from ..image_controller.image_provider import PixmapProvider  # 图片提供器
from ..mission.mission_ocr import MissionOCR  # 任务管理器
from ..event_bus.pubsub_service import PubSubService  # 发布/订阅管理器

# 只要触发了截图/粘贴/图片识图任务，并结束任务（无论是否成功），都发送 <<ScreenshotOcrEnd>> 事件。

Clipboard = QClipboard()  # 剪贴板


class ScreenshotOCR(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.msnDict = {}
        self.recentResult = []  # 缓存本轮任务的识别结果，提交给 <<ScreenshotOcrEnd>>

    # ========================= 【qml调用python】 =========================

    # 对一个imgID进行OCR
    def ocrImgID(self, imgID, configDict):
        self.recentResult = []
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
        self._msnImage(pixmap, imgID, configDict)  # 开始OCR

    # 对一批路径进行OCR
    def ocrPaths(self, paths, configDict):
        self.recentResult = []
        self._msnPaths(paths, configDict)

    # 停止全部任务
    def msnStop(self):
        self.callQml("setMsnState", "none")
        for i in self.msnDict:
            MissionOCR.stopMissionList(i)
        self.msnDict = {}
        PubSubService.publish("<<ScreenshotOcrEnd>>", self.recentResult)

    # ========================= 【OCR 任务控制】 =========================

    # 传入 QImage或QPixmap图片， 图片id， 配置字典。 提交OCR任务。
    def _msnImage(self, img, imgID, configDict):
        # 图片转字节，构造任务队列
        bytesData = PixmapProvider.toBytes(img)
        msnList = [{"bytes": bytesData, "imgID": imgID}]
        self._msn(msnList, configDict)

    # 传入路径列表，提交OCR任务，返回图片缓存ID
    def _msnPaths(self, paths, configDict):
        msnList = [{"path": x} for x in paths]
        self._msn(msnList, configDict)

    # 开始任务
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
        # 保存识别记录
        self.saveOCRRecord(res)
        # 通知qml更新UI
        imgID = msn.get("imgID", "")
        imgPath = msn.get("path", "")
        self.recentResult.append(res)  # 记录结果
        self.callQmlInMain("onOcrGet", res, imgID, imgPath)  # 在主线程中调用qml

    def _onEnd(self, msnInfo, msg):  # 任务队列完成或失败
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

    def saveOCRRecord(self, record):
        """保存OCR识别记录"""
        try:
            import os
            import json
            from datetime import datetime
            # 确保记录目录存在
            records_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "records")
            if not os.path.exists(records_dir):
                os.makedirs(records_dir)
            # 获取今天的日期作为文件名
            today = datetime.date.today().isoformat()
            file_path = os.path.join(records_dir, f"{today}.json")
            # 添加时间戳
            record["timestamp"] = datetime.datetime.now().isoformat()
            # 读取现有记录
            records = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception as e:
                    logger.error(f"读取记录文件 {file_path} 失败: {e}")
                    records = []
            # 添加新记录
            records.append(record)
            # 保存记录
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存OCR记录失败: {e}")
