# ========================================
# =============== 审阅看板页 ===============
# ========================================

import os
import json
import time
import uuid
from PySide2.QtCore import Slot
from umi_log import logger
from .page import Page  # 页基类
from ..utils.review_data_manager import ReviewDataManager


class ReviewBoard(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.data_manager = ReviewDataManager()
        logger.debug("审阅看板控制器初始化完成")

    # ========================= 【qml调用python】 =========================

    @Slot(result='QVariantList')
    def get_records(self):
        """获取所有记录"""
        return self.data_manager.get_all_records()

    @Slot(str, result='QVariant')
    def get_record(self, record_id):
        """获取单个记录"""
        return self.data_manager.get_record(record_id)

    @Slot(str, str, result=bool)
    def update_record_status(self, record_id, status):
        """更新记录状态"""
        try:
            self.data_manager.update_record(record_id, {'status': status})
            return True
        except Exception as e:
            logger.error(f"更新记录状态失败: {e}")
            return False

    @Slot(str, str, result=bool)
    def update_record_tags(self, record_id, tags):
        """更新记录标签"""
        try:
            self.data_manager.update_record(record_id, {'tags': tags.split(',') if tags else []})
            return True
        except Exception as e:
            logger.error(f"更新记录标签失败: {e}")
            return False

    @Slot(str, str, result=bool)
    def update_record_assignee(self, record_id, assignee):
        """更新记录负责人"""
        try:
            self.data_manager.update_record(record_id, {'assignee': assignee})
            return True
        except Exception as e:
            logger.error(f"更新记录负责人失败: {e}")
            return False

    @Slot(str, str, result=bool)
    def update_record_note(self, record_id, note):
        """更新记录备注"""
        try:
            self.data_manager.update_record(record_id, {'note': note})
            return True
        except Exception as e:
            logger.error(f"更新记录备注失败: {e}")
            return False

    @Slot(str, result=bool)
    def delete_record(self, record_id):
        """删除记录"""
        try:
            self.data_manager.delete_record(record_id)
            return True
        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            return False

    @Slot('QVariantList', str, result=bool)
    def batch_update_status(self, record_ids, status):
        """批量更新状态"""
        try:
            for record_id in record_ids:
                self.data_manager.update_record(record_id, {'status': status})
            return True
        except Exception as e:
            logger.error(f"批量更新状态失败: {e}")
            return False

    @Slot('QVariantList', result=bool)
    def batch_delete(self, record_ids):
        """批量删除"""
        try:
            for record_id in record_ids:
                self.data_manager.delete_record(record_id)
            return True
        except Exception as e:
            logger.error(f"批量删除失败: {e}")
            return False

    @Slot('QVariantList', str, result=bool)
    def export_records(self, record_ids, format_type):
        """导出记录"""
        try:
            records = [self.data_manager.get_record(rid) for rid in record_ids]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            if format_type == 'markdown':
                content = self._generate_markdown(records)
                filename = f"review_board_export_{timestamp}.md"
            elif format_type == 'html':
                content = self._generate_html(records)
                filename = f"review_board_export_{timestamp}.html"
            else:
                return False

            export_path = os.path.join(os.path.expanduser("~"), "Documents", "UmiOCR", "exports")
            os.makedirs(export_path, exist_ok=True)
            file_path = os.path.join(export_path, filename)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            logger.error(f"导出记录失败: {e}")
            return False

    def _generate_markdown(self, records):
        """生成Markdown格式报告"""
        content = f"# UmiOCR 审阅看板报告\n"
        content += f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"记录总数: {len(records)}\n\n"

        for i, record in enumerate(records, 1):
            content += f"## 记录 {i}\n"
            content += f"- **ID**: {record.get('id', '')}\n"
            content += f"- **来源**: {record.get('source_path', '')}\n"
            content += f"- **状态**: {record.get('status', '未处理')}\n"
            content += f"- **负责人**: {record.get('assignee', '')}\n"
            content += f"- **置信度**: {record.get('confidence', 'N/A')}\n"
            content += f"- **识别时间**: {record.get('created_at', '')}\n"
            
            tags = record.get('tags', [])
            if tags:
                content += f"- **标签**: {', '.join(tags)}\n"
            
            note = record.get('note', '')
            if note:
                content += f"- **备注**: {note}\n"
            
            content += f"\n### 识别文本摘要\n"
            content += f"{record.get('text_summary', '')}\n\n"
            content += "---\n\n"

        return content

    def _generate_html(self, records):
        """生成HTML格式报告"""
        content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>UmiOCR 审阅看板报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        h3 { color: #666; }
        .record { border: 1px solid #eee; padding: 20px; margin: 15px 0; border-radius: 5px; }
        .record-info { margin-bottom: 15px; }
        .record-info span { font-weight: bold; margin-right: 5px; }
        .text-summary { background-color: #f9f9f9; padding: 15px; border-radius: 3px; border-left: 4px solid #ccc; }
        .status { padding: 3px 8px; border-radius: 3px; font-size: 12px; }
        .status-unprocessed { background-color: #fff3cd; color: #856404; }
        .status-reviewed { background-color: #d4edda; color: #155724; }
        .status-pending { background-color: #f8d7da; color: #721c24; }
        .tag { background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 12px; margin-right: 5px; }
    </style>
</head>
<body>
"""
        content += f"<h1>UmiOCR 审阅看板报告</h1>"
        content += f"<p><strong>生成时间:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>"
        content += f"<p><strong>记录总数:</strong> {len(records)}</p>\n"

        for i, record in enumerate(records, 1):
            status = record.get('status', '未处理')
            status_class = f"status-{status.replace(' ', '-').lower()}"
            
            content += f"<div class='record'>"
            content += f"<h2>记录 {i}</h2>"
            content += f"<div class='record-info'>"
            content += f"<span>ID:</span>{record.get('id', '')}<br>"
            content += f"<span>来源:</span>{record.get('source_path', '')}<br>"
            content += f"<span>状态:</span><span class='status {status_class}'>{status}</span><br>"
            content += f"<span>负责人:</span>{record.get('assignee', '')}<br>"
            content += f"<span>置信度:</span>{record.get('confidence', 'N/A')}<br>"
            content += f"<span>识别时间:</span>{record.get('created_at', '')}<br>"
            
            tags = record.get('tags', [])
            if tags:
                content += f"<span>标签:</span>"
                for tag in tags:
                    content += f"<span class='tag'>{tag}</span>"
                content += "<br>"
            
            note = record.get('note', '')
            if note:
                content += f"<span>备注:</span>{note}<br>"
            
            content += "</div>"
            content += f"<h3>识别文本摘要</h3>"
            content += f"<div class='text-summary'>{record.get('text_summary', '')}</div>"
            content += "</div>\n"

        content += """
</body>
</html>
"""
        return content

    def add_ocr_result(self, source_path, text, confidence=1.0):
        """添加OCR结果到审阅看板"""
        try:
            record = {
                'id': str(uuid.uuid4()),
                'source_path': source_path,
                'text': text,
                'text_summary': text[:200] + '...' if len(text) > 200 else text,
                'confidence': confidence,
                'status': '未处理',
                'tags': [],
                'assignee': '',
                'note': '',
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.data_manager.add_record(record)
            logger.debug(f"OCR结果已添加到审阅看板: {source_path}")
            return True
        except Exception as e:
            logger.error(f"添加OCR结果到审阅看板失败: {e}")
            return False