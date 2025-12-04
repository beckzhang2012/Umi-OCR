# ===============================================
# =============== 后处理规则页控制器 ===============
# ===============================================

import os
import json
from PySide2.QtCore import QObject, Slot

from umi_log import logger
from .page import Page  # 页基类



class PostProcessingRules(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.rules_file = os.path.join(os.getcwd(), "post_processing_rules.json")
        self.rules = self.load_rules()
        self.templates = self.load_templates()

    # ========================= 【规则管理】 =========================

    def load_rules(self):
        """加载后处理规则"""
        if not os.path.exists(self.rules_file):
            return {
                "screenshot_ocr": [],
                "batch_ocr": [],
                "batch_doc": []
            }
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载后处理规则失败: {e}")
            return {
                "screenshot_ocr": [],
                "batch_ocr": [],
                "batch_doc": []
            }

    def save_rules(self):
        """保存后处理规则"""
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存后处理规则失败: {e}")
            return False

    def load_templates(self):
        """加载内置模板"""
        return [
            {
                "name": "全角转半角",
                "description": "将全角字符转换为半角字符",
                "rules": [
                    {
                        "type": "full_to_half",
                        "enabled": True,
                        "name": "全角转半角"
                    }
                ]
            },
            {
                "name": "去序号",
                "description": "去除行首的序号（如：1. 2. 3. 或 (1) (2) (3)）",
                "rules": [
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "去除数字序号",
                        "pattern": r"^\s*\d+\.\s*",
                        "replacement": ""
                    },
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "去除括号序号",
                        "pattern": r"^\s*\(\d+\)\s*",
                        "replacement": ""
                    }
                ]
            },
            {
                "name": "空行合并",
                "description": "将多个连续空行合并为一个",
                "rules": [
                    {
                        "type": "merge_empty_lines",
                        "enabled": True,
                        "name": "合并空行"
                    }
                ]
            },
            {
                "name": "去除多余空格",
                "description": "去除行首、行尾和多余的空格",
                "rules": [
                    {
                        "type": "trim_lines",
                        "enabled": True,
                        "name": "去除行首尾空格"
                    },
                    {
                        "type": "regex_replace",
                        "enabled": True,
                        "name": "去除多余空格",
                        "pattern": r"\s+",
                        "replacement": " "
                    }
                ]
            }
        ]

    # ========================= 【qml调用python】 =========================

    @Slot(result="QVariant")
    def get_rules(self):
        """获取所有规则"""
        return self.rules

    @Slot(str, "QVariant")
    def set_rules(self, target, rules):
        """设置规则"""
        if target in self.rules:
            self.rules[target] = rules
            self.save_rules()

    @Slot(result="QVariant")
    def get_templates(self):
        """获取内置模板"""
        return self.templates

    @Slot(str, str)
    def apply_template(self, target, template_name):
        """应用模板"""
        for template in self.templates:
            if template["name"] == template_name:
                self.rules[target] = template["rules"]
                self.save_rules()
                break

    @Slot(str, result=str)
    def export_rules(self, target):
        """导出规则"""
        if target not in self.rules:
            return ""
        try:
            return json.dumps(self.rules[target], ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"导出规则失败: {e}")
            return ""

    @Slot(str, str)
    def import_rules(self, target, rules_json):
        """导入规则"""
        try:
            rules = json.loads(rules_json)
            self.rules[target] = rules
            self.save_rules()
        except Exception as e:
            logger.error(f"导入规则失败: {e}")

    @Slot(str, str, result="QVariant")
    def preview(self, target, text):
        """预览规则效果"""
        if target not in self.rules:
            return {"original": text, "steps": [], "result": text}

        rules = self.rules[target]
        steps = []
        current_text = text

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            step_result = self.apply_rule(rule, current_text)
            steps.append({
                "name": rule.get("name", "未命名规则"),
                "type": rule.get("type", "unknown"),
                "input": current_text,
                "output": step_result
            })
            current_text = step_result

        return {
            "original": text,
            "steps": steps,
            "result": current_text
        }

    def apply_rule(self, rule, text):
        """应用单个规则"""
        rule_type = rule.get("type")

        if rule_type == "regex_replace":
            import re
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            flags = 0
            if rule.get("case_insensitive", False):
                flags |= re.IGNORECASE
            if rule.get("multiline", False):
                flags |= re.MULTILINE
            if rule.get("dotall", False):
                flags |= re.DOTALL
            return re.sub(pattern, replacement, text, flags=flags)

        elif rule_type == "full_to_half":
            return self.full_to_half(text)

        elif rule_type == "half_to_full":
            return self.half_to_full(text)

        elif rule_type == "upper_case":
            return text.upper()

        elif rule_type == "lower_case":
            return text.lower()

        elif rule_type == "title_case":
            return text.title()

        elif rule_type == "capitalize":
            return text.capitalize()

        elif rule_type == "merge_empty_lines":
            import re
            return re.sub(r"\n\s*\n", "\n\n", text)

        elif rule_type == "trim_lines":
            lines = text.split("\n")
            lines = [line.strip() for line in lines]
            return "\n".join(lines)

        elif rule_type == "python_script":
            script = rule.get("script", "")
            try:
                # 创建一个安全的执行环境
                env = {"text": text}
                exec(script, env)
                return env.get("result", text)
            except Exception as e:
                logger.error(f"执行Python脚本失败: {e}")
                return text

        return text

    def full_to_half(self, text):
        """全角转半角"""
        result = []
        for char in text:
            code = ord(char)
            if code == 0x3000:
                code = 0x0020
            elif 0xFF01 <= code <= 0xFF5E:
                code -= 0xFEE0
            result.append(chr(code))
        return "".join(result)

    def half_to_full(self, text):
        """半角转全角"""
        result = []
        for char in text:
            code = ord(char)
            if code == 0x0020:
                code = 0x3000
            elif 0x0021 <= code <= 0x007E:
                code += 0xFEE0
            result.append(chr(code))
        return "".join(result)

    # ========================= 【TBPU集成】 =========================

    def apply_post_processing(self, target, textBlocks):
        """应用后处理规则到文块列表"""
        if target not in self.rules:
            return textBlocks

        rules = self.rules[target]
        if not rules:
            return textBlocks

        # 将文块转换为文本
        full_text = ""
        for tb in textBlocks:
            full_text += tb.get("text", "") + tb.get("end", "\n")

        # 应用所有规则
        processed_text = full_text
        for rule in rules:
            if rule.get("enabled", True):
                processed_text = self.apply_rule(rule, processed_text)

        # 将处理后的文本转换回文块
        lines = processed_text.split("\n")
        new_textBlocks = []
        for i, line in enumerate(lines):
            if line.strip():
                new_textBlocks.append({
                    "box": [[0, i * 20], [100, i * 20], [100, (i + 1) * 20], [0, (i + 1) * 20]],
                    "score": 1.0,
                    "text": line,
                    "end": "\n"
                })

        return new_textBlocks
