import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCharts 2.15
import "../"
import "../../Widgets"

TabPage {
    id: performanceMonitorPage
    
    // 页面标题
    pageTitle: qsTr("性能监控")
    
    // Python控制器
    pyCtrl: PyCtrl {
        ctrlKey: "PerformanceMonitor"
    }
    
    // 性能指标数据
    property var metrics: {
        cpu_usage: 0,
        gpu_usage: 0,
        memory_usage: 0,
        task_throughput: 0,
        failure_rate: 0,
        total_tasks: 0,
        success_tasks: 0,
        failed_tasks: 0
    }
    
    // 阈值配置
    property var thresholds: {
        cpu_usage: 80,
        gpu_usage: 90,
        memory_usage: 85,
        task_throughput: 0,
        failure_rate: 10
    }
    
    // 告警配置
    property var alertConfig: {
        enable_popup: true,
        enable_log: true,
        enable_notification: false
    }
    
    // 初始化
    Component.onCompleted: {
        // 加载阈值配置
        thresholds.cpu_usage = pyCtrl.getThreshold("cpu_usage")
        thresholds.gpu_usage = pyCtrl.getThreshold("gpu_usage")
        thresholds.memory_usage = pyCtrl.getThreshold("memory_usage")
        thresholds.task_throughput = pyCtrl.getThreshold("task_throughput")
        thresholds.failure_rate = pyCtrl.getThreshold("failure_rate")
        
        // 加载告警配置
        alertConfig.enable_popup = pyCtrl.getAlertConfig("enable_popup")
        alertConfig.enable_log = pyCtrl.getAlertConfig("enable_log")
        alertConfig.enable_notification = pyCtrl.getAlertConfig("enable_notification")
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10
        
        // 实时指标卡片
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            // CPU使用率卡片
            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                metricName: qsTr("CPU使用率")
                metricValue: metrics.cpu_usage
                unit: "%"
                threshold: thresholds.cpu_usage
                color: "#4CAF50"
            }
            
            // GPU使用率卡片
            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                metricName: qsTr("GPU使用率")
                metricValue: metrics.gpu_usage
                unit: "%"
                threshold: thresholds.gpu_usage
                color: "#2196F3"
            }
            
            // 内存使用率卡片
            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                metricName: qsTr("内存使用率")
                metricValue: metrics.memory_usage
                unit: "%"
                threshold: thresholds.memory_usage
                color: "#FF9800"
            }
        }
        
        // 图表区域
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            
            // CPU/GPU图表
            ChartPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                chartTitle: qsTr("CPU/GPU使用率")
                metrics: [
                    { name: qsTr("CPU"), value: metrics.cpu_usage, color: "#4CAF50" },
                    { name: qsTr("GPU"), value: metrics.gpu_usage, color: "#2196F3" }
                ]
                threshold: 100
            }
            
            // 内存图表
            ChartPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                chartTitle: qsTr("内存使用率")
                metrics: [
                    { name: qsTr("内存"), value: metrics.memory_usage, color: "#FF9800" }
                ]
                threshold: thresholds.memory_usage
            }
        }
        
        // 任务统计卡片
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            // 任务总数卡片
            StatCard {
                Layout.fillWidth: true
                statName: qsTr("任务总数")
                statValue: metrics.total_tasks
                color: "#9C27B0"
            }
            
            // 成功任务卡片
            StatCard {
                Layout.fillWidth: true
                statName: qsTr("成功任务")
                statValue: metrics.success_tasks
                color: "#4CAF50"
            }
            
            // 失败任务卡片
            StatCard {
                Layout.fillWidth: true
                statName: qsTr("失败任务")
                statValue: metrics.failed_tasks
                color: "#F44336"
            }
            
            // 失败率卡片
            StatCard {
                Layout.fillWidth: true
                statName: qsTr("失败率")
                statValue: metrics.failure_rate
                unit: "%"
                color: "#FF5722"
                threshold: thresholds.failure_rate
            }
        }
        
        // 配置和操作区域
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            // 阈值配置
            GroupBox {
                Layout.fillWidth: true
                title: qsTr("阈值配置")
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10
                    
                    ThresholdConfigItem {
                        metricName: qsTr("CPU使用率阈值")
                        currentValue: thresholds.cpu_usage
                        onValueChanged: {
                            thresholds.cpu_usage = value
                            pyCtrl.setThreshold("cpu_usage", value)
                        }
                    }
                    
                    ThresholdConfigItem {
                        metricName: qsTr("GPU使用率阈值")
                        currentValue: thresholds.gpu_usage
                        onValueChanged: {
                            thresholds.gpu_usage = value
                            pyCtrl.setThreshold("gpu_usage", value)
                        }
                    }
                    
                    ThresholdConfigItem {
                        metricName: qsTr("内存使用率阈值")
                        currentValue: thresholds.memory_usage
                        onValueChanged: {
                            thresholds.memory_usage = value
                            pyCtrl.setThreshold("memory_usage", value)
                        }
                    }
                    
                    ThresholdConfigItem {
                        metricName: qsTr("失败率阈值")
                        currentValue: thresholds.failure_rate
                        onValueChanged: {
                            thresholds.failure_rate = value
                            pyCtrl.setThreshold("failure_rate", value)
                        }
                    }
                }
            }
            
            // 告警配置
            GroupBox {
                Layout.fillWidth: true
                title: qsTr("告警配置")
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10
                    
                    CheckBox_ {
                        text: qsTr("弹出提醒")
                        checked: alertConfig.enable_popup
                        onCheckedChanged: {
                            alertConfig.enable_popup = checked
                            pyCtrl.setAlertConfig("enable_popup", checked)
                        }
                    }
                    
                    CheckBox_ {
                        text: qsTr("写入日志")
                        checked: alertConfig.enable_log
                        onCheckedChanged: {
                            alertConfig.enable_log = checked
                            pyCtrl.setAlertConfig("enable_log", checked)
                        }
                    }
                    
                    CheckBox_ {
                        text: qsTr("系统通知")
                        checked: alertConfig.enable_notification
                        onCheckedChanged: {
                            alertConfig.enable_notification = checked
                            pyCtrl.setAlertConfig("enable_notification", checked)
                        }
                    }
                }
            }
            
            // 操作按钮
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                Button_ {
                    Layout.fillWidth: true
                    text: qsTr("导出数据")
                    onClicked: exportDialog.open()
                }
                
                Button_ {
                    Layout.fillWidth: true
                    text: qsTr("查看历史")
                    onClicked: historyDialog.open()
                }
                
                Button_ {
                    Layout.fillWidth: true
                    text: qsTr("复制诊断包")
                    onClicked: {
                        var success = pyCtrl.copyDiagnosticPackage()
                        if (success) {
                            messageBox.show(qsTr("诊断包已复制到剪贴板"))
                        } else {
                            messageBox.show(qsTr("复制诊断包失败"), "error")
                        }
                    }
                }
            }
        }
    }
    
    // 导出对话框
    FileDialog_ {
        id: exportDialog
        title: qsTr("导出性能数据")
        selectFolder: false
        nameFilters: [
            qsTr("JSON文件 (*.json)"),
            qsTr("CSV文件 (*.csv)")
        ]
        onAccepted: {
            var result = pyCtrl.exportToFile("all", "24h", fileUrl)
            messageBox.show(result)
        }
    }
    
    // 历史数据对话框
    Dialog {
        id: historyDialog
        title: qsTr("历史数据")
        width: 800
        height: 600
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10
            
            // 时间范围选择
            ComboBox {
                id: timeRangeCombo
                Layout.fillWidth: true
                model: [qsTr("1小时"), qsTr("24小时"), qsTr("7天")]
                currentIndex: 1
            }
            
            // 历史图表
            ChartPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                chartTitle: qsTr("历史性能指标")
                metrics: [
                    { name: qsTr("CPU"), value: 0, color: "#4CAF50" },
                    { name: qsTr("GPU"), value: 0, color: "#2196F3" },
                    { name: qsTr("内存"), value: 0, color: "#FF9800" }
                ]
            }
            
            // 导出按钮
            Button_ {
                Layout.fillWidth: true
                text: qsTr("导出历史数据")
                onClicked: {
                    var timeRange = "24h"
                    if (timeRangeCombo.currentIndex === 0) timeRange = "1h"
                    else if (timeRangeCombo.currentIndex === 2) timeRange = "7d"
                    
                    exportDialog.title = qsTr("导出历史数据")
                    exportDialog.open()
                }
            }
        }
    }
    
    // 消息框
    MessageBox {
        id: messageBox
    }
    
    // Python回调方法
    function updateMetrics(newMetrics) {
        // 更新指标数据
        for (var key in newMetrics) {
            if (metrics.hasOwnProperty(key)) {
                metrics[key] = newMetrics[key]
            }
        }
    }
    
    function showAlert(message, timestamp) {
        messageBox.show(message, "warning")
    }
}

// 指标卡片组件
Component {
    id: metricCardComponent
    
    Rectangle {
        property string metricName
        property real metricValue
        property string unit: ""
        property real threshold: 100
        property color color: "#4CAF50"
        
        radius: 8
        color: metricValue > threshold ? "#FFEB3B" : "#FFFFFF"
        border.color: metricValue > threshold ? "#FF9800" : "#E0E0E0"
        border.width: 2
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 5
            
            Text_ {
                Layout.fillWidth: true
                text: metricName
                fontSize: 14
                color: "#666666"
                horizontalAlignment: Text.AlignHCenter
            }
            
            Text_ {
                Layout.fillWidth: true
                text: metricValue.toFixed(1) + unit
                fontSize: 24
                fontWeight: Font.Bold
                color: metricValue > threshold ? "#F44336" : color
                horizontalAlignment: Text.AlignHCenter
            }
            
            ProgressBar {
                Layout.fillWidth: true
                value: metricValue / 100
                from: 0
                to: 1
                
                background: Rectangle {
                    color: "#E0E0E0"
                    radius: 4
                }
                
                contentItem: Rectangle {
                    color: metricValue > threshold ? "#F44336" : color
                    radius: 4
                }
            }
        }
    }
}

// 统计卡片组件
Component {
    id: statCardComponent
    
    Rectangle {
        property string statName
        property int statValue
        property string unit: ""
        property real threshold: -1
        property color color: "#4CAF50"
        
        radius: 8
        color: "#FFFFFF"
        border.color: "#E0E0E0"
        border.width: 2
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 5
            
            Text_ {
                Layout.fillWidth: true
                text: statName
                fontSize: 14
                color: "#666666"
                horizontalAlignment: Text.AlignHCenter
            }
            
            Text_ {
                Layout.fillWidth: true
                text: statValue + unit
                fontSize: 24
                fontWeight: Font.Bold
                color: threshold > 0 && statValue > threshold ? "#F44336" : color
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}

// 图表面板组件
Component {
    id: chartPanelComponent
    
    Rectangle {
        property string chartTitle
        property var metrics
        property real threshold: 100
        
        radius: 8
        color: "#FFFFFF"
        border.color: "#E0E0E0"
        border.width: 2
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10
            
            Text_ {
                Layout.fillWidth: true
                text: chartTitle
                fontSize: 16
                fontWeight: Font.Bold
                color: "#333333"
                horizontalAlignment: Text.AlignHCenter
            }
            
            ChartView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                antialiasing: true
                
                BarChart {
                    id: barChart
                    barSetSpacing: 10
                    barWidth: 0.8
                    
                    // 创建柱状图系列
                    Component.onCompleted: {
                        for (var i = 0; i < metrics.length; i++) {
                            var barSet = BarSet {
                                label: metrics[i].name
                                values: [metrics[i].value]
                            }
                            barSet.color = metrics[i].color
                            barChart.append(barSet)
                        }
                    }
                }
                
                // 坐标轴
                ValueAxis {
                    id: valueAxisY
                    min: 0
                    max: 100
                    tickCount: 6
                    labelFormat: "%.0f%%"
                }
                
                categoryAxis {
                    id: categoryAxisX
                    categories: [""]
                }
                
                axes: [
                    Axis { orientation: Qt.AlignLeft; axis: valueAxisY },
                    Axis { orientation: Qt.AlignBottom; axis: categoryAxisX }
                ]
            }
        }
    }
}

// 阈值配置项组件
Component {
    id: thresholdConfigItemComponent
    
    RowLayout {
        property string metricName
        property real currentValue
        signal valueChanged(real value)
        
        Text_ {
            Layout.fillWidth: true
            Layout.preferredWidth: 200
            text: metricName
            fontSize: 14
            color: "#333333"
        }
        
        TextField_ {
            Layout.fillWidth: true
            Layout.preferredWidth: 100
            text: currentValue.toFixed(0)
            inputMethodHints: Qt.ImhDigitsOnly
            validator: IntValidator { bottom: 0; top: 100 }
            onEditingFinished: {
                var value = parseFloat(text)
                if (!isNaN(value) && value >= 0 && value <= 100) {
                    valueChanged(value)
                }
            }
        }
        
        Text_ {
            text: "%"
            fontSize: 14
            color: "#666666"
        }
    }
}