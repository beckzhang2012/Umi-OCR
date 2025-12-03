# 测试快捷键设置页面

import sys
import os

# 添加项目路径到Python搜索路径
sys.path.append(os.path.join(os.getcwd(), 'UmiOCR-data', 'py_src'))

from tag_pages.HotkeySettings import HotkeySettings
from tag_pages.tag_pages_connector import TagPageConnector

# 创建页面连接器
connector = TagPageConnector()

# 创建快捷键设置页面控制器
hotkey_ctrl = HotkeySettings('HotkeySettings', connector)

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

print("\n=== 测试完成 ===")