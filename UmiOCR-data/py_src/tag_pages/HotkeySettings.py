# ==================================================== #
# =============== 快捷键设置页面控制器 =============== #
# ==================================================== #

import json
import os
from PySide2.QtCore import QObject, Slot, Signal
from .page import Page
from ..event_bus.key_mouse.keyboard import HotkeyCtrl
from ..utils import pre_configs


class HotkeySettings(Page):
    # 信号定义
    hotkeyChanged = Signal(str, str)  # (hotkeyId, newKeys)
    hotkeyReset = Signal(str)  # (hotkeyId)
    hotkeyConflict = Signal(str, str)  # (hotkeyId, conflictId)
    
    def __init__(self, ctrlKey, controller):
        super().__init__(ctrlKey, controller)
        self._hotkeyConfig = self._loadHotkeyConfig()
        self._defaultHotkeys = self._getDefaultHotkeys()
        
    def _getDefaultHotkeys(self):
        """获取默认快捷键配置"""
        return {
            "screenshot_ocr": {
                "keys": "ctrl+alt+a",
                "description": "截图OCR",
                "module": "截图相关",
                "press": 0
            },
            "quick_ocr": {
                "keys": "ctrl+alt+o",
                "description": "快速OCR",
                "module": "截图相关",
                "press": 0
            },
            "toggle_window": {
                "keys": "ctrl+alt+z",
                "description": "显示/隐藏窗口",
                "module": "全局设置",
                "press": 0
            },
            "exit_app": {
                "keys": "ctrl+q",
                "description": "退出应用",
                "module": "全局设置",
                "press": 0
            },
            "batch_ocr": {
                "keys": "ctrl+shift+b",
                "description": "批量OCR",
                "module": "批量相关",
                "press": 0
            },
            "doc_ocr": {
                "keys": "ctrl+shift+d",
                "description": "文档OCR",
                "module": "批量相关",
                "press": 0
            },
            "qrcode_scan": {
                "keys": "ctrl+shift+q",
                "description": "二维码扫描",
                "module": "二维码",
                "press": 0
            }
        }
        
    def _loadHotkeyConfig(self):
        """加载快捷键配置"""
        config_path = os.path.join(os.getcwd(), ".hotkey_settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载快捷键配置失败: {e}")
        
        # 如果配置文件不存在，返回默认配置
        return self._getDefaultHotkeys()
        
    def _saveHotkeyConfig(self):
        """保存快捷键配置"""
        config_path = os.path.join(os.getcwd(), ".hotkey_settings.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._hotkeyConfig, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存快捷键配置失败: {e}")
            return False
            
    @Slot(result="QVariant")
    def getHotkeyConfig(self):
        """获取快捷键配置"""
        return self._hotkeyConfig
        
    @Slot(str, str, result=bool)
    def updateHotkey(self, hotkeyId, newKeys):
        """更新快捷键"""
        if hotkeyId not in self._hotkeyConfig:
            return False
            
        # 检查快捷键冲突
        conflict_id = self._checkConflict(newKeys, hotkeyId)
        if conflict_id:
            self.hotkeyConflict.emit(hotkeyId, conflict_id)
            return False
            
        # 先删除旧的快捷键注册
        old_keys = self._hotkeyConfig[hotkeyId]["keys"]
        press = self._hotkeyConfig[hotkeyId]["press"]
        HotkeyCtrl.delHotkey(old_keys, hotkeyId, press)
        
        # 更新配置
        self._hotkeyConfig[hotkeyId]["keys"] = newKeys
        
        # 注册新的快捷键
        result = HotkeyCtrl.addHotkey(newKeys, hotkeyId, press)
        if result.startswith("[Success]"):
            if self._saveHotkeyConfig():
                self.hotkeyChanged.emit(hotkeyId, newKeys)
                return True
        
        return False
        
    @Slot(str, result=bool)
    def resetHotkey(self, hotkeyId):
        """重置快捷键为默认值"""
        if hotkeyId not in self._defaultHotkeys:
            return False
            
        default_keys = self._defaultHotkeys[hotkeyId]["keys"]
        return self.updateHotkey(hotkeyId, default_keys)
        
    @Slot(result=bool)
    def resetAllHotkeys(self):
        """重置所有快捷键为默认值"""
        success = True
        for hotkeyId, config in self._defaultHotkeys.items():
            if not self.updateHotkey(hotkeyId, config["keys"]):
                success = False
        return success
        
    @Slot(str, result=str)
    def exportHotkeys(self, exportPath):
        """导出快捷键配置"""
        try:
            with open(exportPath, "w", encoding="utf-8") as f:
                json.dump(self._hotkeyConfig, f, ensure_ascii=False, indent=4)
            return "success"
        except Exception as e:
            return f"导出失败: {str(e)}"
            
    @Slot(str, result=str)
    def importHotkeys(self, importPath):
        """导入快捷键配置"""
        try:
            with open(importPath, "r", encoding="utf-8") as f:
                imported_config = json.load(f)
                
            # 验证导入的配置格式
            for hotkeyId, config in imported_config.items():
                if hotkeyId not in self._hotkeyConfig:
                    continue  # 忽略未知的快捷键
                    
                if "keys" not in config or "description" not in config:
                    return "导入失败: 配置格式错误"
                    
                # 检查冲突
                conflict_id = self._checkConflict(config["keys"], hotkeyId)
                if conflict_id:
                    return f"导入失败: 快捷键 {config['keys']} 与 {self._hotkeyConfig[conflict_id]['description']} 冲突"
                    
            # 应用导入的配置
            for hotkeyId, config in imported_config.items():
                if hotkeyId in self._hotkeyConfig:
                    self._hotkeyConfig[hotkeyId] = config
                    # 更新快捷键注册
                    HotkeyCtrl.delHotkey(self._hotkeyConfig[hotkeyId]["keys"], hotkeyId, self._hotkeyConfig[hotkeyId]["press"])
                    HotkeyCtrl.addHotkey(config["keys"], hotkeyId, config.get("press", 0))
                    
            if self._saveHotkeyConfig():
                return "success"
            else:
                return "导入失败: 保存配置失败"
                
        except Exception as e:
            return f"导入失败: {str(e)}"
            
    def _checkConflict(self, keys, excludeId=None):
        """检查快捷键冲突"""
        for hotkeyId, config in self._hotkeyConfig.items():
            if hotkeyId == excludeId:
                continue
                
            if config["keys"] == keys:
                return hotkeyId
                
        return None
        
    def initHotkeys(self):
        """初始化所有快捷键注册"""
        for hotkeyId, config in self._hotkeyConfig.items():
            HotkeyCtrl.addHotkey(config["keys"], hotkeyId, config["press"])
