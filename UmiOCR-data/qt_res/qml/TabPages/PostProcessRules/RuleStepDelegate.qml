// =============================================
// =============== 规则步骤委托组件 ===============
// =============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: ruleStepDelegate
    
    // 规则步骤数据
    property var ruleStep: {
        id: "",
        type: "",
        enabled: true,
        name: ""
    }
    // 规则步骤在列表中的索引
    property int index: 0
    
    // 规则步骤变化信号
    signal ruleStepChanged
    // 删除按钮点击信号
    signal deleteClicked
    // 上移按钮点击信号
    signal moveUpClicked
    // 下移按钮点击信号
    signal moveDownClicked
    
    // 组件高度
    property int delegateHeight: 100
    
    width: parent.width
    height: delegateHeight
    
    // 背景
    Rectangle {
        anchors.fill: parent
        color: "#f0f0f0"
        radius: 5
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 5
        
        // 顶部栏：名称、启用状态、移动按钮、删除按钮
        RowLayout {
            Layout.fillWidth: true
            spacing: 5
            
            // 启用状态复选框
            CheckBox {
                checked: ruleStep.enabled
                onCheckedChanged: {
                    ruleStep.enabled = checked
                    ruleStepChanged()
                }
            }
            
            // 规则步骤名称输入框
            TextField {
                Layout.fillWidth: true
                text: ruleStep.name
                placeholderText: "规则步骤名称"
                onTextChanged: {
                    ruleStep.name = text
                    ruleStepChanged()
                }
            }
            
            // 移动按钮
            RowLayout {
                spacing: 2
                
                Button {
                    icon.source: "qrc:/images/arrow_up.png"
                    icon.width: 16
                    icon.height: 16
                    onClicked: {
                        moveUpClicked()
                    }
                }
                
                Button {
                    icon.source: "qrc:/images/arrow_down.png"
                    icon.width: 16
                    icon.height: 16
                    onClicked: {
                        moveDownClicked()
                    }
                }
            }
            
            // 删除按钮
            Button {
                icon.source: "qrc:/images/delete.png"
                icon.width: 16
                icon.height: 16
                onClicked: {
                    deleteClicked()
                }
            }
        }
        
        // 内容区域：根据规则类型显示不同的配置项
        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            // 正则替换配置项
            Rectangle {
                id: regexReplaceConfig
                visible: ruleStep.type === "regex_replace"
                anchors.fill: parent
                color: "transparent"
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 5
                    
                    // 正则表达式输入框
                    TextField {
                        Layout.fillWidth: true
                        text: ruleStep.pattern || ""
                        placeholderText: "正则表达式"
                        onTextChanged: {
                            ruleStep.pattern = text
                            ruleStepChanged()
                        }
                    }
                    
                    // 替换字符串输入框
                    TextField {
                        Layout.fillWidth: true
                        text: ruleStep.replacement || ""
                        placeholderText: "替换字符串"
                        onTextChanged: {
                            ruleStep.replacement = text
                            ruleStepChanged()
                        }
                    }
                    
                    // 正则表达式标志
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        CheckBox {
                            text: "IGNORECASE"
                            checked: ruleStep.flags && ruleStep.flags.indexOf("IGNORECASE") !== -1
                            onCheckedChanged: {
                                if (!ruleStep.flags) {
                                    ruleStep.flags = []
                                }
                                if (checked) {
                                    if (ruleStep.flags.indexOf("IGNORECASE") === -1) {
                                        ruleStep.flags.push("IGNORECASE")
                                    }
                                } else {
                                    var index = ruleStep.flags.indexOf("IGNORECASE")
                                    if (index !== -1) {
                                        ruleStep.flags.splice(index, 1)
                                    }
                                }
                                ruleStepChanged()
                            }
                        }
                        
                        CheckBox {
                            text: "MULTILINE"
                            checked: ruleStep.flags && ruleStep.flags.indexOf("MULTILINE") !== -1
                            onCheckedChanged: {
                                if (!ruleStep.flags) {
                                    ruleStep.flags = []
                                }
                                if (checked) {
                                    if (ruleStep.flags.indexOf("MULTILINE") === -1) {
                                        ruleStep.flags.push("MULTILINE")
                                    }
                                } else {
                                    var index = ruleStep.flags.indexOf("MULTILINE")
                                    if (index !== -1) {
                                        ruleStep.flags.splice(index, 1)
                                    }
                                }
                                ruleStepChanged()
                            }
                        }
                        
                        CheckBox {
                            text: "DOTALL"
                            checked: ruleStep.flags && ruleStep.flags.indexOf("DOTALL") !== -1
                            onCheckedChanged: {
                                if (!ruleStep.flags) {
                                    ruleStep.flags = []
                                }
                                if (checked) {
                                    if (ruleStep.flags.indexOf("DOTALL") === -1) {
                                        ruleStep.flags.push("DOTALL")
                                    }
                                } else {
                                    var index = ruleStep.flags.indexOf("DOTALL")
                                    if (index !== -1) {
                                        ruleStep.flags.splice(index, 1)
                                    }
                                }
                                ruleStepChanged()
                            }
                        }
                    }
                }
            }
            
            // 大小写转换配置项
            Rectangle {
                id: caseConversionConfig
                visible: ruleStep.type === "case_conversion"
                anchors.fill: parent
                color: "transparent"
                
                RowLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: "转换类型："
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    ComboBox {
                        model: ["none", "uppercase", "lowercase", "titlecase"]
                        currentIndex: ruleStep.conversion_type === "uppercase" ? 1 : ruleStep.conversion_type === "lowercase" ? 2 : ruleStep.conversion_type === "titlecase" ? 3 : 0
                        onCurrentTextChanged: {
                            ruleStep.conversion_type = currentText
                            ruleStepChanged()
                        }
                    }
                }
            }
            
            // 自定义Python片段配置项
            Rectangle {
                id: pythonSnippetConfig
                visible: ruleStep.type === "python_snippet"
                anchors.fill: parent
                color: "transparent"
                
                TextEdit {
                    anchors.fill: parent
                    text: ruleStep.code || "output = input"
                    placeholderText: "输入Python代码，使用input获取输入文本，将结果赋值给output"
                    font.family: "Consolas"
                    font.size: 12
                    onTextChanged: {
                        ruleStep.code = text
                        ruleStepChanged()
                    }
                }
            }
            
            // 空行合并配置项
            Rectangle {
                id: mergeEmptyLinesConfig
                visible: ruleStep.type === "merge_empty_lines"
                anchors.fill: parent
                color: "transparent"
                
                Label {
                    anchors.centerIn: parent
                    text: "将连续的空行合并为一个空行"
                }
            }
        }
    }
}
