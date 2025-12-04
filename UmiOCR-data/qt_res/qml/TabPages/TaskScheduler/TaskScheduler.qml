// ===============================================
// =============== 任务排程页面 ===============
// ===============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import "../../Widgets" as Widgets
import "../../Configs" as Configs

Widget_ { 
    id: tabPage
    property string ctrlKey
    property var connector
    property var tasks: []
    property var selectedTask: null
    property var executionLogs: []

    // ========================= 【UI布局】 =========================

    ColumnLayout {
        anchors.fill: parent
        spacing: size_.spacing

        // 顶部工具栏
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: size_.spacing
            Layout.leftMargin: size_.spacing
            Layout.rightMargin: size_.spacing

            Button_ {
                text: qsTr("新建任务")
                onClicked: createTaskDialog.open()
            }

            Button_ {
                text: qsTr("编辑任务")
                enabled: selectedTask !== null
                onClicked: editTaskDialog.open()
            }

            Button_ {
                text: qsTr("删除任务")
                enabled: selectedTask !== null
                onClicked: deleteSelectedTask()
            }

            Button_ {
                text: qsTr("立即执行")
                enabled: selectedTask !== null
                onClicked: executeTaskNow()
            }

            Button_ {
                text: qsTr("导出日志")
                onClicked: exportLogsDialog.open()
            }
        }

        // 任务列表
        Widgets.TableView_ {
            id: tasksTable
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: size_.spacing
            Layout.rightMargin: size_.spacing

            model: ListModel {
                id: tasksModel
            }

            columns: [
                { title: qsTr("任务名称"), property: "name", width: 200 },
                { title: qsTr("任务类型"), property: "task_type", width: 120 },
                { title: qsTr("调度类型"), property: "schedule_type", width: 120 },
                { title: qsTr("下次执行"), property: "next_execution", width: 200 },
                { title: qsTr("上次执行"), property: "last_execution", width: 200 },
                { title: qsTr("状态"), property: "status", width: 100 }
            ]

            onCurrentRowChanged: {
                if (currentRow >= 0 && currentRow < tasksModel.count) {
                    selectedTask = tasksModel.get(currentRow)
                } else {
                    selectedTask = null
                }
            }
        }
    }

    // ========================= 【对话框】 =========================

    // 新建/编辑任务对话框
    Widgets.Dialog_ {
        id: createTaskDialog
        title: selectedTask ? qsTr("编辑任务") : qsTr("新建任务")
        width: 600
        height: 500

        ColumnLayout {
            anchors.fill: parent
            spacing: size_.spacing

            // 任务名称
            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("任务名称")
                text: selectedTask ? selectedTask.name : ""
                onTextChanged: {
                    if (selectedTask) selectedTask.name = text
                }
            }

            // 任务类型
            Widgets.ComboBox_ {
                Layout.fillWidth: true
                label: qsTr("任务类型")
                model: [qsTr("批量OCR"), qsTr("截图OCR")]
                currentIndex: selectedTask ? (selectedTask.task_type === 'batch_ocr' ? 0 : 1) : 0
                onCurrentIndexChanged: {
                    if (selectedTask) selectedTask.task_type = currentIndex === 0 ? 'batch_ocr' : 'screenshot_ocr'
                }
            }

            // 调度类型
            Widgets.ComboBox_ {
                id: scheduleTypeCombo
                Layout.fillWidth: true
                label: qsTr("调度类型")
                model: [qsTr("一次性"), qsTr("每天"), qsTr("每周"), qsTr("自定义Cron")]
                currentIndex: selectedTask ? getScheduleTypeIndex(selectedTask.schedule_type) : 0
                onCurrentIndexChanged: updateScheduleConfigUI()
            }

            // 调度配置区域
            Item {
                id: scheduleConfigArea
                Layout.fillWidth: true
                height: childrenRect.height
            }

            // OCR模板
            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("OCR模板")
                text: selectedTask ? selectedTask.ocr_template : ""
                onTextChanged: {
                    if (selectedTask) selectedTask.ocr_template = text
                }
            }

            // 处理文件夹
            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("处理文件夹")
                text: selectedTask ? selectedTask.folders.join('; ') : ""
                placeholderText: qsTr("多个文件夹用分号分隔")
                onTextChanged: {
                    if (selectedTask) selectedTask.folders = text.split(';').map(f => f.trim()).filter(f => f)
                }
            }

            // 失败重试策略
            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("最大重试次数")
                text: selectedTask ? selectedTask.retry_policy.max_retries.toString() : "0"
                inputMethodHints: Qt.ImhDigitsOnly
                onTextChanged: {
                    if (selectedTask) selectedTask.retry_policy.max_retries = parseInt(text) || 0
                }
            }

            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("重试间隔(秒)")
                text: selectedTask ? selectedTask.retry_policy.retry_interval.toString() : "60"
                inputMethodHints: Qt.ImhDigitsOnly
                onTextChanged: {
                    if (selectedTask) selectedTask.retry_policy.retry_interval = parseInt(text) || 60
                }
            }

            // 并发限制
            Widgets.TextField_ {
                Layout.fillWidth: true
                label: qsTr("并发限制")
                text: selectedTask ? selectedTask.concurrency_limit.toString() : "1"
                inputMethodHints: Qt.ImhDigitsOnly
                onTextChanged: {
                    if (selectedTask) selectedTask.concurrency_limit = parseInt(text) || 1
                }
            }

            // 底部按钮
            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight
                spacing: size_.spacing

                Button_ {
                    text: qsTr("取消")
                    onClicked: createTaskDialog.close()
                }

                Button_ {
                    text: qsTr("保存")
                    onClicked: saveTask()
                }
            }
        }
    }

    // 导出日志对话框
    FileDialog {
        id: exportLogsDialog
        title: qsTr("导出执行日志")
        selectExisting: false
        selectFolder: false
        nameFilters: [qsTr("JSON文件 (*.json)")]
        defaultSuffix: "json"

        onAccepted: {
            if (fileUrls.length > 0) {
                const filePath = fileUrls[0].toString().replace('file:///', '')
                connector.exportLogs(ctrlKey, filePath)
            }
        }
    }

    // ========================= 【函数】 =========================

    function getScheduleTypeIndex(scheduleType) {
        switch (scheduleType) {
            case 'once': return 0
            case 'daily': return 1
            case 'weekly': return 2
            case 'cron': return 3
            default: return 0
        }
    }

    function updateScheduleConfigUI() {
        // 清空之前的配置UI
        scheduleConfigArea.children = []

        const index = scheduleTypeCombo.currentIndex
        
        if (index === 0) {
            // 一次性任务
            Widgets.TextField_ {
                parent: scheduleConfigArea
                Layout.fillWidth: true
                label: qsTr("执行时间")
                text: selectedTask && selectedTask.schedule_config.execution_time ? 
                    selectedTask.schedule_config.execution_time : 
                    new Date().toISOString().slice(0, 16)
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextChanged: {
                    if (selectedTask) selectedTask.schedule_config.execution_time = text
                }
            }
        } else if (index === 1) {
            // 每天执行
            RowLayout {
                parent: scheduleConfigArea
                Layout.fillWidth: true
                spacing: size_.spacing

                Widgets.TextField_ {
                    Layout.fillWidth: true
                    label: qsTr("小时")
                    text: selectedTask && selectedTask.schedule_config.hour ? 
                        selectedTask.schedule_config.hour.toString() : "0"
                    inputMethodHints: Qt.ImhDigitsOnly
                    onTextChanged: {
                        if (selectedTask) selectedTask.schedule_config.hour = parseInt(text) || 0
                    }
                }

                Widgets.TextField_ {
                    Layout.fillWidth: true
                    label: qsTr("分钟")
                    text: selectedTask && selectedTask.schedule_config.minute ? 
                        selectedTask.schedule_config.minute.toString() : "0"
                    inputMethodHints: Qt.ImhDigitsOnly
                    onTextChanged: {
                        if (selectedTask) selectedTask.schedule_config.minute = parseInt(text) || 0
                    }
                }
            }
        } else if (index === 2) {
            // 每周执行
            ColumnLayout {
                parent: scheduleConfigArea
                Layout.fillWidth: true
                spacing: size_.spacing

                Widgets.ComboBox_ {
                    Layout.fillWidth: true
                    label: qsTr("星期几")
                    model: [qsTr("周一"), qsTr("周二"), qsTr("周三"), qsTr("周四"), qsTr("周五"), qsTr("周六"), qsTr("周日")]
                    currentIndex: selectedTask && selectedTask.schedule_config.day_of_week ? 
                        selectedTask.schedule_config.day_of_week : 0
                    onCurrentIndexChanged: {
                        if (selectedTask) selectedTask.schedule_config.day_of_week = currentIndex
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: size_.spacing

                    Widgets.TextField_ {
                        Layout.fillWidth: true
                        label: qsTr("小时")
                        text: selectedTask && selectedTask.schedule_config.hour ? 
                            selectedTask.schedule_config.hour.toString() : "0"
                        inputMethodHints: Qt.ImhDigitsOnly
                        onTextChanged: {
                            if (selectedTask) selectedTask.schedule_config.hour = parseInt(text) || 0
                        }
                    }

                    Widgets.TextField_ {
                        Layout.fillWidth: true
                        label: qsTr("分钟")
                        text: selectedTask && selectedTask.schedule_config.minute ? 
                            selectedTask.schedule_config.minute.toString() : "0"
                        inputMethodHints: Qt.ImhDigitsOnly
                        onTextChanged: {
                            if (selectedTask) selectedTask.schedule_config.minute = parseInt(text) || 0
                        }
                    }
                }
            }
        } else if (index === 3) {
            // 自定义Cron表达式
            Widgets.TextField_ {
                parent: scheduleConfigArea
                Layout.fillWidth: true
                label: qsTr("Cron表达式")
                text: selectedTask && selectedTask.schedule_config.cron_expr ? 
                    selectedTask.schedule_config.cron_expr : ""
                placeholderText: qsTr("例如：0 0 * * *")
                onTextChanged: {
                    if (selectedTask) selectedTask.schedule_config.cron_expr = text
                }
            }
        }
    }

    function saveTask() {
        const taskData = {
            name: createTaskDialog.findChild("TextField_", "任务名称").text,
            task_type: createTaskDialog.findChild("ComboBox_", "任务类型").currentIndex === 0 ? 'batch_ocr' : 'screenshot_ocr',
            schedule_type: getScheduleTypeFromIndex(scheduleTypeCombo.currentIndex),
            schedule_config: getScheduleConfig(),
            ocr_template: createTaskDialog.findChild("TextField_", "OCR模板").text,
            folders: createTaskDialog.findChild("TextField_", "处理文件夹").text.split(';').map(f => f.trim()).filter(f => f),
            retry_policy: {
                max_retries: parseInt(createTaskDialog.findChild("TextField_", "最大重试次数").text) || 0,
                retry_interval: parseInt(createTaskDialog.findChild("TextField_", "重试间隔(秒)").text) || 60
            },
            concurrency_limit: parseInt(createTaskDialog.findChild("TextField_", "并发限制").text) || 1,
            enabled: true
        }

        if (selectedTask) {
            taskData.id = selectedTask.id
            connector.updateTask(ctrlKey, taskData)
        } else {
            connector.addTask(ctrlKey, taskData)
        }

        createTaskDialog.close()
        refreshTasks()
    }

    function getScheduleTypeFromIndex(index) {
        switch (index) {
            case 0: return 'once'
            case 1: return 'daily'
            case 2: return 'weekly'
            case 3: return 'cron'
            default: return 'once'
        }
    }

    function getScheduleConfig() {
        const index = scheduleTypeCombo.currentIndex
        const config = {}

        if (index === 0) {
            config.execution_time = scheduleConfigArea.findChild("TextField_", "执行时间").text
        } else if (index === 1) {
            config.hour = parseInt(scheduleConfigArea.findChild("TextField_", "小时").text) || 0
            config.minute = parseInt(scheduleConfigArea.findChild("TextField_", "分钟").text) || 0
        } else if (index === 2) {
            config.day_of_week = scheduleConfigArea.findChild("ComboBox_", "星期几").currentIndex
            config.hour = parseInt(scheduleConfigArea.findChild("TextField_", "小时").text) || 0
            config.minute = parseInt(scheduleConfigArea.findChild("TextField_", "分钟").text) || 0
        } else if (index === 3) {
            config.cron_expr = scheduleConfigArea.findChild("TextField_", "Cron表达式").text
        }

        return config
    }

    function deleteSelectedTask() {
        if (selectedTask) {
            connector.deleteTask(ctrlKey, selectedTask.id)
            refreshTasks()
            selectedTask = null
        }
    }

    function executeTaskNow() {
        if (selectedTask) {
            connector.executeTaskNow(ctrlKey, selectedTask.id)
            refreshTasks()
        }
    }

    function refreshTasks() {
        tasksModel.clear()
        const tasks = connector.getTasks(ctrlKey)
        
        for (let i = 0; i < tasks.length; i++) {
            const task = tasks[i]
            tasksModel.append({
                id: task.id,
                name: task.name,
                task_type: task.task_type === 'batch_ocr' ? qsTr("批量OCR") : qsTr("截图OCR"),
                schedule_type: getScheduleTypeLabel(task.schedule_type),
                next_execution: task.next_execution ? new Date(task.next_execution).toLocaleString() : qsTr("无"),
                last_execution: task.last_execution ? new Date(task.last_execution).toLocaleString() : qsTr("从未执行"),
                status: task.enabled ? qsTr("启用") : qsTr("禁用")
            })
        }
    }

    function getScheduleTypeLabel(scheduleType) {
        switch (scheduleType) {
            case 'once': return qsTr("一次性")
            case 'daily': return qsTr("每天")
            case 'weekly': return qsTr("每周")
            case 'cron': return qsTr("自定义Cron")
            default: return qsTr("未知")
        }
    }

    // ========================= 【生命周期】 =========================

    Component.onCompleted: {
        refreshTasks()
    }

    function showPage() {
        refreshTasks()
    }

    function closePage() {
        // 页面关闭时的清理工作
    }
}