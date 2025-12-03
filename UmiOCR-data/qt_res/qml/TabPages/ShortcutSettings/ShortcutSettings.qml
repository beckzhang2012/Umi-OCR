import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import TagPageConnector 1.0
import KeyMouseConnector 1.0

TabPage {
    id: shortcutSettingsPage
    
    // 页面控制器
    property string controllerKey: ""
    
    // 快捷键配置
    property var shortcutConfig: {}
    
    // 搜索文本
    property string searchText: ""
    
    // 分组筛选
    property string groupFilter: "all"
    
    // 录制状态
    property bool isRecording: false
    property string recordingKey: ""
    property string editingId: ""
    
    // 初始化
    Component.onCompleted: {
        // 获取页面控制器
        controllerKey = tagPageConnector.addPage("ShortcutSettings")
        
        // 加载快捷键配置
        shortcutConfig = tagPageConnector.callPy(controllerKey, "get_shortcut_config", [])
        
        // 监听快捷键录制事件
        pubSubConnector.subscribe("<<readHotkeyRunning>>", onRecordingRunning)
        pubSubConnector.subscribe("<<readHotkeyFinish>>", onRecordingFinish)
    }
    
    // 录制中
    function onRecordingRunning(key) {
        recordingKey = key
    }
    
    // 录制完成
    function onRecordingFinish(key) {
        isRecording = false
        
        if (key) {
            // 更新快捷键
            var result = tagPageConnector.callPy(controllerKey, "update_shortcut_by_id", [editingId, key])
            if (result.startsWith("[Success]")) {
                // 重新加载配置
                shortcutConfig = tagPageConnector.callPy(controllerKey, "get_shortcut_config", [])
            } else {
                // 显示错误消息
                popupManager.show(result)
            }
        }
        
        editingId = ""
        recordingKey = ""
    }
    
    // 开始录制快捷键
    function startRecording(id) {
        editingId = id
        isRecording = true
        
        // 开始录制
        keyMouseConnector.readHotkey()
    }
    
    // 重置快捷键
    function resetShortcut(id) {
        var result = tagPageConnector.callPy(controllerKey, "reset_shortcut_by_id", [id])
        if (result.startsWith("[Success]")) {
            // 重新加载配置
            shortcutConfig = tagPageConnector.callPy(controllerKey, "get_shortcut_config", [])
        } else {
            // 显示错误消息
            popupManager.show(result)
        }
    }
    
    // 重置所有快捷键
    function resetAllShortcuts() {
        var result = tagPageConnector.callPy(controllerKey, "reset_all_shortcuts", [])
        if (result.startsWith("[Success]")) {
            // 重新加载配置
            shortcutConfig = tagPageConnector.callPy(controllerKey, "get_shortcut_config", [])
        } else {
            // 显示错误消息
            popupManager.show(result)
        }
    }
    
    // 导出配置
    function exportConfig() {
        var filePath = fileDialog.saveFile("快捷键配置文件", "*.json")
        if (filePath) {
            var result = tagPageConnector.callPy(controllerKey, "export_config_to_file", [filePath])
            if (result.startsWith("[Success]")) {
                popupManager.show("配置导出成功")
            } else {
                popupManager.show(result)
            }
        }
    }
    
    // 导入配置
    function importConfig() {
        var filePath = fileDialog.openFile("选择快捷键配置文件", "*.json")
        if (filePath) {
            var result = tagPageConnector.callPy(controllerKey, "import_config_from_file", [filePath])
            if (result.startsWith("[Success]")) {
                // 重新加载配置
                shortcutConfig = tagPageConnector.callPy(controllerKey, "get_shortcut_config", [])
                popupManager.show("配置导入成功")
            } else {
                popupManager.show(result)
            }
        }
    }
    
    // 筛选快捷键
    function filterShortcuts() {
        var filtered = []
        
        for (var id in shortcutConfig) {
            var shortcut = shortcutConfig[id]
            var matchesSearch = !searchText || 
                shortcut.description.toLowerCase().includes(searchText.toLowerCase()) || 
                shortcut.key.toLowerCase().includes(searchText.toLowerCase()) || 
                shortcut.module.toLowerCase().includes(searchText.toLowerCase())
            
            var matchesGroup = groupFilter === "all" || shortcut.module === groupFilter
            
            if (matchesSearch && matchesGroup) {
                filtered.push({id: id, ...shortcut})
            }
        }
        
        return filtered
    }
    
    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        
        // 工具栏
        RowLayout {
            id: toolbar
            height: 40
            spacing: 10
            
            // 搜索框
            TextField {
                id: searchField
                placeholderText: "搜索快捷键..."
                onTextChanged: {
                    searchText = text
                }
            }
            
            // 分组筛选
            ComboBox {
                id: groupComboBox
                model: [
                    {text: "全部", value: "all"},
                    {text: "截图相关", value: "截图相关"},
                    {text: "批量相关", value: "批量相关"},
                    {text: "全局设置", value: "全局设置"},
                    {text: "其他", value: "其他"}
                ]
                textRole: "text"
                valueRole: "value"
                onCurrentIndexChanged: {
                    groupFilter = currentValue
                }
            }
            
            // 重置所有
            Button {
                text: "重置所有"
                onClicked: {
                    resetAllShortcuts()
                }
            }
            
            // 导出
            Button {
                text: "导出"
                onClicked: {
                    exportConfig()
                }
            }
            
            // 导入
            Button {
                text: "导入"
                onClicked: {
                    importConfig()
                }
            }
        }
        
        // 快捷键列表
        ListView {
            id: shortcutListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            model: filterShortcuts()
            
            delegate: ShortcutItem {
                id: shortcutItem
                
                width: parent.width
                height: 60
                
                shortcutId: model.id
                description: model.description
                key: model.key
                module: model.module
                
                onEditClicked: {
                    startRecording(model.id)
                }
                
                onResetClicked: {
                    resetShortcut(model.id)
                }
            }
        }
        
        // 录制提示
        Rectangle {
            id: recordingHint
            visible: isRecording
            
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 60
            
            color: "#ff4444"
            
            Text {
                anchors.centerIn: parent
                text: isRecording ? "正在录制快捷键: " + recordingKey : ""
                color: "white"
                font.pixelSize: 16
            }
        }
    }
}

// 快捷键列表项组件
Component {
    id: ShortcutItem
    
    Rectangle {
        id: itemRoot
        
        width: parent.width
        height: 60
        
        color: "transparent"
        
        // 鼠标悬停效果
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            
            onEntered: {
                itemRoot.color = "#f0f0f0"
            }
            
            onExited: {
                itemRoot.color = "transparent"
            }
        }
        
        // 主布局
        RowLayout {
            anchors.fill: parent
            spacing: 10
            
            // 模块
            Text {
                id: moduleText
                text: module
                font.pixelSize: 14
                color: "#666666"
                
                Layout.minimumWidth: 80
                Layout.maximumWidth: 120
            }
            
            // 描述
            Text {
                id: descriptionText
                text: description
                font.pixelSize: 14
                color: "#333333"
                
                Layout.fillWidth: true
            }
            
            // 快捷键
            Rectangle {
                id: keyRect
                
                height: 30
                
                color: "#e0e0e0"
                radius: 5
                
                Text {
                    anchors.centerIn: parent
                    text: key
                    font.pixelSize: 14
                    color: "#333333"
                }
                
                Layout.minimumWidth: 100
                Layout.maximumWidth: 200
            }
            
            // 编辑按钮
            Button {
                id: editButton
                text: "编辑"
                height: 30
                
                onClicked: {
                    editClicked()
                }
            }
            
            // 重置按钮
            Button {
                id: resetButton
                text: "重置"
                height: 30
                
                onClicked: {
                    resetClicked()
                }
            }
        }
    }
}
