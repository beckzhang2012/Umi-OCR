// =============================================
// =============== 后处理规则页面 ===============
// =============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

import ".."

TabPage {
    id: postProcessRulesPage
    ctrlKey: "PostProcessRules"
    
    // 当前选中的OCR类型
    property string currentOcrType: "screenshot_ocr"
    // 当前规则列表
    property var currentRules: []
    // 输入文本
    property string inputText: "示例文本\n1. 第一条\n2. 第二条\n\n全角字符：ＡＢＣ１２３"
    // 输出文本
    property string outputText: ""
    
    // 页面展示时加载规则
    onShowPage: {
        loadRules()
    }
    
    // 加载规则
    function loadRules() {
        currentRules = callPy("load_rules", currentOcrType)
        applyRules()
    }
    
    // 保存规则
    function saveRules() {
        var result = callPy("save_rules", currentOcrType, currentRules)
        if (result) {
            qmlapp.popup.showSimple("保存成功", "后处理规则已保存")
        } else {
            qmlapp.popup.showSimple("保存失败", "后处理规则保存失败")
        }
    }
    
    // 应用规则
    function applyRules() {
        outputText = callPy("apply_rules", currentOcrType, inputText)
    }
    
    // 添加规则步骤
    function addRuleStep(type) {
        var newStep = {
            id: Math.random().toString(36).substr(2, 9),
            type: type,
            enabled: true,
            name: "新规则步骤"
        }
        // 根据类型添加默认值
        if (type === "regex_replace") {
            newStep.pattern = ""
            newStep.replacement = ""
            newStep.flags = []
        } else if (type === "case_conversion") {
            newStep.conversion_type = "none"
        } else if (type === "python_snippet") {
            newStep.code = "output = input"
        }
        currentRules.push(newStep)
        applyRules()
    }
    
    // 删除规则步骤
    function deleteRuleStep(index) {
        currentRules.splice(index, 1)
        applyRules()
    }
    
    // 移动规则步骤
    function moveRuleStep(fromIndex, toIndex) {
        var step = currentRules.splice(fromIndex, 1)[0]
        currentRules.splice(toIndex, 0, step)
        applyRules()
    }
    
    // 加载模板
    function loadTemplate(templateName) {
        var template = callPy("get_template", templateName)
        if (template) {
            currentRules = template.steps
            applyRules()
            qmlapp.popup.showSimple("模板加载成功", template.name)
        } else {
            qmlapp.popup.showSimple("模板加载失败", "模板不存在或加载失败")
        }
    }
    
    // 导出规则
    function exportRules() {
        fileDialog.title = "导出规则"
        fileDialog.selectExisting = false
        fileDialog.fileName = "post_process_rules.json"
        fileDialog.filters = ["JSON files (*.json)"]
        fileDialog.open()
    }
    
    // 导入规则
    function importRules() {
        fileDialog.title = "导入规则"
        fileDialog.selectExisting = true
        fileDialog.filters = ["JSON files (*.json)"]
        fileDialog.open()
    }
    
    // 布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        
        // 顶部工具栏
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            // OCR类型选择
            ComboBox {
                id: ocrTypeComboBox
                model: ["screenshot_ocr", "batch_ocr", "batch_doc"]
                currentIndex: 0
                onCurrentTextChanged: {
                    currentOcrType = currentText
                    loadRules()
                }
            }
            
            // 保存按钮
            Button {
                text: "保存规则"
                onClicked: {
                    saveRules()
                }
            }
            
            // 模板按钮
            MenuButton {
                text: "模板"
                
                Menu {
                    id: templateMenu
                    
                    Action {
                        text: "全角转半角"
                        onClicked: {
                            loadTemplate("full_width_to_half_width")
                        }
                    }
                    Action {
                        text: "去序号"
                        onClicked: {
                            loadTemplate("remove_serial_numbers")
                        }
                    }
                }
            }
            
            // 导入导出按钮
            RowLayout {
                spacing: 5
                
                Button {
                    text: "导入"
                    onClicked: {
                        importRules()
                    }
                }
                
                Button {
                    text: "导出"
                    onClicked: {
                        exportRules()
                    }
                }
            }
        }
        
        // 规则步骤列表和预览区域
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            
            // 规则步骤列表
            ColumnLayout {
                Layout.preferredWidth: 400
                Layout.fillHeight: true
                spacing: 10
                
                // 添加规则步骤按钮
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    
                    Button {
                        text: "正则替换"
                        onClicked: {
                            addRuleStep("regex_replace")
                        }
                    }
                    
                    Button {
                        text: "大小写转换"
                        onClicked: {
                            addRuleStep("case_conversion")
                        }
                    }
                    
                    Button {
                        text: "空行合并"
                        onClicked: {
                            addRuleStep("merge_empty_lines")
                        }
                    }
                    
                    Button {
                        text: "Python片段"
                        onClicked: {
                            addRuleStep("python_snippet")
                        }
                    }
                }
                
                // 规则步骤列表视图
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ListView {
                        id: ruleStepsListView
                        model: currentRules
                        delegate: RuleStepDelegate {
                            id: ruleStepDelegate
                            ruleStep: modelData
                            index: model.index
                            
                            onDeleteClicked: {
                                deleteRuleStep(index)
                            }
                            
                            onMoveUpClicked: {
                                if (index > 0) {
                                    moveRuleStep(index, index - 1)
                                }
                            }
                            
                            onMoveDownClicked: {
                                if (index < currentRules.length - 1) {
                                    moveRuleStep(index, index + 1)
                                }
                            }
                            
                            onRuleStepChanged: {
                                applyRules()
                            }
                        }
                    }
                }
            }
            
            // 预览区域
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10
                
                // 输入文本区域
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    
                    TextEdit {
                        id: inputTextEdit
                        anchors.fill: parent
                        text: inputText
                        placeholderText: "输入要处理的文本"
                        onTextChanged: {
                            inputText = text
                            applyRules()
                        }
                    }
                }
                
                // 输出文本区域
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    TextEdit {
                        id: outputTextEdit
                        anchors.fill: parent
                        text: outputText
                        placeholderText: "处理后的文本"
                        readOnly: true
                    }
                }
            }
        }
    }
    
    // 文件对话框
    FileDialog {
        id: fileDialog
        
        onAccepted: {
            var filePath = fileUrl.toString().replace("file:///", "").replace(/\//g, "\\")
            if (title === "导出规则") {
                var result = callPy("export_rules", filePath, currentRules)
                if (result) {
                    qmlapp.popup.showSimple("导出成功", "规则已导出到：" + filePath)
                } else {
                    qmlapp.popup.showSimple("导出失败", "规则导出失败")
                }
            } else if (title === "导入规则") {
                var importedRules = callPy("import_rules", filePath)
                if (importedRules && importedRules.length > 0) {
                    currentRules = importedRules
                    applyRules()
                    qmlapp.popup.showSimple("导入成功", "规则已从：" + filePath + " 导入")
                } else {
                    qmlapp.popup.showSimple("导入失败", "规则导入失败或文件为空")
                }
            }
        }
    }
}
