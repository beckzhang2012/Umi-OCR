// ===============================================
// =============== 性能监控页面 ===============
// ===============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCharts 2.15
import PubSubConnector 1.0
import UtilsConnector 1.0
import TagPageConnector 1.0

Item {
    id: root
    width: parent.width
    height: parent.height

    // 发布/订阅连接器
    PubSubConnector { id: pubSub }
    // 工具连接器
    UtilsConnector { id: utils }
    // 页面连接器
    TagPageConnector { id: connector }

    // 性能数据模型
    ListModel {
        id: performanceModel
        ListElement { timestamp: 0; cpu_usage: 0; gpu_usage: 0; memory_usage: 0; disk_usage: 0; task_throughput: 0; task_failure_rate: 0 }
    }

    // 告警历史模型
    ListModel {
        id: alertHistoryModel
    }

    // 告警配置
    property var alertConfigs: {
        'cpu_usage': { threshold: 80, enabled: true },
        'gpu_usage': { threshold: 85, enabled: true },
        'memory_usage': { threshold: 85, enabled: true },
        'disk_usage': { threshold: 90, enabled: true },
        'task_failure_rate': { threshold: 10, enabled: true }
    }

    // 时间范围选择
    property int selectedTimeRange: 3600 // 1小时

    // 控制器对象
    property var controller: null

    // 初始化
    Component.onCompleted: {
        // 获取控制器对象
        var ctrlKey = connector.addPage("PerformanceMonitor")
        if (ctrlKey) {
            controller = connector.pages[ctrlKey].pyObj
        }

        // 订阅性能数据更新事件
        pubSub.subscribeGroup("PerformanceMonitor", root, "onPerformanceDataUpdated", "PerformanceDataUpdated")
        // 订阅告警事件
        pubSub.subscribeGroup("PerformanceMonitor", root, "onPerformanceAlert", "PerformanceAlert")

        // 启动性能监控
        if (controller) {
            controller.start_monitoring()
            // 加载告警配置
            loadAlertConfigs()
        }
    }

    // 清理资源
    Component.onDestruction: {
        pubSub.unsubscribeGroup("PerformanceMonitor")
        if (controller) {
            controller.stop_monitoring()
        }
    }

    // 性能数据更新处理
    function onPerformanceDataUpdated(data) {
        // 添加新数据点
        performanceModel.append(data)

        // 限制数据点数量（根据时间范围）
        var maxPoints = selectedTimeRange / 1; // 每秒一个数据点
        if (performanceModel.count > maxPoints) {
            performanceModel.remove(0, performanceModel.count - maxPoints)
        }
    }

    // 告警处理
    function onPerformanceAlert(alert) {
        alertHistoryModel.append({
            metric: alert.metric,
            value: alert.value.toFixed(2),
            threshold: alert.threshold,
            timestamp: new Date(alert.timestamp * 1000).toLocaleString()
        })

        // 显示告警弹窗
        showAlertPopup(alert)
    }

    // 显示告警弹窗
    function showAlertPopup(alert) {
        var metricNames = {
            'cpu_usage': qsTr("CPU使用率"),
            'gpu_usage': qsTr("GPU使用率"),
            'memory_usage': qsTr("内存使用率"),
            'disk_usage': qsTr("磁盘使用率"),
            'task_failure_rate': qsTr("任务失败率")
        }

        var message = qsTr("%1 超过阈值！当前值: %2%, 阈值: %3%").arg(metricNames[alert.metric] || alert.metric).arg(alert.value.toFixed(2)).arg(alert.threshold)

        // 调用全局弹窗管理器显示告警
        if (popupManager) {
            popupManager.showMessage(message, "warning")
        }
    }

    // 加载告警配置
    function loadAlertConfigs() {
        if (controller) {
            alertConfigs = controller.get_alert_configs()
        }
    }

    // 保存告警配置
    function saveAlertConfigs() {
        if (controller) {
            controller.update_alert_configs(alertConfigs)
        }
    }

    // 导出数据
    function exportData(format) {
        if (!controller) return

        var timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
        var fileName = `performance_data_${timestamp}.${format}`
        var filePath = Qt.platform.os === "windows" ? `C:/Users/${Qt.application.userName}/Downloads/${fileName}` : `~/Downloads/${fileName}`

        var success = controller.export_data(filePath, selectedTimeRange, format)
        if (success) {
            if (popupManager) {
                popupManager.showMessage(qsTr("数据导出成功！"), "info")
            }
        } else {
            if (popupManager) {
                popupManager.showMessage(qsTr("数据导出失败！"), "error")
            }
        }
    }

    // 复制诊断包
    function copyDiagnosticPackage() {
        if (!controller) return

        var packageData = controller.get_diagnostic_package()
        utils.copyText(packageData)
        if (popupManager) {
            popupManager.showMessage(qsTr("诊断包已复制到剪贴板！"), "info")
        }
    }

    // 重新加载性能数据
    function reloadPerformanceData() {
        if (!controller) return

        var data = controller.get_performance_data(selectedTimeRange)
        performanceModel.clear()
        for (var i = 0; i < data.length; i++) {
            performanceModel.append(data[i])
        }
    }

    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // 页面标题
        Text {
            text: qsTr("性能监控")
            font.pixelSize: 24
            font.bold: true
            Layout.leftMargin: 10
            Layout.topMargin: 10
        }

        // 控制面板
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Layout.leftMargin: 10
            Layout.rightMargin: 10

            // 时间范围选择
            ComboBox {
                id: timeRangeCombo
                model: [
                    { text: qsTr("15分钟"), value: 900 },
                    { text: qsTr("30分钟"), value: 1800 },
                    { text: qsTr("1小时"), value: 3600 },
                    { text: qsTr("3小时"), value: 10800 },
                    { text: qsTr("6小时"), value: 21600 },
                    { text: qsTr("12小时"), value: 43200 },
                    { text: qsTr("24小时"), value: 86400 }
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: 2 // 默认1小时
                onCurrentIndexChanged: {
                    selectedTimeRange = currentIndex >= 0 ? model[currentIndex].value : 3600
                    // 重新加载数据
                    reloadPerformanceData()
                }
            }

            // 导出按钮
            Button {
                text: qsTr("导出JSON")
                onClicked: exportData('json')
            }

            Button {
                text: qsTr("导出CSV")
                onClicked: exportData('csv')
            }

            // 复制诊断包按钮
            Button {
                text: qsTr("复制诊断包")
                onClicked: copyDiagnosticPackage()
            }
        }

        // 实时指标卡片
        GridLayout {
            Layout.fillWidth: true
            columns: 4
            spacing: 10
            Layout.leftMargin: 10
            Layout.rightMargin: 10

            // CPU使用率卡片
            MetricCard {
                title: qsTr("CPU使用率")
                value: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).cpu_usage.toFixed(1) + "%" : "0%"
                color: "#3498db"
                alertThreshold: alertConfigs.cpu_usage.threshold
                alertEnabled: alertConfigs.cpu_usage.enabled
                currentValue: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).cpu_usage : 0
            }

            // GPU使用率卡片
            MetricCard {
                title: qsTr("GPU使用率")
                value: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).gpu_usage.toFixed(1) + "%" : "0%"
                color: "#e74c3c"
                alertThreshold: alertConfigs.gpu_usage.threshold
                alertEnabled: alertConfigs.gpu_usage.enabled
                currentValue: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).gpu_usage : 0
            }

            // 内存使用率卡片
            MetricCard {
                title: qsTr("内存使用率")
                value: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).memory_usage.toFixed(1) + "%" : "0%"
                color: "#2ecc71"
                alertThreshold: alertConfigs.memory_usage.threshold
                alertEnabled: alertConfigs.memory_usage.enabled
                currentValue: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).memory_usage : 0
            }

            // 磁盘使用率卡片
            MetricCard {
                title: qsTr("磁盘使用率")
                value: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).disk_usage.toFixed(1) + "%" : "0%"
                color: "#f39c12"
                alertThreshold: alertConfigs.disk_usage.threshold
                alertEnabled: alertConfigs.disk_usage.enabled
                currentValue: performanceModel.count > 0 ? performanceModel.get(performanceModel.count - 1).disk_usage : 0
            }
        }

        // 图表区域
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rows: 2
            spacing: 10
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 10

            // CPU/GPU使用率图表
            PerformanceChart {
                id: cpuGpuChart
                title: qsTr("CPU/GPU使用率")
                xAxisLabel: qsTr("时间")
                yAxisLabel: qsTr("使用率 (%)")
                series: [
                    { name: qsTr("CPU"), color: "#3498db", dataRole: "cpu_usage" },
                    { name: qsTr("GPU"), color: "#e74c3c", dataRole: "gpu_usage" }
                ]
                model: performanceModel
            }

            // 内存/磁盘使用率图表
            PerformanceChart {
                id: memoryDiskChart
                title: qsTr("内存/磁盘使用率")
                xAxisLabel: qsTr("时间")
                yAxisLabel: qsTr("使用率 (%)")
                series: [
                    { name: qsTr("内存"), color: "#2ecc71", dataRole: "memory_usage" },
                    { name: qsTr("磁盘"), color: "#f39c12", dataRole: "disk_usage" }
                ]
                model: performanceModel
            }

            // 任务吞吐量图表
            PerformanceChart {
                id: throughputChart
                title: qsTr("任务吞吐量")
                xAxisLabel: qsTr("时间")
                yAxisLabel: qsTr("任务/秒")
                series: [
                    { name: qsTr("吞吐量"), color: "#9b59b6", dataRole: "task_throughput" }
                ]
                model: performanceModel
            }

            // 任务失败率图表
            PerformanceChart {
                id: failureRateChart
                title: qsTr("任务失败率")
                xAxisLabel: qsTr("时间")
                yAxisLabel: qsTr("失败率 (%)")
                series: [
                    { name: qsTr("失败率"), color: "#e74c3c", dataRole: "task_failure_rate" }
                ]
                model: performanceModel
            }
        }

        // 告警配置区域
        GroupBox {
            title: qsTr("告警配置")
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 10

            GridLayout {
                columns: 3
                spacing: 10
                Layout.fillWidth: true
                Layout.margins: 10

                // CPU告警配置
                AlertConfigRow {
                    metricName: qsTr("CPU使用率")
                    threshold: alertConfigs.cpu_usage.threshold
                    enabled: alertConfigs.cpu_usage.enabled
                    onThresholdChanged: alertConfigs.cpu_usage.threshold = threshold
                    onEnabledChanged: alertConfigs.cpu_usage.enabled = enabled
                }

                // GPU告警配置
                AlertConfigRow {
                    metricName: qsTr("GPU使用率")
                    threshold: alertConfigs.gpu_usage.threshold
                    enabled: alertConfigs.gpu_usage.enabled
                    onThresholdChanged: alertConfigs.gpu_usage.threshold = threshold
                    onEnabledChanged: alertConfigs.gpu_usage.enabled = enabled
                }

                // 内存告警配置
                AlertConfigRow {
                    metricName: qsTr("内存使用率")
                    threshold: alertConfigs.memory_usage.threshold
                    enabled: alertConfigs.memory_usage.enabled
                    onThresholdChanged: alertConfigs.memory_usage.threshold = threshold
                    onEnabledChanged: alertConfigs.memory_usage.enabled = enabled
                }

                // 磁盘告警配置
                AlertConfigRow {
                    metricName: qsTr("磁盘使用率")
                    threshold: alertConfigs.disk_usage.threshold
                    enabled: alertConfigs.disk_usage.enabled
                    onThresholdChanged: alertConfigs.disk_usage.threshold = threshold
                    onEnabledChanged: alertConfigs.disk_usage.enabled = enabled
                }

                // 任务失败率告警配置
                AlertConfigRow {
                    metricName: qsTr("任务失败率")
                    threshold: alertConfigs.task_failure_rate.threshold
                    enabled: alertConfigs.task_failure_rate.enabled
                    onThresholdChanged: alertConfigs.task_failure_rate.threshold = threshold
                    onEnabledChanged: alertConfigs.task_failure_rate.enabled = enabled
                }

                // 保存按钮
                Button {
                    text: qsTr("保存配置")
                    Layout.columnSpan: 3
                    Layout.alignment: Qt.AlignRight
                    onClicked: saveAlertConfigs()
                }
            }
        }

        // 告警历史
        GroupBox {
            title: qsTr("告警历史")
            Layout.fillWidth: true
            Layout.maximumHeight: 200
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 10

            TableView {
                id: alertHistoryTable
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: alertHistoryModel

                TableViewColumn {
                    role: "timestamp"
                    title: qsTr("时间")
                    width: 150
                }

                TableViewColumn {
                    role: "metric"
                    title: qsTr("指标")
                    width: 100
                }

                TableViewColumn {
                    role: "value"
                    title: qsTr("当前值")
                    width: 80
                }

                TableViewColumn {
                    role: "threshold"
                    title: qsTr("阈值")
                    width: 80
                }
            }
        }
    }
}

// 指标卡片组件
Component {
    id: metricCardComponent
    MetricCard {}
}

// 性能图表组件
Component {
    id: performanceChartComponent
    PerformanceChart {}
}

// 告警配置行组件
Component {
    id: alertConfigRowComponent
    AlertConfigRow {}
}

// 指标卡片
Item {
    id: metricCard
    property string title: "指标"
    property string value: "0%"
    property color color: "#3498db"
    property real alertThreshold: 80
    property bool alertEnabled: true
    property real currentValue: 0

    width: 200
    height: 100

    Rectangle {
        anchors.fill: parent
        color: currentValue > alertThreshold && alertEnabled ? "#ffe6e6" : "#ffffff"
        border.color: color
        border.width: 2
        radius: 5

        ColumnLayout {
            anchors.fill: parent
            spacing: 5
            Layout.margins: 10

            Text {
                text: title
                font.pixelSize: 14
                color: "#666666"
            }

            Text {
                text: value
                font.pixelSize: 24
                font.bold: true
                color: currentValue > alertThreshold && alertEnabled ? "#e74c3c" : color
            }

            ProgressBar {
                Layout.fillWidth: true
                value: currentValue / 100
                from: 0
                to: 1
                color: currentValue > alertThreshold && alertEnabled ? "#e74c3c" : color
            }
        }
    }
}

// 性能图表
Item {
    id: performanceChart
    property string title: "图表"
    property string xAxisLabel: "时间"
    property string yAxisLabel: "值"
    property var series: []
    property var model: null

    width: 400
    height: 300

    ChartView {
        anchors.fill: parent
        title: title
        antialiasing: true
        theme: ChartView.ChartThemeLight

        ValueAxis {
            id: xAxis
            min: 0
            max: 100
            visible: false
        }

        ValueAxis {
            id: yAxis
            min: 0
            max: 100
            titleText: yAxisLabel
        }

        // 动态创建系列
            Component.onCompleted: {
                if (!model) return

                for (var i = 0; i < series.length; i++) {
                    (function(index) {
                        var lineSeries = new LineSeries()
                        lineSeries.name = series[index].name
                        lineSeries.color = series[index].color
                        lineSeries.axisX = xAxis
                        lineSeries.axisY = yAxis

                        // 连接模型数据
                        model.onDataChanged.connect(function() {
                            updateSeries(lineSeries, series[index].dataRole)
                        })

                        // 初始加载数据
                        updateSeries(lineSeries, series[index].dataRole)
                        chart.addSeries(lineSeries)
                    })(i)
                }

                // 更新X轴范围
                if (model.count > 0) {
                    xAxis.max = model.count
                }
            }

        function updateSeries(series, dataRole) {
            series.clear()
            if (!model || model.count === 0) return

            for (var i = 0; i < model.count; i++) {
                var value = model.get(i)[dataRole] || 0
                series.append(i, value)
            }

            // 更新X轴范围
            xAxis.max = model.count
        }
    }
}

// 告警配置行
Item {
    id: alertConfigRow
    property string metricName: "指标"
    property int threshold: 80
    property bool enabled: true
    signal thresholdChanged(int threshold)
    signal enabledChanged(bool enabled)

    width: parent.width
    height: 40

    RowLayout {
        anchors.fill: parent
        spacing: 10

        Text {
            text: metricName
            Layout.preferredWidth: 120
            verticalAlignment: Text.AlignVCenter
        }

        TextField {
            id: thresholdField
            text: threshold
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            Layout.preferredWidth: 80
            onEditingFinished: {
                var newValue = parseInt(text)
                if (!isNaN(newValue) && newValue >= 0 && newValue <= 100) {
                    thresholdChanged(newValue)
                } else {
                    text = threshold
                }
            }
        }

        Text {
            text: "%"
            verticalAlignment: Text.AlignVCenter
        }

        CheckBox {
            checked: enabled
            onCheckedChanged: enabledChanged(checked)
        }
    }
}