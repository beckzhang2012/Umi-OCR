# ========================================
# =============== 审阅看板页 ===============
# ========================================

import os
import json
import time
import shutil
from datetime import datetime
from PySide2.QtCore import Slot

import logging
import time
import os

# 确保logs目录存在
logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, f'review_board_{time.strftime("%Y%m%d")}.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from .page import Page  # 页基类
import os


class ReviewBoard(Page):
    def __init__(self, ctrlKey=None, controller=None):
        # 如果没有提供参数，创建一个模拟的Page实例
        if ctrlKey is None and controller is None:
            self.ctrlKey = "reviewBoard"
            self.controller = None
        else:
            super().__init__(ctrlKey, controller)
        
        self.data_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "review_board.json")
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        self.records = self._load_records()
        
    def _load_records(self):
        """加载审阅看板记录"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载审阅看板记录失败: {e}")
        return []
    
    def _save_records(self):
        """保存审阅看板记录"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存审阅看板记录失败: {e}")
    
    def _add_record(self, record):
        """添加新的OCR记录到审阅看板"""
        # 生成唯一ID
        record_id = f"{int(time.time() * 1000)}_{len(self.records)}"
        # 添加记录元数据
        record.update({
            "id": record_id,
            "status": "未处理",  # 未处理/已校对/待修改/已完成
            "tags": [],
            "assignee": "",
            "notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        # 生成缩略图（如果需要）
        if "image_path" in record and os.path.exists(record["image_path"]):
            thumbnail_path = os.path.join(os.path.dirname(self.data_file), "thumbnails", f"{record_id}.jpg")
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
            # TODO: 生成缩略图
            record["thumbnail_path"] = thumbnail_path
        
        self.records.insert(0, record)
        self._save_records()
        return record_id
    
    def _update_record(self, record_id, updates):
        """更新记录信息"""
        for record in self.records:
            if record["id"] == record_id:
                record.update(updates)
                record["updated_at"] = datetime.now().isoformat()
                self._save_records()
                return True
        return False
    
    def _delete_record(self, record_id):
        """删除记录"""
        self.records = [r for r in self.records if r["id"] != record_id]
        self._save_records()
    
    def _get_records(self, filters=None, sort_by="created_at", sort_order="desc"):
        """获取记录列表，支持筛选和排序"""
        filtered = self.records.copy()
        
        # 筛选
        if filters:
            if "status" in filters and filters["status"]:
                filtered = [r for r in filtered if r["status"] == filters["status"]]
            if "assignee" in filters and filters["assignee"]:
                filtered = [r for r in filtered if r["assignee"] == filters["assignee"]]
            if "tags" in filters and filters["tags"]:
                filtered = [r for r in filtered if any(tag in r["tags"] for tag in filters["tags"])]
            if "search" in filters and filters["search"]:
                search_term = filters["search"].lower()
                filtered = [r for r in filtered if search_term in r.get("text", "").lower() or search_term in r.get("source", "").lower()]
        
        # 排序
        if sort_by in ["created_at", "updated_at", "confidence"]:
            filtered.sort(key=lambda x: x.get(sort_by, ""), reverse=(sort_order == "desc"))
        
        return filtered
    
    def _batch_update(self, record_ids, updates):
        """批量更新记录"""
        for record in self.records:
            if record["id"] in record_ids:
                record.update(updates)
                record["updated_at"] = datetime.now().isoformat()
        self._save_records()
    
    def _batch_delete(self, record_ids):
        """批量删除记录"""
        self.records = [r for r in self.records if r["id"] not in record_ids]
        self._save_records()
    
    def _export_records(self, record_ids, format_type="markdown"):
        """导出记录为Markdown或HTML报告"""
        records = [r for r in self.records if r["id"] in record_ids]
        if format_type == "markdown":
            return self._export_to_markdown(records)
        elif format_type == "html":
            return self._export_to_html(records)
        return ""
    
    def _export_to_markdown(self, records):
        """导出为Markdown报告"""
        md = f"# OCR审阅看板报告\n\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n共 {len(records)} 条记录\n\n"
        
        for i, record in enumerate(records, 1):
            md += f"## 记录 {i}\n\n"
            md += f"- **来源**: {record.get('source', '')}\n"
            md += f"- **状态**: {record.get('status', '')}\n"
            md += f"- **负责人**: {record.get('assignee', '')}\n"
            md += f"- **置信度**: {record.get('confidence', '0.0')}\n"
            md += f"- **创建时间**: {record.get('created_at', '')}\n"
            md += f"- **更新时间**: {record.get('updated_at', '')}\n"
            if record.get('tags'):
                md += f"- **标签**: {', '.join(record['tags'])}\n"
            if record.get('notes'):
                md += f"- **备注**: {record['notes']}\n"
            md += f"\n**识别文本**:\n\n{record.get('text', '')}\n\n"
            md += "---\n\n"
        
        return md
    
    def _export_to_html(self, records):
        """导出为HTML报告"""
        html = f"""\n<!DOCTYPE html>\n<html>\n<head>\n    <meta charset="UTF-8">\n    <title>OCR审阅看板报告</title>\n    <style>\n        body {{ font-family: Arial, sans-serif; margin: 40px; }} \n        .record {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 5px; }} \n        .record h2 {{ margin-top: 0; }} \n        .metadata {{ margin-bottom: 15px; }} \n        .metadata span {{ margin-right: 20px; }} \n        .text {{ white-space: pre-wrap; background-color: #f5f5f5; padding: 10px; border-radius: 3px; }} \n    </style>\n</head>\n<body>\n    <h1>OCR审阅看板报告</h1>\n    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n    <p>共 {len(records)} 条记录</p>\n"""
        
        for i, record in enumerate(records, 1):
            html += f"""\n        <div class="record">\n            <h2>记录 {i}</h2>\n            <div class="metadata">\n                <span><strong>来源:</strong> {record.get('source', '')}</span>\n                <span><strong>状态:</strong> {record.get('status', '')}</span>\n                <span><strong>负责人:</strong> {record.get('assignee', '')}</span>\n                <span><strong>置信度:</strong> {record.get('confidence', '0.0')}</span>\n            </div>\n            <div class="metadata">\n                <span><strong>创建时间:</strong> {record.get('created_at', '')}</span>\n                <span><strong>更新时间:</strong> {record.get('updated_at', '')}</span>\n                {('<span><strong>标签:</strong> ' + ', '.join(record['tags']) + '</span>') if record.get('tags') else ''} \n            </div>\n            {('<div class="metadata"><strong>备注:</strong> ' + record.get('notes', '') + '</div>') if record.get('notes') else ''} \n            <div class="text">{record.get('text', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</div>\n        </div>\n"""
        
        html += "</body></html>"
        return html
    
    # ========================= 【qml调用python】 =========================
    
    @Slot(list, result=str)
    def addRecord(self, record):
        """添加新记录"""
        return self._add_record(record)
    
    @Slot(str, "QVariant", result=bool)
    def updateRecord(self, record_id, updates):
        """更新记录"""
        # 如果是字典，直接使用；否则调用toVariant()
        if isinstance(updates, dict):
            return self._update_record(record_id, updates)
        else:
            return self._update_record(record_id, updates.toVariant())
    
    @Slot(str)
    def deleteRecord(self, record_id):
        """删除记录"""
        self._delete_record(record_id)
    
    @Slot("QVariant", str, str, result="QVariant")
    def getRecords(self, filters=None, sort_by="created_at", sort_order="desc"):
        """获取记录列表"""
        # 如果是字典，直接使用；否则调用toVariant()
        if isinstance(filters, dict):
            return self._get_records(filters, sort_by, sort_order)
        else:
            return self._get_records(filters.toVariant() if filters else None, sort_by, sort_order)
    
    @Slot(list, "QVariant")
    def batchUpdate(self, record_ids, updates):
        """批量更新记录"""
        # 如果是字典，直接使用；否则调用toVariant()
        if isinstance(updates, dict):
            self._batch_update(record_ids, updates)
        else:
            self._batch_update(record_ids, updates.toVariant())
    
    @Slot(list)
    def batchDelete(self, record_ids):
        """批量删除记录"""
        self._batch_delete(record_ids)
    
    @Slot(list, str, result=str)
    def exportRecords(self, record_ids, format_type):
        """导出记录"""
        return self._export_records(record_ids, format_type)
    
    @Slot(result="QVariant")
    def getAllRecords(self):
        """获取所有记录"""
        return self.records