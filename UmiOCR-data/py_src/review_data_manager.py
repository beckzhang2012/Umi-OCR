#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审阅看板数据管理模块
负责OCR识别记录的JSON文件存储和管理
"""

import json
import os
import time
import uuid
from typing import List, Dict, Optional

class ReviewDataManager:
    """审阅看板数据管理器"""
    
    def __init__(self, data_dir: str = None):
        """初始化数据管理器"""
        self.data_dir = data_dir or self._get_default_data_dir()
        self.records_file = os.path.join(self.data_dir, "review_records.json")
        self._ensure_data_dir()
        self._load_records()
    
    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 上级目录作为数据目录
        return os.path.dirname(current_dir)
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _load_records(self):
        """从JSON文件加载记录"""
        self.records: List[Dict] = []
        
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    self.records = json.load(f)
            except Exception as e:
                print(f"加载记录失败: {e}")
                self.records = []
    
    def _save_records(self):
        """保存记录到JSON文件"""
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存记录失败: {e}")
            return False
    
    def add_record(self, source_path: str, text_summary: str, confidence: float, 
                  image_path: Optional[str] = None, full_text: Optional[str] = None) -> str:
        """添加新的识别记录"""
        record_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        record = {
            "id": record_id,
            "source_path": source_path,
            "text_summary": text_summary,
            "confidence": confidence,
            "image_path": image_path,
            "full_text": full_text,
            "status": "未处理",
            "tags": [],
            "assignee": "",
            "note": "",
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        self.records.insert(0, record)  # 最新记录放在前面
        self._save_records()
        return record_id
    
    def get_records(self) -> List[Dict]:
        """获取所有记录"""
        return self.records.copy()
    
    def get_record(self, record_id: str) -> Optional[Dict]:
        """根据ID获取记录"""
        for record in self.records:
            if record["id"] == record_id:
                return record.copy()
        return None
    
    def update_record(self, record_id: str, **kwargs) -> bool:
        """更新记录字段"""
        for record in self.records:
            if record["id"] == record_id:
                # 更新允许的字段
                allowed_fields = ["status", "tags", "assignee", "note", "text_summary"]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        # 特殊处理tags字段
                        if key == "tags" and isinstance(value, str):
                            # 如果是字符串，按逗号分割并去重
                            tags = [tag.strip() for tag in value.split(",") if tag.strip()]
                            record[key] = list(set(tags))  # 去重
                        else:
                            record[key] = value
                
                record["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                return self._save_records()
        return False
    
    def update_record_status(self, record_id: str, status: str) -> bool:
        """更新记录状态"""
        return self.update_record(record_id, status=status)
    
    def update_record_tags(self, record_id: str, tags: str) -> bool:
        """更新记录标签"""
        return self.update_record(record_id, tags=tags)
    
    def update_record_assignee(self, record_id: str, assignee: str) -> bool:
        """更新记录负责人"""
        return self.update_record(record_id, assignee=assignee)
    
    def update_record_note(self, record_id: str, note: str) -> bool:
        """更新记录备注"""
        return self.update_record(record_id, note=note)
    
    def delete_record(self, record_id: str) -> bool:
        """删除记录"""
        for i, record in enumerate(self.records):
            if record["id"] == record_id:
                del self.records[i]
                return self._save_records()
        return False
    
    def batch_update_status(self, record_ids: List[str], status: str) -> bool:
        """批量更新状态"""
        success_count = 0
        for record_id in record_ids:
            if self.update_record_status(record_id, status):
                success_count += 1
        return success_count == len(record_ids)
    
    def batch_delete(self, record_ids: List[str]) -> bool:
        """批量删除记录"""
        # 先收集要删除的记录索引
        indices_to_delete = []
        for i, record in enumerate(self.records):
            if record["id"] in record_ids:
                indices_to_delete.append(i)
        
        # 从后往前删除，避免索引错乱
        for i in sorted(indices_to_delete, reverse=True):
            del self.records[i]
        
        return self._save_records()
    
    def export_records(self, record_ids: List[str], export_format: str = "markdown") -> str:
        """导出指定记录
        :param record_ids: 记录ID列表
        :param export_format: 导出格式 (markdown/html)
        :return: 导出内容
        """
        records = []
        for record_id in record_ids:
            record = self.get_record(record_id)
            if record:
                records.append(record)
        
        if not records:
            return ""
        
        if export_format == "markdown":
            return self._export_to_markdown(records)
        elif export_format == "html":
            return self._export_to_html(records)
        else:
            return ""
    
    def _export_to_markdown(self, records: List[Dict]) -> str:
        """导出为Markdown格式"""
        from datetime import datetime
        content = "# OCR审阅报告\n\n"
        content += f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"**记录数量**: {len(records)}\n\n"
        
        for i, record in enumerate(records, 1):
            content += f"## 记录 {i}\n\n"
            content += f"- **ID**: {record['id']}\n"
            content += f"- **来源**: {record['source_path']}\n"
            content += f"- **状态**: {record['status']}\n"
            content += f"- **负责人**: {record['assignee'] or '未分配'}\n"
            content += f"- **标签**: {', '.join(record['tags']) if record['tags'] else '无'}\n"
            content += f"- **置信度**: {record['confidence']:.2f}\n"
            content += f"- **创建时间**: {record['created_at']}\n"
            content += f"- **更新时间**: {record['updated_at']}\n\n"
            
            if record['note']:
                content += f"### 备注\n{record['note']}\n\n"
            
            content += f"### 文本摘要\n{record['text_summary']}\n\n"
            
            if record['full_text']:
                content += f"### 完整文本\n```\n{record['full_text']}\n```\n\n"
        
        return content
    
    def _export_to_html(self, records: List[Dict]) -> str:
        """导出为HTML格式"""
        from datetime import datetime
        content = "<!DOCTYPE html>\n"
        content += "<html lang='zh-CN'>\n"
        content += "<head>\n"
        content += "    <meta charset='UTF-8'>\n"
        content += "    <title>OCR审阅报告</title>\n"
        content += "    <style>\n"
        content += "        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }\n"
        content += "        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }\n"
        content += "        h2 { color: #666; margin-top: 30px; }\n"
        content += "        h3 { color: #888; }\n"
        content += "        .record { border: 1px solid #eee; padding: 20px; margin: 15px 0; border-radius: 5px; }\n"
        content += "        .meta { background: #f9f9f9; padding: 10px; border-radius: 3px; margin-bottom: 15px; }\n"
        content += "        .meta p { margin: 5px 0; }\n"
        content += "        pre { background: #f5f5f5; padding: 15px; border-radius: 3px; overflow-x: auto; }\n"
        content += "    </style>\n"
        content += "</head>\n"
        content += "<body>\n"
        
        content += f"<h1>OCR审阅报告</h1>\n"
        content += f"<p><strong>导出时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
        content += f"<p><strong>记录数量:</strong> {len(records)}</p>\n\n"
        
        for i, record in enumerate(records, 1):
            content += f"<div class='record'>\n"
            content += f"    <h2>记录 {i}</h2>\n"
            content += f"    <div class='meta'>\n"
            content += f"        <p><strong>ID:</strong> {record['id']}</p>\n"
            content += f"        <p><strong>来源:</strong> {record['source_path']}</p>\n"
            content += f"        <p><strong>状态:</strong> {record['status']}</p>\n"
            content += f"        <p><strong>负责人:</strong> {record['assignee'] or '未分配'}</p>\n"
            content += f"        <p><strong>标签:</strong> {', '.join(record['tags']) if record['tags'] else '无'}</p>\n"
            content += f"        <p><strong>置信度:</strong> {record['confidence']:.2f}</p>\n"
            content += f"        <p><strong>创建时间:</strong> {record['created_at']}</p>\n"
            content += f"        <p><strong>更新时间:</strong> {record['updated_at']}</p>\n"
            content += f"    </div>\n\n"
            
            if record['note']:
                content += f"    <h3>备注</h3>\n"
                content += f"    <p>{record['note']}</p>\n\n"
            
            content += f"    <h3>文本摘要</h3>\n"
            content += f"    <p>{record['text_summary']}</p>\n\n"
            
            if record['full_text']:
                content += f"    <h3>完整文本</h3>\n"
                content += f"    <pre>{record['full_text']}</pre>\n"
            
            content += "</div>\n\n"
        
        content += "</body>\n"
        content += "</html>"
        
        return content
    
    def clear_all(self) -> bool:
        """清空所有记录"""
        self.records = []
        return self._save_records()
    
    def get_record_count(self) -> int:
        """获取记录总数"""
        return len(self.records)
    
    def get_records_by_status(self, status: str) -> List[Dict]:
        """按状态筛选记录"""
        return [record.copy() for record in self.records if record["status"] == status]
    
    def search_records(self, keyword: str) -> List[Dict]:
        """搜索记录"""
        keyword = keyword.lower()
        results = []
        
        for record in self.records:
            if (keyword in record["source_path"].lower() or
                keyword in record["text_summary"].lower() or
                (record["full_text"] and keyword in record["full_text"].lower()) or
                (record["assignee"] and keyword in record["assignee"].lower()) or
                (record["note"] and keyword in record["note"].lower())):
                results.append(record.copy())
        
        return results

# 全局实例
_data_manager = None

def get_data_manager() -> ReviewDataManager:
    """获取全局数据管理器实例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = ReviewDataManager()
    return _data_manager

if __name__ == "__main__":
    # 测试代码
    manager = ReviewDataManager()
    
    # 添加测试记录
    record_id = manager.add_record(
        source_path="test/image1.jpg",
        text_summary="这是测试文本摘要",
        confidence=0.95,
        full_text="这是完整的识别文本内容\n包含多行文本"
    )
    print(f"添加测试记录: {record_id}")
    
    # 获取所有记录
    records = manager.get_records()
    print(f"记录总数: {len(records)}")
    
    # 更新记录
    manager.update_record_status(record_id, "已校对")
    manager.update_record_assignee(record_id, "张三")
    manager.update_record_tags(record_id, "测试,重要")
    
    # 导出测试
    markdown_content = manager.export_records([record_id], "markdown")
    print("\nMarkdown导出:")
    print(markdown_content)
    
    html_content = manager.export_records([record_id], "html")
    print("\nHTML导出:")
    print(html_content[:500] + "...")  # 只显示前500字符
    
    # 删除测试记录
    manager.delete_record(record_id)
    print(f"\n删除后记录总数: {len(manager.get_records())}")