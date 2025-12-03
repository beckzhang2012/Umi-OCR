// ==============================================
// =============== 功能页：统计分析 ===============
// ==============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCharts 2.15
import ".."
import "../../Widgets"

TabPage {
    id: tabPage
    
    // 配置
    configsComp: Column {
        spacing: 10
        
        RowLayout {
            Layout.fillWidth: true
            
            Label {
                text: qsTr("词汇最小长度:")
                Layout.alignment: Qt.AlignVCenter
            }
            
            SpinBox {
                id: minWordLength
                value: 2
                from: 1
                to: 10
                Layout.preferredWidth: 80
            }
            
            Label {
                text: qsTr("显示前N名:")
                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: 20
            }
            
            SpinBox {
                id: topWordsCount
                value: 20
                from: 5
                to: 50
                Layout.preferredWidth: 80
            }
            
            Button {
                text: qsTr("刷新")
                Layout.leftMargin: 20
                onClicked: refreshStats()
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            
            Label {
                text: qsTr("趋势图天数:")
                Layout.alignment: Qt.AlignVCenter
            }
            
            SpinBox {
                id: trendDays
                value: 30
                from: 7
                to: 90
                Layout.preferredWidth: 80
            }
        }
    }
    
    // 统计数据模型
    property var overallStats: {}
    property var wordFrequency: []
    property var trendData: []
    
    // ========================= 【逻辑】 =========================
    
    // 刷新统计数据
    function refreshStats() {
        // 获取总体统计
        overallStats = tabPage.callPy("get_overall_stats")
        
        // 获取词汇频率
        wordFrequency = tabPage.callPy("get_word_frequency", [minWordLength.value, topWordsCount.value])
        
        // 获取趋势数据
        trendData = tabPage.callPy("get_trend_data", [trendDays.value])
        
        // 更新图表
        updateTrendChart()
    }
    
    // 更新趋势图
    function updateTrendChart() {
        trendChartView.series.clear()
        
        if (!trendData || trendData.length === 0) return
        
        var series = new LineSeries()
        series.name = qsTr("识别次数")
        
        for (var i = 0; i < trendData.length; i++) {
            var day = trendData[i]
            series.append(i, day.count)
        }
        
        trendChartView.series.append(series)
        
        // 更新X轴标签
        var axisX = trendChartView.axisX
        axisX.clear()
        for (var j = 0; j < trendData.length; j += Math.ceil(trendData.length / 10)) {
            axisX.append(j, trendData[j].date.substring(5))
        }
    }
    
    // 导出统计数据
    function exportStats() {
        var dialog = new FileDialog()
        dialog.title = qsTr("导出统计数据")
        dialog.selectExisting = false
        dialog.nameFilters = [
            qsTr("JSON文件 (*.json)"),
            qsTr("CSV文件 (*.csv)")
        ]
        
        dialog.accepted.connect(function() {
            var filePath = dialog.fileUrl.toString().replace("file:///", "")
            var format = dialog.nameFilter.indexOf("JSON") !== -1 ? "json" : "csv"
            
            var success = tabPage.callPy("export_data", [filePath, format])
            if (success) {
                qmlapp.popup.simple(qsTr("导出成功"), qsTr("统计数据已导出到:") + "\n" + filePath)
            } else {
                qmlapp.popup.simple(qsTr("导出失败"), qsTr("无法导出统计数据"), "error")
            }
        })
        
        dialog.open()
    }
    
    // 关闭页面
    function closePage() {
        delPage()
    }
    
    // ========================= 【事件管理】 =========================
    
    Component.onCompleted: {
        refreshStats()
    }
    
    // ========================= 【UI布局】 =========================
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 15
        
        // 总体统计卡片
        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            
            ColumnLayout {
                anchors.fill: parent
                spacing: 10
                
                Label {
                    text: qsTr("总体统计")
                    font.bold: true
                    font.pointSize: 14
                    Layout.alignment: Qt.AlignHCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    
                    StatItem {
                        title: qsTr("总识别次数")
                        value: overallStats.total_count || 0
                        color: "#4CAF50"
                    }
                    
                    StatItem {
                        title: qsTr("成功率")
                        value: (overallStats.success_rate || 0).toFixed(1) + "%"
                        color: "#2196F3"
                    }
                    
                    StatItem {
                        title: qsTr("平均置信度")
                        value: (overallStats.avg_confidence || 0).toFixed(2)
                        color: "#FF9800"
                    }
                    
                    StatItem {
                        title: qsTr("今日识别")
                        value: overallStats.today_count || 0
                        color: "#9C27B0"
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    
                    StatItem {
                        title: qsTr("本周识别")
                        value: overallStats.week_count || 0
                        color: "#00BCD4"
                    }
                    
                    StatItem {
                        title: qsTr("本月识别")
                        value: overallStats.month_count || 0
                        color: "#FF5722"
                    }
                    
                    StatItem {
                        title: qsTr("平均速度")
                        value: (overallStats.avg_speed || 0).toFixed(2) + "s"
                        color: "#607D8B"
                    }
                    
                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }
        
        // 趋势图和词汇统计
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 15
            
            // 趋势图
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 400
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: qsTr("识别趋势图")
                        font.bold: true
                        font.pointSize: 14
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    ChartView {
                        id: trendChartView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        antialiasing: true
                        
                        ValueAxis {
                            id: axisY
                            min: 0
                            titleText: qsTr("识别次数")
                        }
                        
                        CategoryAxis {
                            id: axisX
                            labelsAngle: -45
                            titleText: qsTr("日期")
                        }
                    }
                }
            }
            
            // 词汇统计
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 300
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: qsTr("常用词汇")
                        font.bold: true
                        font.pointSize: 14
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: wordFrequency
                        delegate: wordFrequencyDelegate
                        clip: true
                    }
                }
            }
        }
        
        // 导出按钮
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            
            Button {
                text: qsTr("导出统计数据")
                onClicked: exportStats()
            }
        }
    }




// 词汇频率委托组件
Component {
    id: wordFrequencyDelegate
    
    RowLayout {
        width: parent.width
        padding: 10
        
        Label {
            text: modelData[0]
            font.pointSize: 13
            Layout.fillWidth: true
        }
        
        Label {
            text: modelData[1]
            font.bold: true
            color: "#4CAF50"
        }
    }
}