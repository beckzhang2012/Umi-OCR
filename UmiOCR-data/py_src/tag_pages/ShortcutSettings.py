# ===============================================
# =============== 快捷键设置页面 ===============
# ===============================================

from PySide2.QtCore import QObject, Slot, Signal
import json
import os

from umi_log import logger
from .page import Page
from ..event_bus.key_mouse.keyboard import HotkeyCtrl
from ..utils import pre_configs


class ShortcutSettings(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.shortcut_config = self.load_config()
        self.default_config = self.get_default_config()

    # ========================= 【配置文件操作】 =========================

    def get_config_path(self):
        """获取快捷键配置文件路径"""
        return "./shortcut_settings.json"

    def load_config(self):
        """加载快捷键配置"""
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as file:
                    config = json.load(file)
            except Exception as e:
                logger.error(f"加载快捷键配置失败: {e}")
                config = self.get_default_config()
        else:
            config = self.get_default_config()

        # 确保配置结构完整
        if not isinstance(config, dict):
            config = self.get_default_config()

        return config

    def save_config(self):
        """保存快捷键配置"""
        config_path = self.get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(self.shortcut_config, file, ensure_ascii=False, indent=4)
            return "[Success]"
        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")
            return f"[Error] 保存失败: {e}"

    def get_default_config(self):
        """获取默认快捷键配置"""
        return {
            "screenshot": {
                "key": "ctrl+alt+a",
                "description": "截图OCR",
                "module": "截图相关"
            },
            "batch_ocr": {
                "key": "ctrl+alt+b",
                "description": "批量OCR",
                "module": "批量相关"
            },
            "qrcode": {
                "key": "ctrl+alt+c",
                "description": "扫码识别",
                "module": "其他"
            },
            "toggle_window": {
                "key": "ctrl+alt+o",
                "description": "显示/隐藏窗口",
                "module": "全局设置"
            }
        }

    # ========================= 【快捷键管理】 =========================

    def update_shortcut(self, id, new_key):
        """更新快捷键"""
        if id not in self.shortcut_config:
            return f"[Error] 快捷键ID不存在: {id}"

        # 检查是否与现有快捷键冲突
        if self.is_key_conflict(new_key, id):
            return f"[Error] 快捷键已存在: {new_key}"

        # 删除旧快捷键
        old_key = self.shortcut_config[id]["key"]
        if old_key:
            HotkeyCtrl.delHotkey(keysName=old_key, title=f"<<{id}>>")

        # 添加新快捷键
        result = HotkeyCtrl.addHotkey(keysName=new_key, title=f"<<{id}>>")
        if result.startswith("[Success]") or result.startswith("[Warning]"):
            self.shortcut_config[id]["key"] = new_key
            self.save_config()
            return "[Success]"
        else:
            return result

    def reset_shortcut(self, id=None):
        """重置快捷键"""
        if id:
            # 重置单个快捷键
            if id not in self.default_config:
                return f"[Error] 快捷键ID不存在: {id}"

            # 删除旧快捷键
            old_key = self.shortcut_config.get(id, {}).get("key", "")
            if old_key:
                HotkeyCtrl.delHotkey(keysName=old_key, title=f"<<{id}>>")

            # 恢复默认快捷键
            default_key = self.default_config[id]["key"]
            result = HotkeyCtrl.addHotkey(keysName=default_key, title=f"<<{id}>>")
            if result.startswith("[Success]") or result.startswith("[Warning]"):
                self.shortcut_config[id] = self.default_config[id].copy()
                self.save_config()
                return "[Success]"
            else:
                return result
        else:
            # 重置所有快捷键
            for id in self.shortcut_config:
                old_key = self.shortcut_config[id]["key"]
                if old_key:
                    HotkeyCtrl.delHotkey(keysName=old_key, title=f"<<{id}>>")

            # 恢复所有默认快捷键
            self.shortcut_config = self.get_default_config()
            for id in self.shortcut_config:
                default_key = self.shortcut_config[id]["key"]
                HotkeyCtrl.addHotkey(keysName=default_key, title=f"<<{id}>>")

            self.save_config()
            return "[Success]"

    def is_key_conflict(self, key, exclude_id=None):
        """检查快捷键是否冲突"""
        for id in self.shortcut_config:
            if id == exclude_id:
                continue
            if self.shortcut_config[id]["key"] == key:
                return True
        return False

    def export_config(self, file_path):
        """导出快捷键配置"""
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.shortcut_config, file, ensure_ascii=False, indent=4)
            return "[Success]"
        except Exception as e:
            logger.error(f"导出快捷键配置失败: {e}")
            return f"[Error] 导出失败: {e}"

    def import_config(self, file_path):
        """导入快捷键配置"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                imported_config = json.load(file)

            # 验证导入的配置结构
            if not isinstance(imported_config, dict):
                return "[Error] 配置文件格式错误"

            # 删除所有现有快捷键
            for id in self.shortcut_config:
                key = self.shortcut_config[id]["key"]
                if key:
                    HotkeyCtrl.delHotkey(keysName=key, title=f"<<{id}>>")

            # 应用导入的配置
            self.shortcut_config = imported_config
            for id in self.shortcut_config:
                key = self.shortcut_config[id]["key"]
                if key:
                    HotkeyCtrl.addHotkey(keysName=key, title=f"<<{id}>>")

            self.save_config()
            return "[Success]"
        except Exception as e:
            logger.error(f"导入快捷键配置失败: {e}")
            return f"[Error] 导入失败: {e}"

    # ========================= 【QML调用接口】 =========================

    @Slot(result="QVariant")
    def get_shortcut_config(self):
        """获取快捷键配置"""
        return self.shortcut_config

    @Slot(str, str, result=str)
    def update_shortcut_by_id(self, id, new_key):
        """通过ID更新快捷键"""
        return self.update_shortcut(id, new_key)

    @Slot(str, result=str)
    def reset_shortcut_by_id(self, id):
        """通过ID重置快捷键"""
        return self.reset_shortcut(id)

    @Slot(result=str)
    def reset_all_shortcuts(self):
        """重置所有快捷键"""
        return self.reset_shortcut()

    @Slot(str, result=str)
    def export_config_to_file(self, file_path):
        """导出配置到文件"""
        return self.export_config(file_path)

    @Slot(str, result=str)
    def import_config_from_file(self, file_path):
        """从文件导入配置"""
        return self.import_config(file_path)

    @Slot(str, str, result=bool)
    def check_key_conflict(self, key, exclude_id):
        """检查快捷键是否冲突"""
        return self.is_key_conflict(key, exclude_id)
