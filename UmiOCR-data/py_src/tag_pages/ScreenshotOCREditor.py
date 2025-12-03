# ======================================== 
# =============== 截图OCR编辑器 =============== 
# ======================================== 

import json 
import os 
from datetime import datetime 

from umi_log import logger 
from .ScreenshotOCR import ScreenshotOCR  # 继承截图OCR类 

class ScreenshotOCREditor(ScreenshotOCR): 
    def __init__(self, *args): 
        super().__init__(*args) 
        self.editHistory = []  # 编辑历史，用于撤销/重做 
        self.historyIndex = -1  # 当前历史记录索引 
        self.editedResults = {}  # 已编辑的结果，key: 结果ID，value: 编辑后的结果数据 
        
        # 初始化编辑数据存储目录 
        self.editDataDir = os.path.join(os.path.dirname(__file__), "..", "..", "edit_data") 
        if not os.path.exists(self.editDataDir): 
            os.makedirs(self.editDataDir) 
    
    # ========================= 【编辑功能】 ========================= 
    
    # 进入编辑模式 
    def enterEditMode(self, resultId): 
        logger.info(f"进入编辑模式，结果ID: {resultId}") 
        # 加载已有的编辑数据 
        self.loadEditData(resultId) 
        # 通知QML进入编辑模式 
        self.callQmlInMain("enterEditMode", resultId) 
    
    # 退出编辑模式 
    def exitEditMode(self, resultId, saveChanges=True): 
        logger.info(f"退出编辑模式，结果ID: {resultId}") 
        if saveChanges: 
            self.saveEditData(resultId) 
        # 通知QML退出编辑模式 
        self.callQmlInMain("exitEditMode", resultId) 
    
    # 编辑文字内容 
    def editText(self, resultId, newText): 
        if resultId not in self.editedResults: 
            self.editedResults[resultId] = self.getResultData(resultId) 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 更新文字内容 
        self.editedResults[resultId]["text"] = newText 
        self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
        
        # 通知QML更新文字 
        self.callQmlInMain("updateText", resultId, newText) 
    
    # 添加标注 
    def addAnnotation(self, resultId, annotationType, startIndex, endIndex, color="yellow"): 
        """ 
        添加标注 
        :param resultId: 结果ID 
        :param annotationType: 标注类型 (highlight, underline, strikethrough) 
        :param startIndex: 起始索引 
        :param endIndex: 结束索引 
        :param color: 颜色 (仅对高亮有效) 
        """ 
        if resultId not in self.editedResults: 
            self.editedResults[resultId] = self.getResultData(resultId) 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 确保annotations数组存在 
        if "annotations" not in self.editedResults[resultId]: 
            self.editedResults[resultId]["annotations"] = [] 
        
        # 添加标注 
        annotation = { 
            "type": annotationType, 
            "start": startIndex, 
            "end": endIndex, 
            "color": color, 
            "id": f"annotation_{len(self.editedResults[resultId]['annotations'])}" 
        } 
        self.editedResults[resultId]["annotations"].append(annotation) 
        self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
        
        # 通知QML更新标注 
        self.callQmlInMain("updateAnnotations", resultId, self.editedResults[resultId]["annotations"]) 
    
    # 删除标注 
    def deleteAnnotation(self, resultId, annotationId): 
        if resultId not in self.editedResults or "annotations" not in self.editedResults[resultId]: 
            return 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 删除标注 
        self.editedResults[resultId]["annotations"] = [ 
            ann for ann in self.editedResults[resultId]["annotations"] 
            if ann["id"] != annotationId 
        ] 
        self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
        
        # 通知QML更新标注 
        self.callQmlInMain("updateAnnotations", resultId, self.editedResults[resultId]["annotations"]) 
    
    # 添加备注 
    def addNote(self, resultId, note): 
        if resultId not in self.editedResults: 
            self.editedResults[resultId] = self.getResultData(resultId) 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 更新备注 
        self.editedResults[resultId]["note"] = note 
        self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
        
        # 通知QML更新备注 
        self.callQmlInMain("updateNote", resultId, note) 
    
    # 添加标签 
    def addTag(self, resultId, tag): 
        if resultId not in self.editedResults: 
            self.editedResults[resultId] = self.getResultData(resultId) 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 确保tags数组存在 
        if "tags" not in self.editedResults[resultId]: 
            self.editedResults[resultId]["tags"] = [] 
        
        # 添加标签（避免重复） 
        if tag not in self.editedResults[resultId]["tags"]: 
            self.editedResults[resultId]["tags"].append(tag) 
            self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
            
            # 通知QML更新标签 
            self.callQmlInMain("updateTags", resultId, self.editedResults[resultId]["tags"]) 
    
    # 删除标签 
    def deleteTag(self, resultId, tag): 
        if resultId not in self.editedResults or "tags" not in self.editedResults[resultId]: 
            return 
        
        # 保存到历史记录 
        self.saveToHistory(resultId) 
        
        # 删除标签 
        if tag in self.editedResults[resultId]["tags"]: 
            self.editedResults[resultId]["tags"].remove(tag) 
            self.editedResults[resultId]["edit_time"] = datetime.now().isoformat() 
            
            # 通知QML更新标签 
            self.callQmlInMain("updateTags", resultId, self.editedResults[resultId]["tags"]) 
    
    # ========================= 【撤销/重做】 ========================= 
    
    # 保存到历史记录 
    def saveToHistory(self, resultId): 
        if resultId not in self.editedResults: 
            return 
        
        # 移除当前索引之后的所有历史记录 
        if self.historyIndex < len(self.editHistory) - 1: 
            self.editHistory = self.editHistory[:self.historyIndex + 1] 
        
        # 保存当前状态到历史记录 
        self.editHistory.append({ 
            "resultId": resultId, 
            "data": json.dumps(self.editedResults[resultId]) 
        }) 
        
        # 限制历史记录数量（最多50条） 
        if len(self.editHistory) > 50: 
            self.editHistory.pop(0) 
        
        self.historyIndex = len(self.editHistory) - 1 
    
    # 撤销 
    def undo(self): 
        if self.historyIndex <= 0: 
            return  # 没有可撤销的操作 
        
        self.historyIndex -= 1 
        historyItem = self.editHistory[self.historyIndex] 
        
        # 恢复历史状态 
        self.editedResults[historyItem["resultId"]] = json.loads(historyItem["data"]) 
        
        # 通知QML更新所有数据 
        self.updateAllData(historyItem["resultId"]) 
    
    # 重做 
    def redo(self): 
        if self.historyIndex >= len(self.editHistory) - 1: 
            return  # 没有可重做的操作 
        
        self.historyIndex += 1 
        historyItem = self.editHistory[self.historyIndex] 
        
        # 恢复历史状态 
        self.editedResults[historyItem["resultId"]] = json.loads(historyItem["data"]) 
        
        # 通知QML更新所有数据 
        self.updateAllData(historyItem["resultId"]) 
    
    # ========================= 【数据管理】 ========================= 
    
    # 获取结果数据 
    def getResultData(self, resultId): 
        # 这里需要根据实际情况从结果列表中获取数据 
        # 暂时返回一个默认的结构 
        return { 
            "id": resultId, 
            "text": "", 
            "annotations": [], 
            "note": "", 
            "tags": [], 
            "create_time": datetime.now().isoformat(), 
            "edit_time": datetime.now().isoformat() 
        } 
    
    # 加载编辑数据 
    def loadEditData(self, resultId): 
        dataFile = os.path.join(self.editDataDir, f"{resultId}.json") 
        if os.path.exists(dataFile): 
            try: 
                with open(dataFile, "r", encoding="utf-8") as f: 
                    self.editedResults[resultId] = json.load(f) 
                logger.info(f"已加载编辑数据: {resultId}") 
            except Exception as e: 
                logger.error(f"加载编辑数据失败: {resultId}, {str(e)}") 
    
    # 保存编辑数据 
    def saveEditData(self, resultId): 
        if resultId not in self.editedResults: 
            return 
        
        dataFile = os.path.join(self.editDataDir, f"{resultId}.json") 
        try: 
            with open(dataFile, "w", encoding="utf-8") as f: 
                json.dump(self.editedResults[resultId], f, ensure_ascii=False, indent=2) 
            logger.info(f"已保存编辑数据: {resultId}") 
        except Exception as e: 
            logger.error(f"保存编辑数据失败: {resultId}, {str(e)}") 
    
    # 导出结果为Markdown格式 
    def exportToMarkdown(self, resultId): 
        if resultId not in self.editedResults: 
            return "" 
        
        resultData = self.editedResults[resultId] 
        markdown = f"# 截图OCR结果\n\n" 
        
        # 基本信息 
        markdown += f"**创建时间:** {resultData['create_time']}\n" 
        markdown += f"**编辑时间:** {resultData['edit_time']}\n\n" 
        
        # 标签 
        if resultData.get('tags'): 
            markdown += f"**标签:** {', '.join(resultData['tags'])}\n\n" 
        
        # 备注 
        if resultData.get('note'): 
            markdown += f"**备注:** {resultData['note']}\n\n" 
        
        # 识别文字（带标注） 
        markdown += f"**识别文字:**\n\n" 
        text = resultData['text'] 
        
        if resultData.get('annotations'): 
            # 按标注结束位置排序，避免重叠问题 
            annotations = sorted(resultData['annotations'], key=lambda x: x['end'], reverse=True) 
            
            for ann in annotations: 
                start = ann['start'] 
                end = ann['end'] 
                
                if end > len(text): 
                    end = len(text) 
                if start < 0: 
                    start = 0 
                if start >= end: 
                    continue 
                
                # 根据标注类型添加Markdown格式 
                if ann['type'] == 'highlight': 
                    # 高亮使用 ==text== 格式（Obsidian兼容） 
                    formatted_text = f"=={text[start:end]}==" 
                elif ann['type'] == 'underline': 
                    # 下划线使用 <u>text</u> 格式 
                    formatted_text = f"<u>{text[start:end]}</u>" 
                elif ann['type'] == 'strikethrough': 
                    # 删除线使用 ~~text~~ 格式 
                    formatted_text = f"~~{text[start:end]}~~" 
                else: 
                    formatted_text = text[start:end] 
                
                # 替换原始文字中的对应部分 
                text = text[:start] + formatted_text + text[end:] 
        
        markdown += f"{text}\n" 
        
        return markdown 
    
    # 通知QML更新所有数据 
    def updateAllData(self, resultId): 
        if resultId not in self.editedResults: 
            return 
        
        resultData = self.editedResults[resultId] 
        
        # 更新文字 
        self.callQmlInMain("updateText", resultId, resultData.get("text", "")) 
        
        # 更新标注 
        self.callQmlInMain("updateAnnotations", resultId, resultData.get("annotations", [])) 
        
        # 更新备注 
        self.callQmlInMain("updateNote", resultId, resultData.get("note", "")) 
        
        # 更新标签 
        self.callQmlInMain("updateTags", resultId, resultData.get("tags", []))