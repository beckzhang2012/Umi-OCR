import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import QtQuick.Window 2.15

import "../components" as Components

Page {
    id: directoryMonitorPage
    
    // 控制器
    property var controller
    
    // 页面状态
    property bool isRunning: false
    property var taskStats: {}
    
    // 对话框状态
    property bool showAddMonitorDialog: false
    property bool showEditMonitorDialog: false
    property var currentMonitorItem: null
    
    // 表单数据
    property var formData: {
        name: "",
        directory: "",
        fileTypes: [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
        pollingInterval: 60,
        recursiveLevel: 0,
        enabled: true,
        routes: []
    }
    
    // 初始化
    Component.onCompleted: {
        if (controller) {
            controller.monitorItemsChanged.connect(refreshMonitorItems)
            controller.fileTasksChanged.connect(refreshFileTasks)
            controller.taskStatsChanged.connect(refreshTaskStats)
            controller.alertTriggered.connect(showAlert)
            
            refreshMonitorItems()
            refreshFileTasks()
            refreshTaskStats()
        }
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        
        // 页面标题
        Components.PageTitle {
            title: qsTr("目录监控")
            subtitle: qsTr("自动监控指定目录，新图片出现时自动分配到OCR任务")
        }
        
        // 控制面板
        RowLayout {
            Layout.fillWidth: true
            
            Button {
                text: isRunning ? qsTr("停止监控") : qsTr("启动监控")
                onClicked: {
                    if (isRunning) {
                        controller.stopMonitor()
                    } else {
                        controller.startMonitor()
                    }
                    isRunning = !isRunning
                }
                enabled: monitorItemsModel.count > 0
            }
            
            Button {
                text: qsTr("添加监控项")
                onClicked: {
                    formData = {
                        name: "",
                        directory: "",
                        fileTypes: [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
                        pollingInterval: 60,
                        recursiveLevel: 0,
                        enabled: true,
                        routes: []
                    }
                    currentMonitorItem = null
                    showAddMonitorDialog = true
                }
            }
        }
        
        // 统计卡片
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            
            Components.StatCard {
                title: qsTr("等待中")
                value: taskStats.waiting || 0
                color: "#667eea"
            }
            
            Components.StatCard {
                title: qsTr("处理中")
                value: taskStats.processing || 0
                color: "#f59e0b"
            }
            
            Components.StatCard {
                title: qsTr("已完成")
                value: taskStats.completed || 0
                color: "#10b981"
            }
            
            Components.StatCard {
                title: qsTr("失败")
                value: taskStats.failed || 0
                color: "#ef4444"
            }
            
            Components.StatCard {
                title: qsTr("总计")
                value: taskStats.total || 0
                color: "#6b7280"
            }
        }
        
        // 监控项列表
        Section {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 200
            
            header: Text {
                text: qsTr("监控项列表")
                font.pixelSize: 18
                font.bold: true
                padding: 8
            }
            
            ListView {
                id: monitorItemsListView
                anchors.fill: parent
                model: ListModel {
                    id: monitorItemsModel
                }
                delegate: monitorItemDelegate
            }
        }
        
        // 文件任务列表
        Section {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 300
            
            header: Text {
                text: qsTr("文件任务列表")
                font.pixelSize: 18
                font.bold: true
                padding: 8
            }
            
            ListView {
                id: fileTasksListView
                anchors.fill: parent
                model: ListModel {
                    id: fileTasksModel
                }
                delegate: fileTaskDelegate
            }
        }
    }
    
    // 监控项委托
    Component {
        id: monitorItemDelegate
        
        Item {
            width: parent.width
            height: 60
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 12
                
                CheckBox {
                    checked: model.enabled
                    onCheckedChanged: {
                        controller.toggle_monitor_item(model.id)
                    }
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    
                    Text {
                        text: model.name
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    
                    Text {
                        text: model.directory
                        font.pixelSize: 12
                        color: "#6b7280"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
                
                RowLayout {
                    spacing: 8
                    
                    Button {
                        text: qsTr("编辑")
                        onClicked: {
                            currentMonitorItem = model
                            formData = {
                                name: model.name,
                                directory: model.directory,
                                fileTypes: model.fileTypes,
                                pollingInterval: model.pollingInterval,
                                recursiveLevel: model.recursiveLevel,
                                enabled: model.enabled,
                                routes: model.routes
                            }
                            showEditMonitorDialog = true
                        }
                    }
                    
                    Button {
                        text: qsTr("删除")
                        color: "#ef4444"
                        onClicked: {
                            if (confirmDialog.confirm(qsTr("确定要删除这个监控项吗？"))) {
                                controller.delete_monitor_item(model.id)
                            }
                        }
                    }
                }
            }
        }
    }
    
    // 文件任务委托
    Component {
        id: fileTaskDelegate
        
        Item {
            width: parent.width
            height: 80
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    
                    Text {
                        text: model.file_path.split("/").pop().split("\\").pop()
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    
                    Components.StatusBadge {
                        text: getStatusText(model.status)
                        color: getStatusColor(model.status)
                    }
                }
                
                Text {
                    text: model.file_path
                    font.pixelSize: 12
                    color: "#6b7280"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    Text {
                        text: model.created_at
                        font.pixelSize: 11
                        color: "#9ca3af"
                    }
                    
                    Item {
                        Layout.fillWidth: true
                    }
                    
                    Button {
                        text: qsTr("重试")
                        enabled: model.status === "failed"
                        onClicked: {
                            controller.retry_file_task(model.id)
                        }
                    }
                    
                    Button {
                        text: qsTr("跳过")
                        enabled: model.status === "waiting" || model.status === "failed"
                        onClicked: {
                            controller.skip_file_task(model.id)
                        }
                    }
                    
                    Button {
                        text: qsTr("删除")
                        color: "#ef4444"
                        onClicked: {
                            controller.delete_file_task(model.id)
                        }
                    }
                }
            }
        }
    }
    
    // 添加监控项对话框
    Components.Dialog {
        id: addMonitorDialog
        visible: showAddMonitorDialog
        title: qsTr("添加监控项")
        width: 600
        height: 500
        
        onAccepted: {
            controller.add_monitor_item(formData)
            showAddMonitorDialog = false
        }
        
        onRejected: {
            showAddMonitorDialog = false
        }
        
        contentItem: MonitorItemForm {
            formData: directoryMonitorPage.formData
        }
    }
    
    // 编辑监控项对话框
    Components.Dialog {
        id: editMonitorDialog
        visible: showEditMonitorDialog
        title: qsTr("编辑监控项")
        width: 600
        height: 500
        
        onAccepted: {
            if (currentMonitorItem) {
                controller.update_monitor_item(currentMonitorItem.id, formData)
            }
            showEditMonitorDialog = false
        }
        
        onRejected: {
            showEditMonitorDialog = false
        }
        
        contentItem: MonitorItemForm {
            formData: directoryMonitorPage.formData
        }
    }
    
    // 确认对话框
    Components.ConfirmDialog {
        id: confirmDialog
    }
    
    // 告警对话框
    Components.AlertDialog {
        id: alertDialog
    }
    
    // 辅助函数
    function getStatusText(status) {
        switch(status) {
            case "waiting": return qsTr("等待中")
            case "processing": return qsTr("处理中")
            case "completed": return qsTr("已完成")
            case "failed": return qsTr("失败")
            default: return status
        }
    }
    
    function getStatusColor(status) {
        switch(status) {
            case "waiting": return "#667eea"
            case "processing": return "#f59e0b"
            case "completed": return "#10b981"
            case "failed": return "#ef4444"
            default: return "#6b7280"
        }
    }
    
    // 刷新监控项列表
    function refreshMonitorItems() {
        if (controller) {
            var items = controller.get_monitor_items()
            monitorItemsModel.clear()
            for (var i = 0; i < items.length; i++) {
                monitorItemsModel.append(items[i])
            }
        }
    }
    
    // 刷新文件任务列表
    function refreshFileTasks() {
        if (controller) {
            var tasks = controller.get_file_tasks()
            fileTasksModel.clear()
            for (var i = 0; i < tasks.length; i++) {
                fileTasksModel.append(tasks[i])
            }
        }
    }
    
    // 刷新任务统计
    function refreshTaskStats() {
        if (controller) {
            taskStats = controller.get_task_stats()
        }
    }
    
    // 显示告警
    function showAlert(type, message) {
        alertDialog.show(message, type)
    }
}

// 监控项表单组件
Component {
    id: MonitorItemForm
    
    property var formData
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        
        // 名称
        TextField {
            Layout.fillWidth: true
            placeholderText: qsTr("监控项名称")
            text: formData.name
            onTextChanged: formData.name = text
        }
        
        // 目录选择
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("监控目录")
                text: formData.directory
                readOnly: true
            }
            
            Button {
                text: qsTr("浏览")
                onClicked: {
                    folderDialog.open()
                }
            }
        }
        
        // 文件类型
        TextField {
            Layout.fillWidth: true
            placeholderText: qsTr("文件类型（逗号分隔）")
            text: formData.fileTypes.join(", ")
            onTextChanged: {
                formData.fileTypes = text.split(",").map(function(item) { return item.trim() }).filter(function(item) { return item !== "" })
            }
        }
        
        // 轮询间隔
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("轮询间隔（秒）")
                text: formData.pollingInterval.toString()
                inputMethodHints: Qt.ImhDigitsOnly
                onTextChanged: {
                    var value = parseInt(text)
                    if (!isNaN(value) && value > 0) {
                        formData.pollingInterval = value
                    }
                }
            }
            
            Text {
                text: qsTr("秒")
                verticalAlignment: Text.AlignVCenter
            }
        }
        
        // 递归层级
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("递归层级（-1表示无限）")
                text: formData.recursiveLevel.toString()
                inputMethodHints: Qt.ImhDigitsOnly
                onTextChanged: {
                    var value = parseInt(text)
                    if (!isNaN(value)) {
                        formData.recursiveLevel = value
                    }
                }
            }
        }
        
        // 启用状态
        CheckBox {
            text: qsTr("启用监控项")
            checked: formData.enabled
            onCheckedChanged: formData.enabled = checked
        }
    }
}

// 文件夹选择对话框
FolderDialog {
    id: folderDialog
    title: qsTr("选择监控目录")
    selectFolder: true
    
    onAccepted: {
        directoryMonitorPage.formData.directory = fileUrl.toString().replace("file:///", "").replace(/\//g, "\\")
    }
}