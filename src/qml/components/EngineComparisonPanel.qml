import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import QtQuick.Window 2.15
import "../utils" as Utils

// 引擎对比面板组件
// 支持逐条查看差异、导出对比报告
Item {
    id: root
    width: parent.width
    height: parent.height

    // 输入属性
    property var engineResults: []  // 多引擎识别结果
    property var engineNames: []   // 引擎名称列表

    // 内部状态
    property var currentItemIndex: -1
    property var diffItems: []     // 差异项列表

    // 初始化差异检测
    onEngineResultsChanged: {
        detectDifferences()
    }

    // 检测差异
    function detectDifferences() {
        diffItems = []
        if (engineResults.length < 2) {
            return
        }

        // 获取所有结果的文本行
        var allLines = []
        for (var i = 0; i < engineResults.length; i++) {
            var result = engineResults[i]
            if (result && result.text) {
                allLines.push(result.text.split('\n'))
            } else {
                allLines.push([])
            }
        }

        // 找出最大行数
        var maxLines = 0
        for (var j = 0; j < allLines.length; j++) {
            if (allLines[j].length > maxLines) {
                maxLines = allLines[j].length
            }
        }

        // 逐行比较
        for (var line = 0; line < maxLines; line++) {
            var lineTexts = []
            var hasDiff = false

            for (var e = 0; e < allLines.length; e++) {
                var text = allLines[e][line] || ''
                lineTexts.push(text)
            }

            // 检查是否有差异
            for (var k = 1; k < lineTexts.length; k++) {
                if (lineTexts[k] !== lineTexts[0]) {
                    hasDiff = true
                    break
                }
            }

            if (hasDiff) {
                diffItems.push({
                    line: line + 1,
                    texts: lineTexts,
                    hasDiff: true
                })
            }
        }

        // 更新列表
        diffList.model = diffItems
    }

    // 导出对比报告
    function exportReport() {
        if (engineResults.length === 0) {
            Utils.MessageBox.show("错误", "没有可导出的结果！")
            return
        }

        // 创建保存对话框
        var dialog = Utils.FileDialog.create({
            title: "保存对比报告",
            selectExisting: false,
            selectFolder: false,
            nameFilters: ["文本文件 (*.txt)", "所有文件 (*)"]
        })

        dialog.accepted.connect(function() {
            var filePath = dialog.fileUrl.replace('file:///', '')
            generateReport(filePath)
        })

        dialog.open()
    }

    // 生成报告
    function generateReport(filePath) {
        try {
            var report = "OCR引擎对比报告\n"
            report += "生成时间: " + new Date().toLocaleString() + "\n"
            report += "参与引擎: " + engineNames.join(", ") + "\n"
            report += "========================================\n\n"

            // 添加完整结果对比
            for (var i = 0; i < engineResults.length; i++) {
                report += "【" + engineNames[i] + "】\n"
                report += engineResults[i].text + "\n\n"
            }

            // 添加差异分析
            if (diffItems.length > 0) {
                report += "========================================\n"
                report += "差异分析\n"
                report += "========================================\n\n"

                for (var j = 0; j < diffItems.length; j++) {
                    var diff = diffItems[j]
                    report += "第 " + diff.line + " 行:\n"
                    for (var k = 0; k < diff.texts.length; k++) {
                        report += engineNames[k] + ": " + diff.texts[k] + "\n"
                    }
                    report += "\n"
                }
            } else {
                report += "========================================\n"
                report += "所有引擎识别结果一致\n"
            }

            // 写入文件
            var file = new Utils.File()
            file.open(filePath, Utils.File.WriteOnly)
            file.write(report)
            file.close()

            Utils.MessageBox.show("成功", "对比报告已保存到:\n" + filePath)
        } catch (e) {
            Utils.MessageBox.show("错误", "保存报告失败: " + e.message)
        }
    }

    // 复制差异项
    function copyDiffItem(index) {
        if (index < 0 || index >= diffItems.length) {
            return
        }

        var diff = diffItems[index]
        var text = "第 " + diff.line + " 行差异:\n"
        for (var i = 0; i < diff.texts.length; i++) {
            text += engineNames[i] + ": " + diff.texts[i] + "\n"
        }

        Utils.Clipboard.setText(text)
        Utils.MessageBox.show("成功", "差异信息已复制到剪贴板")
    }

    // 布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        // 头部信息
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16

            Text {
                text: "引擎对比分析"
                font.pixelSize: 20
                font.bold: true
                color: "#333"
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "导出报告"
                onClicked: exportReport()
                enabled: engineResults.length > 0
            }
        }

        // 统计信息
        Rectangle {
            Layout.fillWidth: true
            Layout.margins: 16
            height: 60
            color: "#f5f5f5"
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16

                ColumnLayout {
                    Text {
                        text: "参与引擎"
                        font.pixelSize: 12
                        color: "#666"
                    }
                    Text {
                        text: engineNames.length
                        font.pixelSize: 18
                        font.bold: true
                        color: "#333"
                    }
                }

                Item {
                    Layout.fillWidth: true
                }

                ColumnLayout {
                    Text {
                        text: "差异行数"
                        font.pixelSize: 12
                        color: "#666"
                    }
                    Text {
                        text: diffItems.length
                        font.pixelSize: 18
                        font.bold: true
                        color: diffItems.length > 0 ? "#e74c3c" : "#27ae60"
                    }
                }

                Item {
                    Layout.fillWidth: true
                }

                ColumnLayout {
                    Text {
                        text: "总行数"
                        font.pixelSize: 12
                        color: "#666"
                    }
                    Text {
                        text: engineResults.length > 0 ? engineResults[0].text.split('\n').length : 0
                        font.pixelSize: 18
                        font.bold: true
                        color: "#333"
                    }
                }
            }
        }

        // 差异列表
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 16
            color: "#ffffff"
            radius: 8
            border.color: "#e0e0e0"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12

                // 列表标题
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "行号"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#333"
                        Layout.preferredWidth: 60
                    }

                    Repeater {
                        model: engineNames

                        Text {
                            text: modelData
                            font.pixelSize: 14
                            font.bold: true
                            color: "#333"
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }

                    Item {
                        Layout.preferredWidth: 80
                    }
                }

                // 列表内容
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: 8

                    ListView {
                        id: diffList
                        width: parent.width
                        height: parent.height
                        model: diffItems
                        delegate: diffDelegate
                        spacing: 8
                    }
                }
            }
        }
    }

    // 差异项委托
    Component {
        id: diffDelegate

        Rectangle {
            width: parent.width
            height: implicitHeight
            color: "#fef5e7"
            radius: 6
            border.color: "#f39c12"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                // 行号
                Text {
                    text: "第 " + line + " 行"
                    font.pixelSize: 13
                    color: "#333"
                    Layout.preferredWidth: 60
                    verticalAlignment: Text.AlignVCenter
                }

                // 各引擎结果
                Repeater {
                    model: texts

                    Text {
                        text: modelData
                        font.pixelSize: 13
                        color: "#333"
                        Layout.fillWidth: true
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                }

                // 操作按钮
                Button {
                    text: "复制"
                    onClicked: copyDiffItem(index)
                    Layout.preferredWidth: 60
                }
            }
        }
    }
}