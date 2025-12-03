// ===================================================
// =============== 功能页：快捷键设置 ===============
// ===================================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

import ".."
import "../../Widgets"
import "../../ApiManager"

TabPage {
    id: tabPage

    Panel{
        anchors.fill: parent
        anchors.margins: size_.line

        ScrollView {
            anchors.fill: parent
            anchors.margins: size_.spacing
            anchors.leftMargin: size_.line * 2
            anchors.rightMargin: size_.line * 2
            contentWidth: width
            clip: true

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.rightMargin: size_.spacing * 2
                spacing: size_.spacing
                clip: true

                // ==================== 标题 ====================

                Text_ {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: qsTr("快捷键设置")
                    textSize: size_.bigText
                }
                Text_ {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: qsTr("查看、修改和管理所有快捷键配置")
                }
                SplitLine {}

                // ==================== 搜索栏 ====================

                TextField {
                    id: searchField
                    anchors.left: parent.left
                    anchors.right: parent.right
                    placeholderText: qsTr("搜索快捷键名称或功能...")
                    onTextChanged: {
                        filterHotkeys()
                    }
                }

                // ==================== 分组筛选 ====================

                ComboBox {
                    id: groupFilter
                    anchors.left: parent.left
                    anchors.right: parent.right
                    model: [qsTr("全部"), qsTr("OCR操作"), qsTr("窗口操作")]
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        filterHotkeys()
                    }
                }

                SplitLine {}

                // ==================== 快捷键列表 ====================

                Repeater {
                    id: hotkeyRepeater
                    model: filteredHotkeys

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: size_.line * 4
                        color: index % 2 === 0 ? "#f0f0f0" : "#ffffff"
                        radius: 5

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: size_.spacing
                            spacing: size_.spacing

                            Text_ {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 200
                                text: modelData.description
                                elide: Text.ElideRight
                            }

                            Text_ {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 150
                                text: modelData.group
                                elide: Text.ElideRight
                            }

                            Text_ {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 200
                                text: qmlapp.globalConfigs.getValue("hotkeys")[modelData.id].key
                                elide: Text.ElideRight
                            }

                            Button {
                                text: isRecording ? qsTr("录制中...") : qsTr("修改")
                                enabled: !isRecording
                                onClicked: {
                                    recordHotkey(modelData)
                                }
                            }

                            Button {
                                text: qsTr("重置")
                                onClicked: {
                                    resetHotkey(modelData)
                                }
                            }
                        }
                    }
                }

                SplitLine {}

                // ==================== 操作按钮 ====================

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: size_.spacing

                    Button {
                        Layout.fillWidth: true
                        text: qsTr("导出配置")
                        onClicked: {
                            exportHotkeys()
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: qsTr("导入配置")
                        onClicked: {
                            importHotkeys()
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: qsTr("全部重置")
                        onClicked: {
                            resetAllHotkeys()
                        }
                    }
                }
            }
        }
    }

    // 录制状态
    property bool isRecording: false
    property var currentRecordingHotkey: null

    // ==================== 数据模型 ====================

    property var allHotkeys: [
        {id: "screenshot_ocr", description: qsTr("截图OCR"), group: qsTr("截图相关"), defaultHotkey: "Ctrl+Shift+A"},
        {id: "batch_ocr", description: qsTr("批量OCR"), group: qsTr("批量相关"), defaultHotkey: "Ctrl+Shift+B"},
        {id: "quick_ocr", description: qsTr("快速OCR"), group: qsTr("全局设置"), defaultHotkey: "Ctrl+Shift+Q"},
        {id: "minimize_window", description: qsTr("最小化窗口"), group: qsTr("窗口操作"), defaultHotkey: "Ctrl+M"},
        {id: "exit_app", description: qsTr("退出应用"), group: qsTr("窗口操作"), defaultHotkey: "Alt+F4"},
        {id: "open_settings", description: qsTr("打开设置"), group: qsTr("全局设置"), defaultHotkey: "Ctrl+,"}
    ]

    property var filteredHotkeys: allHotkeys

    // ==================== 函数 ====================

    function filterHotkeys() {
        const searchText = searchField.text.toLowerCase()
        const selectedGroup = groupFilter.currentText

        filteredHotkeys = allHotkeys.filter(hotkey => {
            const matchesSearch = hotkey.id.toLowerCase().includes(searchText) ||
                                 hotkey.description.toLowerCase().includes(searchText) ||
                                 hotkey.group.toLowerCase().includes(searchText) ||
                                 (qmlapp.globalConfigs.getValue("hotkeys")[hotkey.id] && qmlapp.globalConfigs.getValue("hotkeys")[hotkey.id].key.toLowerCase().includes(searchText))
            
            const matchesGroup = selectedGroup === qsTr("全部") || hotkey.group === selectedGroup

            return matchesSearch && matchesGroup
        })
    }

    function recordHotkey(hotkey) {
        isRecording = true
        currentRecordingHotkey = hotkey

        // 注册录制事件监听
        PubSubService.subscribe("<<readHotkeyRunning>>", onRecordingRunning)
        PubSubService.subscribe("<<readHotkeyFinish>>", onRecordingFinish)

        // 开始录制
        var result = qmlapp.keyMouse.readHotkey("<<readHotkeyRunning>>", "<<readHotkeyFinish>>")
        if (result !== "[Success]") {
            qmlapp.popup.message(qsTr("录制失败"), result, "error")
            isRecording = false
            currentRecordingHotkey = null
        }
    }

    // 录制中回调
    function onRecordingRunning(hotkeyString) {
        if (currentRecordingHotkey) {
            // 实时更新显示
            var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
            hotkeys[currentRecordingHotkey.id].key = hotkeyString
            qmlapp.globalConfigs.setValue("hotkeys", hotkeys)
        }
    }

    // 录制完成回调
    function onRecordingFinish(hotkeyString) {
        // 取消订阅事件
        PubSubService.unsubscribe("<<readHotkeyRunning>>", onRecordingRunning)
        PubSubService.unsubscribe("<<readHotkeyFinish>>", onRecordingFinish)

        isRecording = false

        if (!hotkeyString) {
            // 用户取消录制
            if (currentRecordingHotkey) {
                var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
                hotkeys[currentRecordingHotkey.id].key = currentRecordingHotkey.defaultHotkey
                qmlapp.globalConfigs.setValue("hotkeys", hotkeys)
            }
            currentRecordingHotkey = null
            return
        }

        // 检查快捷键冲突
        var conflict = checkHotkeyConflict(hotkeyString, currentRecordingHotkey.id)
        if (conflict) {
            qmlapp.popup.message(qsTr("快捷键冲突"), qsTr("该快捷键已被 %1 使用").arg(conflict.description), "error")
            // 恢复原快捷键
            var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
            hotkeys[currentRecordingHotkey.id].key = currentRecordingHotkey.defaultHotkey
            qmlapp.globalConfigs.setValue("hotkeys", hotkeys)
            currentRecordingHotkey = null
            return
        }

        // 保存新快捷键
        var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        hotkeys[currentRecordingHotkey.id].key = hotkeyString
        qmlapp.globalConfigs.setValue("hotkeys", hotkeys)

        qmlapp.popup.simple(qsTr("录制成功"), qsTr("快捷键已更新为: %1").arg(hotkeyString))
        currentRecordingHotkey = null
    }

    // 检查快捷键冲突
    function checkHotkeyConflict(newHotkey, excludeId) {
        var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        for (var i = 0; i < allHotkeys.length; i++) {
            var hotkey = allHotkeys[i]
            if (hotkey.id !== excludeId && hotkeys[hotkey.id].key === newHotkey) {
                return hotkey
            }
        }
        return null
    }

    function resetHotkey(hotkey) {
        var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        hotkeys[hotkey.id].key = hotkey.defaultHotkey
        qmlapp.globalConfigs.setValue("hotkeys", hotkeys)
        qmlapp.popup.simple(qsTr("重置成功"), qsTr("%1 已重置为默认快捷键").arg(hotkey.description))
    }

    function resetAllHotkeys() {
        var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        allHotkeys.forEach(hotkey => {
            hotkeys[hotkey.id].key = hotkey.defaultHotkey
        })
        qmlapp.globalConfigs.setValue("hotkeys", hotkeys)
        qmlapp.popup.simple(qsTr("重置成功"), qsTr("所有快捷键已重置为默认值"))
    }

    // 导出配置
    function exportHotkeys() {
        var hotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        var jsonString = JSON.stringify(hotkeys, null, 2)
        
        // 使用系统对话框保存文件
        var dialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FileDialog { 
            id: exportDialog
            title: qsTr("导出快捷键配置")
            selectExisting: false
            selectFolder: false
            nameFilters: [qsTr("JSON文件 (*.json)")]
            defaultSuffix: "json"
        }', tabPage)
        
        dialog.onAccepted: {
            var file = Qt.openFileUrl(dialog.fileUrl, QIODevice.WriteOnly)
            if (file.open(QIODevice.WriteOnly)) {
                file.write(jsonString)
                file.close()
                qmlapp.popup.simple(qsTr("导出成功"), qsTr("快捷键配置已导出到: %1").arg(dialog.fileUrl.toString()))
            } else {
                qmlapp.popup.message(qsTr("导出失败"), qsTr("无法写入文件"), "error")
            }
            dialog.destroy()
        }
        
        dialog.onRejected: {
            dialog.destroy()
        }
        
        dialog.open()
    }

    // 导入配置
    function importHotkeys() {
        // 使用系统对话框选择文件
        var dialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FileDialog { 
            id: importDialog
            title: qsTr("导入快捷键配置")
            selectExisting: true
            selectFolder: false
            nameFilters: [qsTr("JSON文件 (*.json)")]
        }', tabPage)
        
        dialog.onAccepted: {
            var file = Qt.openFileUrl(dialog.fileUrl, QIODevice.ReadOnly)
            if (file.open(QIODevice.ReadOnly)) {
                var jsonString = file.readAll()
                file.close()
                
                try {
                    var importedHotkeys = JSON.parse(jsonString)
                    
                    // 验证导入的配置格式
                    if (typeof importedHotkeys !== 'object' || importedHotkeys === null) {
                        throw new Error(qsTr("配置文件格式错误"))
                    }
                    
                    // 检查是否有冲突
                    var currentHotkeys = qmlapp.globalConfigs.getValue("hotkeys")
                    var conflicts = []
                    
                    for (var key in importedHotkeys) {
                        if (importedHotkeys.hasOwnProperty(key)) {
                            // 检查是否是有效的快捷键配置
                            if (!importedHotkeys[key] || !importedHotkeys[key].key) {
                                throw new Error(qsTr("配置文件格式错误: 缺少必要字段"))
                            }
                            
                            // 检查冲突
                            for (var currentKey in currentHotkeys) {
                                if (currentKey !== key && currentHotkeys[currentKey].key === importedHotkeys[key].key) {
                                    conflicts.push({
                                        existing: currentHotkeys[currentKey],
                                        imported: importedHotkeys[key]
                                    })
                                }
                            }
                        }
                    }
                    
                    // 如果有冲突，询问用户是否继续
                    if (conflicts.length > 0) {
                        var conflictMsg = qsTr("发现 %1 个快捷键冲突:\n").arg(conflicts.length)
                        conflicts.forEach(function(conflict, index) {
                            conflictMsg += qsTr("%1. %2 (%3) 与 %4 (%5)\n").arg(index + 1)
                                .arg(conflict.existing.description).arg(conflict.existing.key)
                                .arg(conflict.imported.description).arg(conflict.imported.key)
                        })
                        conflictMsg += qsTr("是否继续导入（将覆盖现有配置）？")
                        
                        qmlapp.popup.dialog(qsTr("快捷键冲突"), conflictMsg, function(confirm) {
                            if (confirm) {
                                applyImportedHotkeys(importedHotkeys)
                            }
                        }, "warning", {yesText: qsTr("继续"), noText: qsTr("取消")})
                    } else {
                        applyImportedHotkeys(importedHotkeys)
                    }
                    
                } catch (error) {
                    qmlapp.popup.message(qsTr("导入失败"), error.message, "error")
                }
            } else {
                qmlapp.popup.message(qsTr("导入失败"), qsTr("无法读取文件"), "error")
            }
            dialog.destroy()
        }
        
        dialog.onRejected: {
            dialog.destroy()
        }
        
        dialog.open()
    }

    // 应用导入的快捷键配置
    function applyImportedHotkeys(importedHotkeys) {
        var currentHotkeys = qmlapp.globalConfigs.getValue("hotkeys")
        
        // 合并导入的配置
        for (var key in importedHotkeys) {
            if (importedHotkeys.hasOwnProperty(key) && currentHotkeys.hasOwnProperty(key)) {
                currentHotkeys[key].key = importedHotkeys[key].key
            }
        }
        
        qmlapp.globalConfigs.setValue("hotkeys", currentHotkeys)
        qmlapp.popup.simple(qsTr("导入成功"), qsTr("快捷键配置已导入"))
    }
}