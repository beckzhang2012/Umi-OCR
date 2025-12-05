// ===============================================
// =============== 性能监控页面 ===============
// ===============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCharts 2.15
import PubSubConnector 1.0 // 发布/订阅连接器

TabPage {
    id: performanceMonitorPage

    // ========================= 【属性】 =========================

    // 性能数据
    property var performanceData: {
        cpu: 0,
        gpu: 0,
        memory: 0,
        throughput: 0,
        failureRate: 0
    }

    // 告警阈值
    property var alertThresholds: {
        cpu: 80,
        gpu: 90,
        memory: 85,
        throughput: 1,
        failureRate: 10
    }

    // 历史数据
    property var historyData: []

    // ========================= 【组件】 =========================

    // 发布/订阅连接器
    PubSubConnector {
        id: pubSubConnector
    }

    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // 标题栏
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 40

            Text {
                text: qsTr("性能监控")
                font.pixelSize: 24
                font.bold: true
            }

            Spacer {
                Layout.fillWidth: true
            }

            // 一键复制诊断包按钮
            Button {
                text: qsTr("复制诊断包")
                onClicked: {
                    callPy("copy_diagnostic_package")
                }
            }
        }

        // 实时数据面板
        GridLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            columns: 5
            spacing: 10

            // CPU 占用率
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent

                    Text {
                        text: qsTr("CPU 占用率")
                        font.pixelSize: 14
                    }

                    Text {
                        text: performanceData.cpu + "%"
                        font.pixelSize: 24
                        font.bold: true
                        color: performanceData.cpu > alertThresholds.cpu ? "#FF5722" : "#2196F3"
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: performanceData.cpu / 100
                        color: performanceData.cpu > alertThresholds.cpu ? "#FF5722" : "#2196F3"
                    }
                }
            }

            // GPU 占用率
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent

                    Text {
                        text: qsTr("GPU 占用率")
                        font.pixelSize: 14
                    }

                    Text {
                        text: performanceData.gpu + "%"
                        font.pixelSize: 24
                        font.bold: true
                        color: performanceData.gpu > alertThresholds.gpu ? "#FF5722" : "#2196F3"
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: performanceData.gpu / 100
                        color: performanceData.gpu > alertThresholds.gpu ? "#FF5722" : "#2196F3"
                    }
                }
            }

            // 内存占用率
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent

                    Text {
                        text: qsTr("内存占用率")
                        font.pixelSize: 14
                    }

                    Text {
                        text: performanceData.memory + "%"
                        font.pixelSize: 24
                        font.bold: true
                        color: performanceData.memory > alertThresholds.memory ? "#FF5722" : "#2196F3"
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: performanceData.memory / 100
                        color: performanceData.memory > alertThresholds.memory ? "#FF5722" : "#2196F3"
                    }
                }
            }

            // 任务吞吐率
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent

                    Text {
                        text: qsTr("任务吞吐率")
                        font.pixelSize: 14
                    }

                    Text {
                        text: performanceData.throughput + qsTr(" 个/秒")
                        font.pixelSize: 24
                        font.bold: true
                        color: performanceData.throughput < alertThresholds.throughput ? "#FF5722" : "#2196F3"
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: Math.min(performanceData.throughput / 10, 1) // 假设最大吞吐率为 10 个/秒
                        color: performanceData.throughput < alertThresholds.throughput ? "#FF5722" : "#2196F3"
                    }
                }
            }

            // 任务失败率
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent

                    Text {
                        text: qsTr("任务失败率")
                        font.pixelSize: 14
                    }

                    Text {
                        text: performanceData.failureRate + "%"
                        font.pixelSize: 24
                        font.bold: true
                        color: performanceData.failureRate > alertThresholds.failureRate ? "#FF5722" : "#2196F3"
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: performanceData.failureRate / 100
                        color: performanceData.failureRate > alertThresholds.failureRate ? "#FF5722" : "#2196F3"
                    }
                }
            }
        }

        // 图表区域
        TabView {
            id: chartTabView
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            // CPU/GPU 占用率图表
            Tab {
                title: qsTr("CPU/GPU 占用率")

                ChartView {
                    id: cpuGpuChart
                    anchors.fill: parent
                    antialiasing: true
                    theme: ChartView.ChartThemeQt

                    LineSeries {
                        id: cpuSeries
                        name: qsTr("CPU 占用率")
                        color: "#2196F3"
                    }

                    LineSeries {
                        id: gpuSeries
                        name: qsTr("GPU 占用率")
                        color: "#4CAF50"
                    }

                    ValueAxis {
                        id: cpuGpuXAxis
                        min: 0
                        max: 60 // 显示最近 60 秒的数据
                        labelFormat: "%.0f"
                    }

                    ValueAxis {
                        id: cpuGpuYAxis
                        min: 0
                        max: 100
                        labelFormat: "%.0f%%"
                    }

                    Component.onCompleted: {
                        cpuGpuChart.createDefaultAxes()
                        cpuGpuChart.axisX(cpuSeries, 0).setRange(0, 60)
                        cpuGpuChart.axisY(cpuSeries, 0).setRange(0, 100)
                        cpuGpuChart.axisX(gpuSeries, 0).setRange(0, 60)
                        cpuGpuChart.axisY(gpuSeries, 0).setRange(0, 100)
                    }
                }
            }

            // 内存占用率图表
            Tab {
                title: qsTr("内存占用率")

                ChartView {
                    id: memoryChart
                    anchors.fill: parent
                    antialiasing: true
                    theme: ChartView.ChartThemeQt

                    LineSeries {
                        id: memorySeries
                        name: qsTr("内存占用率")
                        color: "#FF9800"
                    }

                    ValueAxis {
                        id: memoryXAxis
                        min: 0
                        max: 60 // 显示最近 60 秒的数据
                        labelFormat: "%.0f"
                    }

                    ValueAxis {
                        id: memoryYAxis
                        min: 0
                        max: 100
                        labelFormat: "%.0f%%"
                    }

                    Component.onCompleted: {
                        memoryChart.createDefaultAxes()
                        memoryChart.axisX(memorySeries, 0).setRange(0, 60)
                        memoryChart.axisY(memorySeries, 0).setRange(0, 100)
                    }
                }
            }

            // 任务吞吐率图表
            Tab {
                title: qsTr("任务吞吐率")

                ChartView {
                    id: throughputChart
                    anchors.fill: parent
                    antialiasing: true
                    theme: ChartView.ChartThemeQt

                    LineSeries {
                        id: throughputSeries
                        name: qsTr("任务吞吐率")
                        color: "#9C27B0"
                    }

                    ValueAxis {
                        id: throughputXAxis
                        min: 0
                        max: 60 // 显示最近 60 秒的数据
                        labelFormat: "%.0f"
                    }

                    ValueAxis {
                        id: throughputYAxis
                        min: 0
                        max: 10 // 假设最大吞吐率为 10 个/秒
                        labelFormat: "%.1f"
                    }

                    Component.onCompleted: {
                        throughputChart.createDefaultAxes()
                        throughputChart.axisX(throughputSeries, 0).setRange(0, 60)
                        throughputChart.axisY(throughputSeries, 0).setRange(0, 10)
                    }
                }
            }

            // 任务失败率图表
            Tab {
                title: qsTr("任务失败率")

                ChartView {
                    id: failureRateChart
                    anchors.fill: parent
                    antialiasing: true
                    theme: ChartView.ChartThemeQt

                    LineSeries {
                        id: failureRateSeries
                        name: qsTr("任务失败率")
                        color: "#FF5722"
                    }

                    ValueAxis {
                        id: failureRateXAxis
                        min: 0
                        max: 60 // 显示最近 60 秒的数据
                        labelFormat: "%.0f"
                    }

                    ValueAxis {
                        id: failureRateYAxis
                        min: 0
                        max: 100
                        labelFormat: "%.0f%%"
                    }

                    Component.onCompleted: {
                        failureRateChart.createDefaultAxes()
                        failureRateChart.axisX(failureRateSeries, 0).setRange(0, 60)
                        failureRateChart.axisY(failureRateSeries, 0).setRange(0, 100)
                    }
                }
            }
        }

        // 告警设置和历史数据导出区域
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            spacing: 10

            // 告警设置按钮
            Button {
                text: qsTr("告警设置")
                onClicked: {
                    // 打开告警设置对话框
                    alertSettingsDialog.open()
                }
            }

            // 历史数据导出按钮
            Button {
                text: qsTr("导出历史数据")
                onClicked: {
                    // 打开导出历史数据对话框
                    exportHistoryDialog.open()
                }
            }

            Spacer {
                Layout.fillWidth: true
            }

            // 刷新按钮
            Button {
                text: qsTr("刷新")
                onClicked: {
                    // 刷新数据
                    callPy("refresh_data")
                }
            }
        }
    }

    // ========================= 【告警设置对话框】 =========================

    Dialog {
        id: alertSettingsDialog
        title: qsTr("告警设置")
        width: 400
        height: 300

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            // CPU 阈值
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("CPU 阈值 (%)")
                    Layout.preferredWidth: 120
                }

                SpinBox {
                    id: cpuThresholdSpinBox
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: alertThresholds.cpu
                    onValueChanged: {
                        alertThresholds.cpu = value
                        callPy("set_alert_threshold", "cpu", value)
                    }
                }
            }

            // GPU 阈值
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("GPU 阈值 (%)")
                    Layout.preferredWidth: 120
                }

                SpinBox {
                    id: gpuThresholdSpinBox
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: alertThresholds.gpu
                    onValueChanged: {
                        alertThresholds.gpu = value
                        callPy("set_alert_threshold", "gpu", value)
                    }
                }
            }

            // 内存阈值
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("内存阈值 (%)")
                    Layout.preferredWidth: 120
                }

                SpinBox {
                    id: memoryThresholdSpinBox
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: alertThresholds.memory
                    onValueChanged: {
                        alertThresholds.memory = value
                        callPy("set_alert_threshold", "memory", value)
                    }
                }
            }

            // 吞吐率阈值
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("吞吐率阈值 (个/秒)")
                    Layout.preferredWidth: 150
                }

                SpinBox {
                    id: throughputThresholdSpinBox
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: alertThresholds.throughput
                    onValueChanged: {
                        alertThresholds.throughput = value
                        callPy("set_alert_threshold", "throughput", value)
                    }
                }
            }

            // 失败率阈值
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("失败率阈值 (%)")
                    Layout.preferredWidth: 120
                }

                SpinBox {
                    id: failureRateThresholdSpinBox
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: alertThresholds.failureRate
                    onValueChanged: {
                        alertThresholds.failureRate = value
                        callPy("set_alert_threshold", "failureRate", value)
                    }
                }
            }
        }
    }

    // ========================= 【导出历史数据对话框】 =========================

    Dialog {
        id: exportHistoryDialog
        title: qsTr("导出历史数据")
        width: 400
        height: 200

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            // 导出格式选择
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("导出格式")
                    Layout.preferredWidth: 100
                }

                ComboBox {
                    id: exportFormatComboBox
                    Layout.fillWidth: true
                    model: ["JSON", "CSV"]
                    currentIndex: 0
                }
            }

            // 导出按钮
            Button {
                text: qsTr("导出")
                Layout.alignment: Qt.AlignRight
                onClicked: {
                    callPy("export_history_data", exportFormatComboBox.currentText)
                    exportHistoryDialog.close()
                }
            }
        }
    }

    // ========================= 【方法】 =========================

    // 更新性能数据
    function updatePerformanceData(data) {
        performanceData = data

        // 更新 CPU 系列数据
        if (cpuSeries.count > 60) {
            cpuSeries.remove(0)
        }
        cpuSeries.append(cpuSeries.count, data.cpu)

        // 更新 GPU 系列数据
        if (gpuSeries.count > 60) {
            gpuSeries.remove(0)
        }
        gpuSeries.append(gpuSeries.count, data.gpu)

        // 更新内存系列数据
        if (memorySeries.count > 60) {
            memorySeries.remove(0)
        }
        memorySeries.append(memorySeries.count, data.memory)

        // 更新吞吐率系列数据
        if (throughputSeries.count > 60) {
            throughputSeries.remove(0)
        }
        throughputSeries.append(throughputSeries.count, data.throughput)

        // 更新失败率系列数据
        if (failureRateSeries.count > 60) {
            failureRateSeries.remove(0)
        }
        failureRateSeries.append(failureRateSeries.count, data.failureRate)
    }

    // ========================= 【信号和槽】 =========================

    // 页面展示时的信号处理
    onShowPage: {
        // 订阅性能数据
        pubSubConnector.subscribe("performance_data", updatePerformanceData)

        // 初始化告警阈值
        callPy("get_alert_threshold", "cpu").then(function(value) {
            alertThresholds.cpu = value
            cpuThresholdSpinBox.value = value
        })

        callPy("get_alert_threshold", "gpu").then(function(value) {
            alertThresholds.gpu = value
            gpuThresholdSpinBox.value = value
        })

        callPy("get_alert_threshold", "memory").then(function(value) {
            alertThresholds.memory = value
            memoryThresholdSpinBox.value = value
        })

        callPy("get_alert_threshold", "throughput").then(function(value) {
            alertThresholds.throughput = value
            throughputThresholdSpinBox.value = value
        })

        callPy("get_alert_threshold", "failureRate").then(function(value) {
            alertThresholds.failureRate = value
            failureRateThresholdSpinBox.value = value
        })
    }

    // 页面销毁时的信号处理
    Component.onDestruction: {
        // 取消订阅性能数据
        pubSubConnector.unsubscribe("performance_data", updatePerformanceData)
    }
}
