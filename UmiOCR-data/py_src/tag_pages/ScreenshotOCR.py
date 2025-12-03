# ========================================
# =============== 截图OCR页 ===============
# ========================================

from PySide2.QtGui import QClipboard  # 截图 剪贴板
import json
import os
from datetime import datetime

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
        self.export_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "edits")
        os.makedirs(self.export_dir, exist_ok=True)

    def saveEditedResult(self, result_id, text, annotations, notes, tags):
        """
        保存编辑后的结果到JSON文件
        :param result_id: 结果ID
        :param text: 编辑后的文字
        :param annotations: 标注信息
        :param notes: 备注信息
        :param tags: 标签信息
        """
        try:
            # 创建保存目录
            os.makedirs(self.export_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"result_{result_id}_{timestamp}.json"
            json_path = os.path.join(self.export_dir, json_filename)
            
            # 准备保存的数据
            save_data = {
                "result_id": result_id,
                "text": text,
                "annotations": annotations,
                "notes": notes,
                "tags": tags,
                "save_time": timestamp,
                "version": "1.0"
            }
            
            # 保存为JSON文件
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"编辑结果已保存到: {json_path}")
            return True
        except Exception as e:
            logger.error(f"保存编辑结果失败: {e}")
            return False
    
    def exportToMarkdown(self, result_id, text, annotations, notes, tags):
        """
        导出编辑后的结果到Markdown文件
        :param result_id: 结果ID
        :param text: 编辑后的文字
        :param annotations: 标注信息
        :param notes: 备注信息
        :param tags: 标签信息
        """
        try:
            # 创建保存目录
            os.makedirs(self.export_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_filename = f"result_{result_id}_{timestamp}.md"
            md_path = os.path.join(self.export_dir, md_filename)
            
            # 生成Markdown内容
            md_content = "# OCR识别结果（编辑后）\n\n"
            
            # 添加标签
            if tags:
                md_content += "## 标签\n"
                for tag in tags:
                    md_content += f"- {tag}\n"
                md_content += "\n"
            
            # 添加备注
            if notes:
                md_content += "## 备注\n"
                md_content += f"{notes}\n\n"
            
            # 添加标注后的文字
            md_content += "## 文本内容\n\n"
            
            # 处理标注信息
            if annotations:
                # 按开始位置排序标注
                sorted_annotations = sorted(annotations, key=lambda x: x["start"])
                
                current_pos = 0
                for annotation in sorted_annotations:
                    start = annotation["start"]
                    end = annotation["end"]
                    style = annotation["style"]
                    
                    # 添加标注前的文本
                    md_content += text[current_pos:start]
                    
                    # 添加带标注的文本
                    annotated_text = text[start:end]
                    if style == "highlight":
                        md_content += f"=={annotated_text}=="
                    elif style == "underline":
                        md_content += f"<u>{annotated_text}</u>"
                    elif style == "strikethrough":
                        md_content += f"~~{annotated_text}~~"
                    else:
                        md_content += annotated_text
                    
                    current_pos = end
                
                # 添加剩余文本
                md_content += text[current_pos:]
            else:
                md_content += text
            
            # 添加保存时间
            md_content += f"\n\n---\n保存时间: {timestamp}\n"
            md_content += f"结果ID: {result_id}\n"
            
            # 保存为Markdown文件
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            logger.info(f"Markdown导出已保存到: {md_path}")
            return True
        except Exception as e:
            logger.error(f"导出Markdown失败: {e}")
            return False

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
