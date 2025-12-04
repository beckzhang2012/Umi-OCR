import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import Qt.labs.platform 1.1

Page {
    id: directoryMonitorPage
    title: qsTr("目录监控")
    
    // 控制器对象
    property var controller
    
    // 数据模型
    property var monitors: []
    property var queue: []
    property var queueStats: {"waiting": 0, "processing": 0, "completed": 0, "failed": 0, "total": 0}
    
    // 对话框状态
    property bool addMonitorDialogVisible: false
    property bool addRuleDialogVisible: false
    property var currentMonitor: null
    
    // 初始化
    Component.onCompleted: {
        // 获取控制器
        controller = tagPageConn.addPage("DirectoryMonitor")
        if (controller) {
            tagPageConn.setPageQmlObj(controller, directoryMonitorPage)
            
            // 加载数据
            monitors = tagPageConn.callPy(controller, "get_monitors", [])
            queue = tagPageConn.callPy(controller, "get_queue", [])
            queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
        }
    }
    
    // 信号处理
    signal taskAdded(string taskId)
    signal taskUpdated(string taskId)
    signal taskCompleted(string taskId)
    signal taskFailed(string taskId)
    signal queueUpdated()
    signal monitorStatusChanged(string monitorId, bool isRunning)
    
    // 任务添加信号处理
    onTaskAdded: {
        queue = tagPageConn.callPy(controller, "get_queue", [])
        queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
    }
    
    // 任务更新信号处理
    onTaskUpdated: {
        queue = tagPageConn.callPy(controller, "get_queue", [])
        queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
    }
    
    // 任务完成信号处理
    onTaskCompleted: {
        queue = tagPageConn.callPy(controller, "get_queue", [])
        queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
    }
    
    // 任务失败信号处理
    onTaskFailed: {
        queue = tagPageConn.callPy(controller, "get_queue", [])
        queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
    }
    
    // 队列更新信号处理
    onQueueUpdated: {
        queue = tagPageConn.callPy(controller, "get_queue", [])
        queueStats = tagPageConn.callPy(controller, "get_queue_stats", [])
    }
    
    // 监控状态变化信号处理
    onMonitorStatusChanged: {
        monitors = tagPageConn.callPy(controller, "get_monitors", [])
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        
        // 顶部工具栏
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button_ {
                text: qsTr("添加监控项")
                onClicked: {
                    currentMonitor = null
                    addMonitorDialogVisible = true
                }
            }
            
            Button_ {
                text: qsTr("启动所有监控")
                onClicked: {
                    tagPageConn.callPy(controller, "start_monitoring", [])
                }
            }
            
            Button_ {
                text: qsTr("停止所有监控")
                onClicked: {
                    tagPageConn.callPy(controller, "stop_monitoring", [])
                }
            }
            
            Button_ {
                text: qsTr("清除队列")
                onClicked: {
                    tagPageConn.callPy(controller, "clear_queue", [])
                    queue = []
                    queueStats = {"waiting": 0, "processing": 0, "completed": 0, "failed": 0, "total": 0}
                }
            }
            
            Button_ {
                text: qsTr("清除已处理记录")
                onClicked: {
                    tagPageConn.callPy(controller, "clear_processed_files", [])
                }
            }
        }
        
        // 队列统计
        GridLayout {
            Layout.fillWidth: true
            columns: 5
            spacing: 10
            
            Frame_ {
                Layout.fillWidth: true
                
                ColumnLayout {
                    Text {
                        text: qsTr("等待中")
                        font.bold: true
                    }
                    Text {
                        text: queueStats.waiting
                        font.pixelSize: 24
                        color: "#FF9800"
                    }
                }
            }
            
            Frame_ {
                Layout.fillWidth: true
                
                ColumnLayout {
                    Text {
                        text: qsTr("处理中")
                        font.bold: true
                    }
                    Text {
                        text: queueStats.processing
                        font.pixelSize: 24
                        color: "#2196F3"
                    }
                }
            }
            
            Frame_ {
                Layout.fillWidth: true
                
                ColumnLayout {
                    Text {
                        text: qsTr("已完成")
                        font.bold: true
                    }
                    Text {
                        text: queueStats.completed
                        font.pixelSize: 24
                        color: "#4CAF50"
                    }
                }
            }
            
            Frame_ {
                Layout.fillWidth: true
                
                ColumnLayout {
                    Text {
                        text: qsTr("失败")
                        font.bold: true
                    }
                    Text {
                        text: queueStats.failed
                        font.pixelSize: 24
                        color: "#F44336"
                    }
                }
            }
            
            Frame_ {
                Layout.fillWidth: true
                
                ColumnLayout {
                    Text {
                        text: qsTr("总计")
                        font.bold: true
                    }
                    Text {
                        text: queueStats.total
                        font.pixelSize: 24
                        color: "#607D8B"
                    }
                }
            }
        }
        
        // 监控项列表
        Frame_ {
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            
            ColumnLayout {
                Text {
                    text: qsTr("监控项列表")
                    font.bold: true
                }
                
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: monitors
                    delegate: MonitorItem {
                        monitor: modelData
                        onEdit: {
                            currentMonitor = modelData
                            addMonitorDialogVisible = true
                        }
                        onDelete: {
                            tagPageConn.callPy(controller, "delete_monitor", [modelData.id])
                            monitors = tagPageConn.callPy(controller, "get_monitors", [])
                        }
                        onAddRule: {
                            currentMonitor = modelData
                            addRuleDialogVisible = true
                        }
                    }
                }
            }
        }
        
        // 任务队列
        Frame_ {
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            ColumnLayout {
                Text {
                    text: qsTr("任务队列")
                    font.bold: true
                }
                
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: queue
                    delegate: TaskItem {
                        task: modelData
                        onRetry: {
                            tagPageConn.callPy(controller, "retry_task", [modelData.id])
                        }
                        onSkip: {
                            tagPageConn.callPy(controller, "skip_task", [modelData.id])
                        }
                    }
                }
            }
        }
    }
    
    // 添加监控项对话框
    AddMonitorDialog_ {
        id: addMonitorDialog
        visible: addMonitorDialogVisible
        monitor: currentMonitor
        onAccepted: {
            if (currentMonitor) {
                tagPageConn.callPy(controller, "update_monitor", [currentMonitor.id, JSON.stringify(addMonitorDialog.monitor)])
            } else {
                tagPageConn.callPy(controller, "add_monitor", [JSON.stringify(addMonitorDialog.monitor)])
            }
            monitors = tagPageConn.callPy(controller, "get_monitors", [])
            addMonitorDialogVisible = false
        }
        onRejected: {
            addMonitorDialogVisible = false
        }
    }
    
    // 添加路由规则对话框
    AddRuleDialog_ {
        id: addRuleDialog
        visible: addRuleDialogVisible
        onAccepted: {
            if (currentMonitor) {
                var rules = currentMonitor.rules || []
                rules.push(addRuleDialog.rule)
                tagPageConn.callPy(controller, "update_monitor", [currentMonitor.id, JSON.stringify({"rules": rules})])
                monitors = tagPageConn.callPy(controller, "get_monitors", [])
            }
            addRuleDialogVisible = false
        }
        onRejected: {
            addRuleDialogVisible = false
        }
    }
}

// 监控项列表项组件
Component {
    id: MonitorItem
    
    Rectangle {
        width: parent.width
        height: 60
        color: "#F5F5F5"
        border.color: "#E0E0E0"
        border.width: 1
        radius: 5
        
        property var monitor
        signal edit()
        signal delete()
        signal addRule()
        
        RowLayout {
            anchors.fill: parent
            spacing: 10
            padding: 10
            
            ColumnLayout {
                Layout.fillWidth: true
                
                Text {
                    text: monitor.name
                    font.bold: true
                }
                
                Text {
                    text: monitor.directory
                    font.pixelSize: 12
                    color: "#607D8B"
                }
                
                Text {
                    text: qsTr("文件类型: %1 | 轮询间隔: %2秒 | 递归: %3 | 规则数: %4")
                        .arg(monitor.file_types.join(", "))
                        .arg(monitor.poll_interval)
                        .arg(monitor.recursive ? qsTr("是") : qsTr("否"))
                        .arg((monitor.rules || []).length)
                    font.pixelSize: 10
                    color: "#9E9E9E"
                }
            }
            
            ColumnLayout {
                spacing: 5
                
                Button_ {
                    text: qsTr("编辑")
                    onClicked: edit()
                }
                
                Button_ {
                    text: qsTr("删除")
                    onClicked: delete()
                }
                
                Button_ {
                    text: qsTr("添加规则")
                    onClicked: addRule()
                }
            }
        }
    }
}

// 任务列表项组件
Component {
    id: TaskItem
    
    Rectangle {
        width: parent.width
        height: 80
        color: "#F5F5F5"
        border.color: "#E0E0E0"
        border.width: 1
        radius: 5
        
        property var task
        signal retry()
        signal skip()
        
        RowLayout {
            anchors.fill: parent
            spacing: 10
            padding: 10
            
            ColumnLayout {
                Layout.fillWidth: true
                
                Text {
                    text: task.file_path
                    font.bold: true
                    wrapMode: Text.WrapAnywhere
                }
                
                Text {
                    text: qsTr("模板: %1 | 输出目录: %2 | 优先级: %3")
                        .arg(task.template)
                        .arg(task.output_dir || qsTr("默认"))
                        .arg(task.priority)
                    font.pixelSize: 12
                    color: "#607D8B"
                }
                
                Text {
                    text: qsTr("状态: %1 | 创建时间: %2 | 重试次数: %3/%4")
                        .arg(getStatusText(task.status))
                        .arg(new Date(task.created_time * 1000).toLocaleString())
                        .arg(task.retry_count)
                        .arg(task.max_retries)
                    font.pixelSize: 10
                    color: "#9E9E9E"
                }
                
                Text {
                    text: task.error_message || ""
                    font.pixelSize: 10
                    color: "#F44336"
                    wrapMode: Text.WrapAnywhere
                    visible: task.error_message
                }
            }
            
            ColumnLayout {
                spacing: 5
                
                Button_ {
                    text: qsTr("重试")
                    onClicked: retry()
                    visible: task.status === "failed"
                }
                
                Button_ {
                    text: qsTr("跳过")
                    onClicked: skip()
                    visible: task.status === "waiting" || task.status === "failed"
                }
            }
        }
    }
    
    function getStatusText(status) {
        switch(status) {
            case "waiting": return qsTr("等待中");
            case "processing": return qsTr("处理中");
            case "completed": return qsTr("已完成");
            case "failed": return qsTr("失败");
            default: return status;
        }
    }
}

// 添加监控项对话框组件
Component {
    id: AddMonitorDialog
    
    Dialog_ {
        id: dialog
        title: monitor ? qsTr("编辑监控项") : qsTr("添加监控项")
        width: 600
        height: 400
        
        property var monitor: {
            name: "",
            directory: "",
            file_types: ["*.png", "*.jpg", "*.jpeg"],
            poll_interval: 5,
            recursive: true,
            rules: []
        }
        
        ColumnLayout {
            anchors.fill: parent
            spacing: 10
            padding: 10
            
            TextField_ {
                Layout.fillWidth: true
                placeholderText: qsTr("监控项名称")
                text: dialog.monitor.name
                onTextChanged: {
                    dialog.monitor.name = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                TextField_ {
                    Layout.fillWidth: true
                    placeholderText: qsTr("监控目录")
                    text: dialog.monitor.directory
                    onTextChanged: {
                        dialog.monitor.directory = text
                    }
                }
                
                Button_ {
                    text: qsTr("浏览")
                    onClicked: {
                        var fileDialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FolderDialog_ { title: "选择监控目录"; selectFolder: true; visible: true }', dialog)
                        fileDialog.accepted.connect(function() {
                            dialog.monitor.directory = fileDialog.fileUrl.toString().replace("file:///", "").replace(/%20/g, " ")
                            fileDialog.destroy()
                        })
                        fileDialog.rejected.connect(function() {
                            fileDialog.destroy()
                        })
                    }
                }
            }
            
            TextField_ {
                Layout.fillWidth: true
                placeholderText: qsTr("文件类型（逗号分隔，如：*.png,*.jpg）")
                text: dialog.monitor.file_types.join(",")
                onTextChanged: {
                    dialog.monitor.file_types = text.split(",").map(function(type) { return type.trim() }).filter(function(type) { return type.length > 0 })
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                TextField_ {
                    Layout.fillWidth: true
                    placeholderText: qsTr("轮询间隔（秒）")
                    text: dialog.monitor.poll_interval.toString()
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onTextChanged: {
                        var interval = parseInt(text)
                        if (!isNaN(interval) && interval > 0) {
                            dialog.monitor.poll_interval = interval
                        }
                    }
                }
                
                CheckBox_ {
                    text: qsTr("递归子目录")
                    checked: dialog.monitor.recursive
                    onCheckedChanged: {
                        dialog.monitor.recursive = checked
                    }
                }
            }
            
            Text {
                text: qsTr("路由规则")
                font.bold: true
            }
            
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: dialog.monitor.rules
                delegate: Text {
                    text: qsTr("类型: %1 | 模式: %2 | 模板: %3 | 输出目录: %4")
                        .arg(modelData.type)
                        .arg(modelData.pattern)
                        .arg(modelData.template)
                        .arg(modelData.output_dir || qsTr("默认"))
                    font.pixelSize: 12
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (!dialog.monitor.name || !dialog.monitor.directory) {
                messageDialog.show(qsTr("请填写监控项名称和目录"), qsTr("错误"))
                return
            }
            dialog.accept()
        }
    }
}

// 添加路由规则对话框组件
Component {
    id: AddRuleDialog
    
    Dialog_ {
        id: dialog
        title: qsTr("添加路由规则")
        width: 500
        height: 300
        
        property var rule: {
            type: "filename_regex",
            pattern: "",
            template: "default",
            output_dir: "",
            priority: 0
        }
        
        ColumnLayout {
            anchors.fill: parent
            spacing: 10
            padding: 10
            
            ComboBox_ {
                Layout.fillWidth: true
                model: [
                    {text: qsTr("文件名正则"), value: "filename_regex"},
                    {text: qsTr("文件大小"), value: "file_size"},
                    {text: qsTr("修改时间"), value: "modified_time"}
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: 0
                onCurrentIndexChanged: {
                    dialog.rule.type = currentValue
                }
            }
            
            TextField_ {
                Layout.fillWidth: true
                placeholderText: qsTr("模式")
                text: dialog.rule.pattern
                onTextChanged: {
                    dialog.rule.pattern = text
                }
            }
            
            TextField_ {
                Layout.fillWidth: true
                placeholderText: qsTr("OCR模板")
                text: dialog.rule.template
                onTextChanged: {
                    dialog.rule.template = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                TextField_ {
                    Layout.fillWidth: true
                    placeholderText: qsTr("输出目录")
                    text: dialog.rule.output_dir
                    onTextChanged: {
                        dialog.rule.output_dir = text
                    }
                }
                
                Button_ {
                    text: qsTr("浏览")
                    onClicked: {
                        var fileDialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FolderDialog_ { title: "选择输出目录"; selectFolder: true; visible: true }', dialog)
                        fileDialog.accepted.connect(function() {
                            dialog.rule.output_dir = fileDialog.fileUrl.toString().replace("file:///", "").replace(/%20/g, " ")
                            fileDialog.destroy()
                        })
                        fileDialog.rejected.connect(function() {
                            fileDialog.destroy()
                        })
                    }
                }
            }
            
            TextField_ {
                Layout.fillWidth: true
                placeholderText: qsTr("优先级")
                text: dialog.rule.priority.toString()
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextChanged: {
                    var priority = parseInt(text)
                    if (!isNaN(priority)) {
                        dialog.rule.priority = priority
                    }
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (!dialog.rule.pattern) {
                messageDialog.show(qsTr("请填写模式"), qsTr("错误"))
                return
            }
            dialog.accept()
        }
    }
}

// 消息对话框组件
Component {
    id: messageDialog
    
    MessageDialog_ {
        function show(text, title) {
            this.text = text
            this.title = title
            this.visible = true
        }
    }
}
