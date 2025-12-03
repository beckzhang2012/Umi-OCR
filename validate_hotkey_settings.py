# 验证快捷键设置页面代码逻辑

import sys
import os
import json

# 添加项目路径到Python搜索路径
sys.path.append(os.path.join(os.getcwd(), 'UmiOCR-data', 'py_src'))

# 模拟Qt的Signal和Slot装饰器
class MockSignal:
    def __init__(self):
        pass
    def connect(self, func):
        pass

class MockSlot:
    def __init__(self):
        pass
    def __call__(self, func):
        return func

# 模拟KeyMouseConnector
class MockKeyMouseConnector:
    def __init__(self):
        self.HotkeyCtrl = MockHotkeyCtrl()

class MockHotkeyCtrl:
    def __init__(self):
        self.hotkeys = {}
    def addHotkey(self, keys, callback, trigger_on_release=False):
        self.hotkeys[keys] = callback
    def delHotkey(self, keys, trigger_on_release=False):
        if keys in self.hotkeys:
            del self.hotkeys[keys]

# 模拟TagPageConnector
class MockTagPageConnector:
    def __init__(self):
        self.qml_obj = None

# 导入HotkeySettings类，替换Qt依赖
from tag_pages.HotkeySettings import HotkeySettings

# 替换Qt的Signal和Slot
HotkeySettings.hotkeyConfigChanged = MockSignal()
HotkeySettings.hotkeyConflict = MockSignal()
HotkeySettings.recordingStatusChanged = MockSignal()
HotkeySettings.hotkeyConfigImported = MockSignal()
HotkeySettings.hotkeyConfigExported = MockSignal()

# 创建模拟的连接器
key_mouse_connector = MockKeyMouseConnector()
tag_pages_connector = MockTagPageConnector()

# 创建快捷键设置页面控制器
hotkey_ctrl = HotkeySettings('HotkeySettings', tag_pages_connector)

# 模拟设置KeyMouseConnector
hotkey_ctrl.key_mouse_connector = key_mouse_connector

# 测试获取快捷键配置
print("=== 测试获取快捷键配置 ===")
config = hotkey_ctrl.getHotkeyConfig()
for hotkey_id, hotkey_info in config.items():
    print(f"{hotkey_id}: {hotkey_info['description']} - {hotkey_info['keys']} ({hotkey_info['module']})")

# 测试更新快捷键
print("\n=== 测试更新快捷键 ===")
test_hotkey_id = 'screenshot_ocr'
test_new_keys = 'ctrl+shift+s'
success = hotkey_ctrl.updateHotkey(test_hotkey_id, test_new_keys)
print(f"更新快捷键 {test_hotkey_id} 为 {test_new_keys}: {'成功' if success else '失败'}")

# 测试重置快捷键
print("\n=== 测试重置快捷键 ===")
success = hotkey_ctrl.resetHotkey(test_hotkey_id)
print(f"重置快捷键 {test_hotkey_id}: {'成功' if success else '失败'}")

# 测试检查快捷键冲突
print("\n=== 测试检查快捷键冲突 ===")
conflict_id = hotkey_ctrl._checkConflict('ctrl+alt+a')
if conflict_id:
    print(f"快捷键 'ctrl+alt+a' 与 {config[conflict_id]['description']} 冲突")
else:
    print("快捷键 'ctrl+alt+a' 没有冲突")

# 测试保存配置
print("\n=== 测试保存配置 ===")
hotkey_ctrl.saveConfig()
if os.path.exists(hotkey_ctrl.config_path):
    print(f"配置文件已保存到 {hotkey_ctrl.config_path}")
    with open(hotkey_ctrl.config_path, 'r', encoding='utf-8') as f:
        saved_config = json.load(f)
    print(f"保存的配置包含 {len(saved_config)} 个快捷键")
else:
    print("配置文件保存失败")

# 测试加载配置
print("\n=== 测试加载配置 ===")
hotkey_ctrl.loadConfig()
loaded_config = hotkey_ctrl.getHotkeyConfig()
print(f"加载的配置包含 {len(loaded_config)} 个快捷键")

print("\n=== 验证完成 ===")