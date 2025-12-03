# =======================================
# =============== 模板管理器 ===============
# =======================================

import os
import json
from umi_log import logger


class TemplateManager:
    def __init__(self, template_type="BatchOCR"):
        self.template_type = template_type
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        self.template_file = os.path.join(self.template_dir, f"{template_type}_templates.json")
        self.templates = {}
        self._init_template_dir()
        self._load_templates()

    def _init_template_dir(self):
        """初始化模板目录"""
        if not os.path.exists(self.template_dir):
            try:
                os.makedirs(self.template_dir)
            except Exception as e:
                logger.error(f"创建模板目录失败: {e}")

    def _load_templates(self):
        """从文件加载模板"""
        if os.path.exists(self.template_file):
            try:
                with open(self.template_file, "r", encoding="utf-8") as f:
                    self.templates = json.load(f)
            except Exception as e:
                logger.error(f"加载模板文件失败: {e}")
                self.templates = {}
        else:
            self.templates = {}

    def _save_templates(self):
        """保存模板到文件"""
        try:
            with open(self.template_file, "w", encoding="utf-8") as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存模板文件失败: {e}")
            return False

    def get_all_templates(self):
        """获取所有模板"""
        return list(self.templates.values())

    def get_template(self, template_id):
        """根据ID获取模板"""
        return self.templates.get(template_id)

    def add_template(self, template_id, name, description, config):
        """添加新模板"""
        if template_id in self.templates:
            return False, "模板ID已存在"
        
        self.templates[template_id] = {
            "id": template_id,
            "name": name,
            "description": description,
            "config": config,
            "create_time": os.path.getctime(self.template_file) if os.path.exists(self.template_file) else os.time()
        }
        
        if self._save_templates():
            return True, "模板添加成功"
        else:
            del self.templates[template_id]
            return False, "模板保存失败"

    def update_template(self, template_id, name=None, description=None, config=None):
        """更新模板"""
        if template_id not in self.templates:
            return False, "模板不存在"
        
        template = self.templates[template_id]
        if name is not None:
            template["name"] = name
        if description is not None:
            template["description"] = description
        if config is not None:
            template["config"] = config
        
        if self._save_templates():
            return True, "模板更新成功"
        else:
            return False, "模板更新失败"

    def delete_template(self, template_id):
        """删除模板"""
        if template_id not in self.templates:
            return False, "模板不存在"
        
        del self.templates[template_id]
        
        if self._save_templates():
            return True, "模板删除成功"
        else:
            return False, "模板删除失败"

    def search_templates(self, keyword):
        """搜索模板"""
        if not keyword:
            return self.get_all_templates()
        
        keyword = keyword.lower()
        results = []
        for template in self.templates.values():
            if keyword in template["name"].lower() or keyword in template["description"].lower():
                results.append(template)
        return results