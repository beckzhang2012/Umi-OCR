# =============================================
# =============== 编辑管理器 ===============
# =============================================

import json
import os
import uuid
from collections import deque
from umi_log import logger

class EditManager:
    def __init__(self, page_name="ScreenshotOCR"):
        self.page_name = page_name
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "edit_data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.data_path = os.path.join(self.data_dir, f"{page_name}_edits.json")
        
        # 编辑历史记录，用于撤销重做
        self.history_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)
        
        # 当前编辑的记录ID
        self.current_record_id = None
        
        # 加载已保存的编辑数据
        self.load_data()
        
    def load_data(self):
        """加载已保存的编辑数据"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self.edit_data = json.load(f)
            else:
                self.edit_data = {}
        except Exception as e:
            logger.error(f"加载编辑数据失败: {e}")
            self.edit_data = {}
            
    def save_data(self):
        """保存编辑数据到文件"""
        try:
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.edit_data, f, ensure_ascii=False, indent=2)
            return {"success": True, "msg": "保存成功"}
        except Exception as e:
            logger.error(f"保存编辑数据失败: {e}")
            return {"success": False, "msg": str(e)}
            
    def create_new_record(self, ocr_result):
        """为新的OCR结果创建编辑记录"""
        record_id = str(uuid.uuid4())
        
        # 初始化编辑记录
        edit_record = {
            "id": record_id,
            "origin_result": ocr_result,
            "edited_text": self._get_full_text(ocr_result),
            "annotations": [],
            "notes": "",
            "tags": [],
            "create_time": ocr_result.get("time", 0),
            "update_time": ocr_result.get("time", 0)
        }
        
        self.edit_data[record_id] = edit_record
        self.current_record_id = record_id
        self.save_data()
        
        # 记录到历史栈
        self.history_stack.append({
            "action": "create",
            "record_id": record_id,
            "before": None,
            "after": edit_record.copy()
        })
        self.redo_stack.clear()
        
        return {"success": True, "data": edit_record}
        
    def _get_full_text(self, ocr_result):
        """从OCR结果中提取完整文本"""
        if ocr_result.get("code") != 100:
            return ""
        full_text = ""
        for line in ocr_result.get("data", []):
            full_text += line.get("text", "") + "\n"
        return full_text.strip()
        
    def update_edited_text(self, record_id, new_text):
        """更新编辑后的文本"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        # 保存历史状态
        self.history_stack.append({
            "action": "edit_text",
            "record_id": record_id,
            "before": self.edit_data[record_id]["edited_text"],
            "after": new_text
        })
        self.redo_stack.clear()
        
        self.edit_data[record_id]["edited_text"] = new_text
        self.edit_data[record_id]["update_time"] = self._get_current_time()
        
        return self.save_data()
        
    def add_annotation(self, record_id, annotation):
        """添加标注"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        annotation["id"] = str(uuid.uuid4())
        annotation["create_time"] = self._get_current_time()
        
        # 保存历史状态
        self.history_stack.append({
            "action": "add_annotation",
            "record_id": record_id,
            "before": None,
            "after": annotation.copy()
        })
        self.redo_stack.clear()
        
        self.edit_data[record_id]["annotations"].append(annotation)
        self.edit_data[record_id]["update_time"] = self._get_current_time()
        
        return self.save_data()
        
    def update_annotation(self, record_id, annotation_id, new_annotation):
        """更新标注"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        annotations = self.edit_data[record_id]["annotations"]
        for i, ann in enumerate(annotations):
            if ann["id"] == annotation_id:
                # 保存历史状态
                self.history_stack.append({
                    "action": "update_annotation",
                    "record_id": record_id,
                    "before": ann.copy(),
                    "after": new_annotation.copy()
                })
                self.redo_stack.clear()
                
                annotations[i] = new_annotation
                self.edit_data[record_id]["update_time"] = self._get_current_time()
                return self.save_data()
                
        return {"success": False, "msg": "标注不存在"}
        
    def delete_annotation(self, record_id, annotation_id):
        """删除标注"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        annotations = self.edit_data[record_id]["annotations"]
        for i, ann in enumerate(annotations):
            if ann["id"] == annotation_id:
                # 保存历史状态
                self.history_stack.append({
                    "action": "delete_annotation",
                    "record_id": record_id,
                    "before": ann.copy(),
                    "after": None
                })
                self.redo_stack.clear()
                
                del annotations[i]
                self.edit_data[record_id]["update_time"] = self._get_current_time()
                return self.save_data()
                
        return {"success": False, "msg": "标注不存在"}
        
    def update_notes(self, record_id, notes):
        """更新备注"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        # 保存历史状态
        self.history_stack.append({
            "action": "update_notes",
            "record_id": record_id,
            "before": self.edit_data[record_id]["notes"],
            "after": notes
        })
        self.redo_stack.clear()
        
        self.edit_data[record_id]["notes"] = notes
        self.edit_data[record_id]["update_time"] = self._get_current_time()
        
        return self.save_data()
        
    def add_tag(self, record_id, tag):
        """添加标签"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        if tag not in self.edit_data[record_id]["tags"]:
            # 保存历史状态
            self.history_stack.append({
                "action": "add_tag",
                "record_id": record_id,
                "before": None,
                "after": tag
            })
            self.redo_stack.clear()
            
            self.edit_data[record_id]["tags"].append(tag)
            self.edit_data[record_id]["update_time"] = self._get_current_time()
            
        return self.save_data()
        
    def remove_tag(self, record_id, tag):
        """移除标签"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        if tag in self.edit_data[record_id]["tags"]:
            # 保存历史状态
            self.history_stack.append({
                "action": "remove_tag",
                "record_id": record_id,
                "before": tag,
                "after": None
            })
            self.redo_stack.clear()
            
            self.edit_data[record_id]["tags"].remove(tag)
            self.edit_data[record_id]["update_time"] = self._get_current_time()
            
        return self.save_data()
        
    def undo(self):
        """撤销上一步操作"""
        if not self.history_stack:
            return {"success": False, "msg": "没有可撤销的操作"}
            
        action = self.history_stack.pop()
        record_id = action["record_id"]
        
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        record = self.edit_data[record_id]
        
        if action["action"] == "edit_text":
            record["edited_text"] = action["before"]
        elif action["action"] == "add_annotation":
            for i, ann in enumerate(record["annotations"]):
                if ann["id"] == action["after"]["id"]:
                    del record["annotations"][i]
                    break
        elif action["action"] == "update_annotation":
            for i, ann in enumerate(record["annotations"]):
                if ann["id"] == action["after"]["id"]:
                    record["annotations"][i] = action["before"]
                    break
        elif action["action"] == "delete_annotation":
            record["annotations"].append(action["before"])
        elif action["action"] == "update_notes":
            record["notes"] = action["before"]
        elif action["action"] == "add_tag":
            if action["after"] in record["tags"]:
                record["tags"].remove(action["after"])
        elif action["action"] == "remove_tag":
            record["tags"].append(action["before"])
            
        self.redo_stack.append(action)
        record["update_time"] = self._get_current_time()
        
        return self.save_data()
        
    def redo(self):
        """重做上一步撤销的操作"""
        if not self.redo_stack:
            return {"success": False, "msg": "没有可重做的操作"}
            
        action = self.redo_stack.pop()
        record_id = action["record_id"]
        
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        record = self.edit_data[record_id]
        
        if action["action"] == "edit_text":
            record["edited_text"] = action["after"]
        elif action["action"] == "add_annotation":
            record["annotations"].append(action["after"])
        elif action["action"] == "update_annotation":
            for i, ann in enumerate(record["annotations"]):
                if ann["id"] == action["after"]["id"]:
                    record["annotations"][i] = action["after"]
                    break
        elif action["action"] == "delete_annotation":
            for i, ann in enumerate(record["annotations"]):
                if ann["id"] == action["before"]["id"]:
                    del record["annotations"][i]
                    break
        elif action["action"] == "update_notes":
            record["notes"] = action["after"]
        elif action["action"] == "add_tag":
            if action["after"] not in record["tags"]:
                record["tags"].append(action["after"])
        elif action["action"] == "remove_tag":
            if action["before"] in record["tags"]:
                record["tags"].remove(action["before"])
                
        self.history_stack.append(action)
        record["update_time"] = self._get_current_time()
        
        return self.save_data()
        
    def get_record(self, record_id):
        """获取指定ID的编辑记录"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
        return {"success": True, "data": self.edit_data[record_id]}
        
    def get_all_records(self):
        """获取所有编辑记录"""
        return {"success": True, "data": list(self.edit_data.values())}
        
    def delete_record(self, record_id):
        """删除编辑记录"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        del self.edit_data[record_id]
        
        # 清除历史栈中相关的操作
        new_history = deque()
        for action in self.history_stack:
            if action["record_id"] != record_id:
                new_history.append(action)
        self.history_stack = new_history
        
        new_redo = deque()
        for action in self.redo_stack:
            if action["record_id"] != record_id:
                new_redo.append(action)
        self.redo_stack = new_redo
        
        if self.current_record_id == record_id:
            self.current_record_id = None
            
        return self.save_data()
        
    def export_as_markdown(self, record_id):
        """导出为Markdown格式"""
        if record_id not in self.edit_data:
            return {"success": False, "msg": "记录不存在"}
            
        record = self.edit_data[record_id]
        md_content = f"# OCR识别结果\n\n"
        
        if record["tags"]:
            md_content += f"**标签**: {', '.join(record['tags'])}\n\n"
            
        if record["notes"]:
            md_content += f"**备注**: {record['notes']}\n\n"
            
        md_content += "---\n\n"
        md_content += "## 识别文本\n\n"
        
        # 应用标注
        text = record["edited_text"]
        annotations = sorted(record["annotations"], key=lambda x: x.get("start", 0), reverse=True)
        
        for ann in annotations:
            start = ann.get("start", 0)
            end = ann.get("end", len(text))
            ann_type = ann.get("type", "highlight")
            
            if start >= end or start >= len(text) or end > len(text):
                continue
                
            content = text[start:end]
            if ann_type == "highlight":
                replacement = f"=={content}=="
            elif ann_type == "underline":
                replacement = f"<u>{content}</u>"
            elif ann_type == "strikethrough":
                replacement = f"~~{content}~~"
            else:
                replacement = content
                
            text = text[:start] + replacement + text[end:]
            
        md_content += text
        md_content += "\n\n---\n\n"
        md_content += "*导出时间: " + self._format_time(self._get_current_time()) + "*"
        
        return {"success": True, "data": md_content}
        
    def _get_current_time(self):
        """获取当前时间戳"""
        import time
        return int(time.time())
        
    def _format_time(self, timestamp):
        """格式化时间戳为可读格式"""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))