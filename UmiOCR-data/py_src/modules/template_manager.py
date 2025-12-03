# ===============================================
# =============== 模板管理器 ===============
# ===============================================

"""
管理OCR配置模板，包括保存、加载、重命名和删除模板。
模板数据存储为JSON文件，位于UmiOCR-data目录下。
"""

import json
import os
from typing import List, Dict, Optional

class TemplateManager:
    def __init__(self, data_dir: str = "UmiOCR-data"):
        self.data_dir = data_dir
        self.template_dir = os.path.join(data_dir, "templates")
        self._ensure_template_dir()
    
    def _ensure_template_dir(self):
        """确保模板目录存在"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
    
    def save_template(self, name: str, description: str, configs: Dict) -> str:
        """
        保存模板
        
        参数:
            name: 模板名称
            description: 模板描述
            configs: OCR配置字典
            
        返回:
            保存成功的消息
        """
        if not name:
            return "[Error] 模板名称不能为空"
        
        # 检查模板是否已存在
        template_file = os.path.join(self.template_dir, f"{name}.json")
        if os.path.exists(template_file):
            return "[Error] 模板名称已存在"
        
        # 创建模板数据
        template_data = {
            "name": name,
            "description": description,
            "configs": configs,
            "created": str(pd.Timestamp.now()) if 'pd' in globals() else str(datetime.datetime.now())
        }
        
        # 保存到文件
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            return "[Success] 模板保存成功"
        except Exception as e:
            return f"[Error] 保存模板失败: {str(e)}"
    
    def load_template(self, name: str) -> Optional[Dict]:
        """
        加载模板
        
        参数:
            name: 模板名称
            
        返回:
            模板数据字典，如果加载失败返回None
        """
        template_file = os.path.join(self.template_dir, f"{name}.json")
        
        if not os.path.exists(template_file):
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            return template_data
        except Exception as e:
            return None
    
    def delete_template(self, name: str) -> str:
        """
        删除模板
        
        参数:
            name: 模板名称
            
        返回:
            删除结果消息
        """
        template_file = os.path.join(self.template_dir, f"{name}.json")
        
        if not os.path.exists(template_file):
            return "[Error] 模板不存在"
        
        try:
            os.remove(template_file)
            return "[Success] 模板删除成功"
        except Exception as e:
            return f"[Error] 删除模板失败: {str(e)}"
    
    def rename_template(self, old_name: str, new_name: str) -> str:
        """
        重命名模板
        
        参数:
            old_name: 原模板名称
            new_name: 新模板名称
            
        返回:
            重命名结果消息
        """
        if not new_name:
            return "[Error] 新模板名称不能为空"
        
        old_file = os.path.join(self.template_dir, f"{old_name}.json")
        new_file = os.path.join(self.template_dir, f"{new_name}.json")
        
        if not os.path.exists(old_file):
            return "[Error] 原模板不存在"
        
        if os.path.exists(new_file):
            return "[Error] 新模板名称已存在"
        
        try:
            # 重命名文件
            os.rename(old_file, new_file)
            
            # 更新文件内容中的name字段
            with open(new_file, 'r+', encoding='utf-8') as f:
                template_data = json.load(f)
                template_data['name'] = new_name
                f.seek(0)
                json.dump(template_data, f, ensure_ascii=False, indent=2)
                f.truncate()
            
            return "[Success] 模板重命名成功"
        except Exception as e:
            return f"[Error] 重命名模板失败: {str(e)}"
    
    def list_templates(self) -> List[Dict]:
        """
        获取所有模板列表
        
        返回:
            模板列表，每个元素包含name和description字段
        """
        templates = []
        
        if not os.path.exists(self.template_dir):
            return templates
        
        try:
            # 遍历模板目录
            for filename in os.listdir(self.template_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.template_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                            templates.append({
                                "name": template_data.get("name", filename[:-5]),
                                "description": template_data.get("description", ""),
                                "created": template_data.get("created", "")
                            })
                    except Exception as e:
                        # 忽略损坏的模板文件
                        continue
            
            # 按创建时间排序
            templates.sort(key=lambda x: x['created'], reverse=True)
            return templates
        except Exception as e:
            return []

# 全局模板管理器实例
template_manager = TemplateManager()

# 确保导入必要的模块
try:
    import pandas as pd
    import datetime
except ImportError:
    pass
