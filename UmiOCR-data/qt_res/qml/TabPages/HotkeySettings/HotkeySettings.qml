import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import TagPageConnector 1.0
import KeyMouseConnector 1.0

Item {
    id: hotkeySettingsPage
    property string ctrlKey: ""
    property TagPageConnector connector: null
    property var hotkeyConfig: ({})
    property var filteredHotkeys: ({})
    property string searchText: ""
    property string selectedGroup: "all"
    
    // 键盘鼠标连接器
    KeyMouseConnector { id: keyMouseConn }
    
    // 初始化
    function showPage() {
        loadHotkeyConfig()
    }
    
    function loadHotkeyConfig() {
        hotkeyConfig = connector.callQml(ctrlKey, "getHotkeyConfig")
        filterHotkeys()
    }
    
    function filterHotkeys() {
        filteredHotkeys = {}
        for (let id in hotkeyConfig) {
            let hotkey = hotkeyConfig[id]
            let matchesSearch = searchText === "" || 
                hotkey.description.toLowerCase().includes(searchText.toLowerCase()) ||
                hotkey.keys.toLowerCase().includes(searchText.toLowerCase())
            
            let matchesGroup = selectedGroup === "all" || hotkey.module === selectedGroup
            
            if (matchesSearch && matchesGroup) {
                filteredHotkeys[id] = hotkey
            }
        }
    }
    
    function startRecording(hotkeyId) {
        // 停止其他正在录制的项目
        for (let id in hotkeyConfig) {
            if (hotkeyConfig[id].isRecording) {
                hotkeyConfig[id].isRecording = false
            }
        }
        
        // 开始录制当前项目
        hotkeyConfig[hotkeyId].isRecording = true
        
        // 调用Python开始录制快捷键
        let result = keyMouseConn.readHotkey("<<readHotkeyRunning>>", "<<readHotkeyFinish>>")
        if (!result.startsWith("[Success]")) {
            console.error("开始录制快捷键失败:", result)
            hotkeyConfig[hotkeyId].isRecording = false
        }
    }
    
    function stopRecording(hotkeyId) {
        hotkeyConfig[hotkeyId].isRecording = false
    }
    
    function updateHotkey(hotkeyId, newKeys) {
        if (newKeys === "") {
            // 用户取消录制
            stopRecording(hotkeyId)
            return
        }
        
        // 调用Python更新快捷键
        let success = connector.callQml(ctrlKey, "updateHotkey", hotkeyId, newKeys)
        if (success) {
            hotkeyConfig[hotkeyId].keys = newKeys
            stopRecording(hotkeyId)
        } else {
            console.error("更新快捷键失败")
        }
    }
    
    function resetHotkey(hotkeyId) {
        let success = connector.callQml(ctrlKey, "resetHotkey", hotkeyId)
        if (success) {
            loadHotkeyConfig()
        }
    }
    
    function resetAllHotkeys() {
        if (confirm(qsTr("确定要重置所有快捷键为默认值吗？"))) {
            let success = connector.callQml(ctrlKey, "resetAllHotkeys")
            if (success) {
                loadHotkeyConfig()
            }
        }
    }
    
    function exportHotkeys() {
        let filePath = Qt.openUrlExternally("file:///" + Qt.createQmlObject("import QtQuick.Dialogs 1.3; FileDialog { id: fd; title: '导出快捷键配置'; nameFilters: ['JSON Files (*.json)']; selectExisting: false }", hotkeySettingsPage).fileUrl)
        if (filePath) {
            let result = connector.callQml(ctrlKey, "exportHotkeys", filePath)
            if (result === "success") {
                messageDialog.show(qsTr("导出成功"), qsTr("快捷键配置已成功导出"))
            } else {
                messageDialog.show(qsTr("导出失败"), result)
            }
        }
    }
    
    function importHotkeys() {
        let filePath = Qt.openUrlExternally("file:///" + Qt.createQmlObject("import QtQuick.Dialogs 1.3; FileDialog { id: fd; title: '导入快捷键配置'; nameFilters: ['JSON Files (*.json)']; selectExisting: true }", hotkeySettingsPage).fileUrl)
        if (filePath) {
            let result = connector.callQml(ctrlKey, "importHotkeys", filePath)
            if (result === "success") {
                messageDialog.show(qsTr("导入成功"), qsTr("快捷键配置已成功导入"))
                loadHotkeyConfig()
            } else {
                messageDialog.show(qsTr("导入失败"), result)
            }
        }
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 16
        padding: 16
        
        // 标题和操作按钮
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            
            Label {
                text: qsTr("快捷键设置")
                font.pixelSize: 24
                font.bold: true
            }
            
            Item {
                Layout.fillWidth: true
            }
            
            Button {
                text: qsTr("导出")
                onClicked: exportHotkeys()
            }
            
            Button {
                text: qsTr("导入")
                onClicked: importHotkeys()
            }
            
            Button {
                text: qsTr("重置所有")
                onClicked: resetAllHotkeys()
            }
        }
        
        // 搜索框
        TextField {
            Layout.fillWidth: true
            placeholderText: qsTr("搜索快捷键或功能...")
            text: searchText
            onTextChanged: {
                searchText = text
                filterHotkeys()
            }
        }
        
        // 分组筛选
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            Label {
                text: qsTr("分组:")
                verticalAlignment: Text.AlignVCenter
            }
            
            ComboBox {
                model: [qsTr("全部"), qsTr("截图相关"), qsTr("批量相关"), qsTr("全局设置"), qsTr("二维码")]
                currentIndex: 0
                onCurrentTextChanged: {
                    if (currentText === qsTr("全部")) {
                        selectedGroup = "all"
                    } else {
                        selectedGroup = currentText
                    }
                    filterHotkeys()
                }
            }
        }
        
        // 快捷键列表
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            TableView {
                id: hotkeyTable
                model: Object.keys(filteredHotkeys)
                
                TableViewColumn {
                    role: "description"
                    title: qsTr("功能说明")
                    width: 250
                }
                
                TableViewColumn {
                    role: "module"
                    title: qsTr("所属模块")
                    width: 150
                }
                
                TableViewColumn {
                    role: "keys"
                    title: qsTr("当前绑定")
                    width: 200
                }
                
                TableViewColumn {
                    role: "actions"
                    title: qsTr("操作")
                    width: 150
                }
                
                delegate: Item {
                    id: delegateItem
                    width: hotkeyTable.width
                    height: 40
                    
                    property string hotkeyId: modelData
                    property var hotkey: filteredHotkeys[hotkeyId]
                    
                    Label {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        text: hotkey.description
                        width: 234
                        elide: Text.ElideRight
                    }
                    
                    Label {
                        anchors.left: parent.left
                        anchors.leftMargin: 266
                        anchors.verticalCenter: parent.verticalCenter
                        text: hotkey.module
                        width: 134
                        elide: Text.ElideRight
                    }
                    
                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 410
                        anchors.verticalCenter: parent.verticalCenter
                        width: 184
                        height: 30
                        color: hotkey.isRecording ? "#ff6b6b" : "#f0f0f0"
                        border.color: "#ccc"
                        border.width: 1
                        radius: 4
                        
                        Text {
                            anchors.centerIn: parent
                            text: hotkey.isRecording ? qsTr("录制中...") : hotkey.keys
                            color: hotkey.isRecording ? "white" : "black"
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (!hotkey.isRecording) {
                                    startRecording(hotkeyId)
                                }
                            }
                        }
                    }
                    
                    RowLayout {
                        anchors.left: parent.left
                        anchors.leftMargin: 604
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        
                        Button {
                            text: qsTr("重置")
                            onClicked: resetHotkey(hotkeyId)
                            enabled: !hotkey.isRecording
                        }
                    }
                }
            }
        }
    }
    
    // 消息对话框
    MessageDialog {
        id: messageDialog
        title: ""
        text: ""
        standardButtons: StandardButton.Ok
    }
    
    // 订阅快捷键录制事件
    Connections {
        target: pubSubService
        
        function onPublish(topic, data) {
            if (topic === "<<readHotkeyRunning>>") {
                // 更新录制中的快捷键显示
                for (let id in hotkeyConfig) {
                    if (hotkeyConfig[id].isRecording) {
                        hotkeyConfig[id].keys = data
                        hotkeyTable.update()
                    }
                }
            } else if (topic === "<<readHotkeyFinish>>") {
                // 完成录制
                for (let id in hotkeyConfig) {
                    if (hotkeyConfig[id].isRecording) {
                        updateHotkey(id, data)
                        hotkeyTable.update()
                    }
                }
            }
        }
    }
}