# =============================================
# =============== 后处理规则页面控制器 ===============
# =============================================

from PySide6.QtCore import QObject, Slot, Signal, QByteArray
from PySide6.QtQml import QJSValue
import json
import os
import re

from umi_log import logger
from .page import Page


class PostProcessRules(Page):
    def __init__(self, ctrlKey, controller):
        super().__init__(ctrlKey, controller)
        # 规则集文件路径
        self.rules_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "post_process_rules.json")
        # 加载规则集
        self.rulesets = self.load_rulesets()
        # 内置模板
        self.builtin_templates = {
            "full_width_to_half_width": {
                "name": "全角转半角",
                "description": "将全角字符转换为半角字符",
                "steps": [
                    {
                        "type": "python_snippet",
                        "enabled": True,
                        "name": "全角转半角",
                        "code": "result = ''\nfor char in input:\n    code = ord(char)\n    if code == 0x3000:\n        code = 0x20\n    elif 0xFF01 <= code <= 0xFF5E:\n        code -= 0xfee0\n    result += chr(code)\noutput = result"
                    }
                ]
            },
            "remove_serial_numbers": {
                "name": "去序号",
                "description": "移除行首的序号（如1. 2. 3. 或①②③等）",
                "steps": [
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "移除数字序号",
                        "pattern": r"^\s*\d+\.\s*",
                        "replacement": "",
                        "flags": ["MULTILINE"]
                    },
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "移除汉字序号",
                        "pattern": r"^\s*[\u4e00-\u9fa5]{1,2}\s*、\s*",
                        "replacement": "",
                        "flags": ["MULTILINE"]
                    },
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "移除圆圈序号",
                        "pattern": r"^\s*[\u2460-\u2473]\s*",
                        "replacement": "",
                        "flags": ["MULTILINE"]
                    }
                ]
            }
        }

    def load_rulesets(self):
        """加载规则集"""
        try:
            if os.path.exists(self.rules_file_path):
                with open(self.rules_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # 如果文件不存在，返回默认值
                return {
                    "screenshot_ocr": [],
                    "batch_ocr": [],
                    "batch_doc": []
                }
        except Exception as e:
            logger.error(f"加载后处理规则集失败: {e}")
            return {
                "screenshot_ocr": [],
                "batch_ocr": [],
                "batch_doc": []
            }

    def save_rulesets(self):
        """保存规则集"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.rules_file_path), exist_ok=True)
            with open(self.rules_file_path, "w", encoding="utf-8") as f:
                json.dump(self.rulesets, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存后处理规则集失败: {e}")
            return False

    @Slot(str, QJSValue, result=bool)
    def save_rules(self, ocr_type, rules):
        """保存指定OCR类型的规则"""
        try:
            # 将QJSValue转换为Python列表
            rules_list = rules.toVariant()
            # 保存规则
            self.rulesets[ocr_type] = rules_list
            # 保存到文件
            return self.save_rulesets()
        except Exception as e:
            logger.error(f"保存后处理规则失败: {e}")
            return False

    @Slot(str, result=QJSValue)
    def load_rules(self, ocr_type):
        """加载指定OCR类型的规则"""
        try:
            # 获取规则
            rules = self.rulesets.get(ocr_type, [])
            # 返回给QML
            return QJSValue.fromVariant(rules)
        except Exception as e:
            logger.error(f"加载后处理规则失败: {e}")
            return QJSValue.fromVariant([])

    @Slot(result=QJSValue)
    def get_builtin_templates(self):
        """获取内置模板"""
        try:
            return QJSValue.fromVariant(self.builtin_templates)
        except Exception as e:
            logger.error(f"获取内置模板失败: {e}")
            return QJSValue.fromVariant({})

    @Slot(str, result=QJSValue)
    def get_template(self, template_name):
        """获取指定名称的模板"""
        try:
            template = self.builtin_templates.get(template_name, {})
            return QJSValue.fromVariant(template)
        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return QJSValue.fromVariant({})

    @Slot(str, str, result=str)
    def apply_rules(self, ocr_type, text):
        """应用指定OCR类型的规则到文本"""
        try:
            # 获取规则
            rules = self.rulesets.get(ocr_type, [])
            # 应用每个规则步骤
            result = text
            for step in rules:
                if step.get("enabled", False):
                    step_type = step.get("type", "")
                    if step_type == "regex_replace":
                        # 正则替换
                        pattern = step.get("pattern", "")
                        replacement = step.get("replacement", "")
                        flags = step.get("flags", [])
                        # 解析flags
                        re_flags = 0
                        if "IGNORECASE" in flags:
                            re_flags |= re.IGNORECASE
                        if "MULTILINE" in flags:
                            re_flags |= re.MULTILINE
                        if "DOTALL" in flags:
                            re_flags |= re.DOTALL
                        # 替换
                        result = re.sub(pattern, replacement, result, flags=re_flags)
                    elif step_type == "case_conversion":
                        # 大小写转换
                        conversion_type = step.get("conversion_type", "none")
                        if conversion_type == "uppercase":
                            result = result.upper()
                        elif conversion_type == "lowercase":
                            result = result.lower()
                        elif conversion_type == "titlecase":
                            result = result.title()
                    elif step_type == "merge_empty_lines":
                        # 空行合并
                        result = re.sub(r"\n\s*\n", "\n\n", result)
                    elif step_type == "python_snippet":
                        # 自定义Python片段
                        code = step.get("code", "")
                        # 执行代码
                        try:
                            local_vars = {"input": result, "output": ""}
                            exec(code, {}, local_vars)
                            result = local_vars.get("output", result)
                        except Exception as e:
                            logger.error(f"执行Python片段失败: {e}")
                            # 执行失败时，保持原始结果不变
            return result
        except Exception as e:
            logger.error(f"应用后处理规则失败: {e}")
            return text

    @Slot(str, QJSValue, result=bool)
    def export_rules(self, file_path, rules):
        """导出规则到JSON文件"""
        try:
            # 将QJSValue转换为Python列表
            rules_list = rules.toVariant()
            # 保存到文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(rules_list, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"导出规则失败: {e}")
            return False

    @Slot(str, result=QJSValue)
    def import_rules(self, file_path):
        """从JSON文件导入规则"""
        try:
            # 从文件加载规则
            with open(file_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            # 返回给QML
            return QJSValue.fromVariant(rules)
        except Exception as e:
            logger.error(f"导入规则失败: {e}")
            return QJSValue.fromVariant([])
