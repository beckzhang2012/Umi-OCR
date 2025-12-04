// ===============================================
// =============== 后处理规则页面 ===============
// ===============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import "../../Widgets"
import "../../Widgets/Configs"

TabPage {
    id: tabPage
    property string currentTarget: "screenshot_ocr"
    property var currentRules: []
    property var templates: []
    property string previewText: "这是一个测试文本。\n\n1. 第一点\n2. 第二点\n\n(1) 子点一\n(2) 子点二\n\n全角字符：ＡＢＣ１２３！＠＃\n半角字符：ABC123!@#\n\n多余的   空格   和\n\n\n空行。"
    property var previewResult: {}

    // ========================= 【初始化】 =========================

    Component.onCompleted: {
        loadRules()
        loadTemplates()
        updatePreview()
    }

    function loadRules() {
        currentRules = callPy("get_rules")
    }

    function loadTemplates() {
        templates = callPy("get_templates")
    }

    function saveRules() {
        callPy("set_rules", currentTarget, currentRules[currentTarget])
    }

    function updatePreview() {
        previewResult = callPy("preview", currentTarget, previewText)
    }

    // ========================= 【UI布局】 =========================

    DoubleRowLayout {
        anchors.fill: parent
        initSplitterX: size_.line * 25

        // 左面板：规则管理
        leftItem: Panel {
            anchors.fill: parent
            ColumnLayout {
                anchors.fill: parent
                spacing: size_.spacing

                // 目标选择
                RowLayout {
                    Label {
                        text: qsTr("应用到：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    ComboBox {
                        id: targetComboBox
                        model: [
                            {key: "screenshot_ocr", text: qsTr("截图OCR")},
                            {key: "batch_ocr", text: qsTr("批量OCR")},
                            {key: "batch_doc", text: qsTr("批量文档")}
                        ]
                        textRole: "text"
                        valueRole: "key"
                        currentIndex: 0
                        onCurrentValueChanged: {
                            currentTarget = currentValue
                            updatePreview()
                        }
                    }
                }

                // 规则列表
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    Column {
                        id: rulesColumn
                        anchors.fill: parent
                        spacing: size_.smallSpacing

                        Repeater {
                            id: rulesRepeater
                            model: currentRules[currentTarget] || []

                            RuleItem {
                                id: ruleItem
                                width: rulesColumn.width
                                rule: modelData
                                index: index

                                onRuleChanged: {
                                    currentRules[currentTarget][index] = rule
                                    saveRules()
                                    updatePreview()
                                }

                                onDeleteRequested: {
                                    currentRules[currentTarget].splice(index, 1)
                                    saveRules()
                                    updatePreview()
                                }

                                onMoveUpRequested: {
                                    if (index > 0) {
                                        var temp = currentRules[currentTarget][index]
                                        currentRules[currentTarget][index] = currentRules[currentTarget][index - 1]
                                        currentRules[currentTarget][index - 1] = temp
                                        saveRules()
                                        updatePreview()
                                    }
                                }

                                onMoveDownRequested: {
                                    if (index < currentRules[currentTarget].length - 1) {
                                        var temp = currentRules[currentTarget][index]
                                        currentRules[currentTarget][index] = currentRules[currentTarget][index + 1]
                                        currentRules[currentTarget][index + 1] = temp
                                        saveRules()
                                        updatePreview()
                                    }
                                }
                            }
                        }
                    }
                }

                // 添加规则按钮
                RowLayout {
                    Button_ {
                        text_: qsTr("添加正则替换")
                        onClicked: {
                            var newRule = {
                                type: "regex_replace",
                                enabled: true,
                                name: qsTr("新正则替换规则"),
                                pattern: "",
                                replacement: "",
                                case_insensitive: false,
                                multiline: false,
                                dotall: false
                            }
                            currentRules[currentTarget].push(newRule)
                            saveRules()
                            updatePreview()
                        }
                    }
                    Button_ {
                        text_: qsTr("添加大小写转换")
                        onClicked: {
                            var newRule = {
                                type: "upper_case",
                                enabled: true,
                                name: qsTr("新大小写转换规则"),
                                conversion_type: "upper"
                            }
                            currentRules[currentTarget].push(newRule)
                            saveRules()
                            updatePreview()
                        }
                    }
                    Button_ {
                        text_: qsTr("添加全角半角转换")
                        onClicked: {
                            var newRule = {
                                type: "full_to_half",
                                enabled: true,
                                name: qsTr("新全角半角转换规则"),
                                conversion_type: "full_to_half"
                            }
                            currentRules[currentTarget].push(newRule)
                            saveRules()
                            updatePreview()
                        }
                    }
                    Button_ {
                        text_: qsTr("添加空行合并")
                        onClicked: {
                            var newRule = {
                                type: "merge_empty_lines",
                                enabled: true,
                                name: qsTr("新空行合并规则")
                            }
                            currentRules[currentTarget].push(newRule)
                            saveRules()
                            updatePreview()
                        }
                    }
                    Button_ {
                        text_: qsTr("添加Python脚本")
                        onClicked: {
                            var newRule = {
                                type: "python_script",
                                enabled: true,
                                name: qsTr("新Python脚本规则"),
                                script: "result = text"
                            }
                            currentRules[currentTarget].push(newRule)
                            saveRules()
                            updatePreview()
                        }
                    }
                }

                // 模板和导入导出
                RowLayout {
                    ComboBox {
                        id: templateComboBox
                        model: templates
                        textRole: "name"
                        width: size_.line * 10
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0) {
                                var template = templates[currentIndex]
                                var confirmed = confirm(qsTr("确定要应用模板\"%1\"吗？这将覆盖当前所有规则。").arg(template.name))
                                if (confirmed) {
                                    callPy("apply_template", currentTarget, template.name)
                                    loadRules()
                                    updatePreview()
                                }
                                currentIndex = -1
                            }
                        }
                    }
                    Button_ {
                        text_: qsTr("导出规则")
                        onClicked: {
                            var rulesJson = callPy("export_rules", currentTarget)
                            if (rulesJson) {
                                var dialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FileDialog { title: "导出规则"; selectExisting: false; nameFilters: ["JSON文件 (*.json)"] }', tabPage)
                                dialog.accepted.connect(function() {
                                    var file = Qt.createQmlObject('import QtQuick 2.15; TextFile {}', tabPage)
                                    if (file.open(dialog.fileUrl, TextFile.WriteOnly | TextFile.Truncate)) {
                                        file.write(rulesJson)
                                        file.close()
                                    }
                                })
                                dialog.open()
                            }
                        }
                    }
                    Button_ {
                        text_: qsTr("导入规则")
                        onClicked: {
                            var dialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; FileDialog { title: "导入规则"; selectExisting: true; nameFilters: ["JSON文件 (*.json)"] }', tabPage)
                            dialog.accepted.connect(function() {
                                var file = Qt.createQmlObject('import QtQuick 2.15; TextFile {}', tabPage)
                                if (file.open(dialog.fileUrl, TextFile.ReadOnly)) {
                                    var rulesJson = file.readAll()
                                    file.close()
                                    callPy("import_rules", currentTarget, rulesJson)
                                    loadRules()
                                    updatePreview()
                                }
                            })
                            dialog.open()
                        }
                    }
                }
            }
        }

        // 右面板：预览
        rightItem: Panel {
            anchors.fill: parent
            ColumnLayout {
                anchors.fill: parent
                spacing: size_.spacing

                // 预览文本输入
                GroupBox {
                    title: qsTr("测试文本")
                    Layout.fillWidth: true
                    Layout.preferredHeight: size_.line * 10

                    TextEdit_ {
                        id: previewTextEdit
                        anchors.fill: parent
                        text: previewText
                        onTextChanged: {
                            previewText = text
                            updatePreview()
                        }
                    }
                }

                // 预览结果
                GroupBox {
                    title: qsTr("处理结果")
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ScrollView {
                        anchors.fill: parent
                        clip: true

                        Column {
                            anchors.fill: parent
                            spacing: size_.smallSpacing

                            // 最终结果
                            Text_ {
                                text: qsTr("最终结果：")
                                color: theme.textColor
                                font.pixelSize: size_.text
                                font.bold: true
                            }
                            TextEdit_ {
                                readOnly: true
                                text: previewResult.result || ""
                                height: size_.line * 5
                            }

                            // 步骤详情
                            Text_ {
                                text: qsTr("步骤详情：")
                                color: theme.textColor
                                font.pixelSize: size_.text
                                font.bold: true
                            }
                            Repeater {
                                model: previewResult.steps || []

                                GroupBox {
                                    title: modelData.name
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: size_.line * 8

                                    ColumnLayout {
                                        Text_ {
                                            text: qsTr("输入：")
                                            color: theme.textColor
                                            font.pixelSize: size_.smallText
                                            font.bold: true
                                        }
                                        TextEdit_ {
                                            readOnly: true
                                            text: modelData.input
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: size_.line * 2
                                        }
                                        Text_ {
                                            text: qsTr("输出：")
                                            color: theme.textColor
                                            font.pixelSize: size_.smallText
                                            font.bold: true
                                        }
                                        TextEdit_ {
                                            readOnly: true
                                            text: modelData.output
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: size_.line * 2
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ===============================================
// =============== 规则项组件 ===============
// ===============================================

Component {
    id: RuleItem

    Rectangle {
        id: ruleItemRoot
        property var rule
        property int index
        width: parent.width
        height: content.height + size_.spacing * 2
        color: theme.bgColor
        border.width: 1
        border.color: theme.coverColor4
        radius: size_.btnRadius

        signal ruleChanged(var rule)
        signal deleteRequested()
        signal moveUpRequested()
        signal moveDownRequested()

        Column {
            id: content
            anchors.fill: parent
            anchors.margins: size_.spacing
            spacing: size_.smallSpacing

            // 规则头部
            RowLayout {
                CheckBox {
                    checked: rule.enabled
                    onCheckedChanged: {
                        rule.enabled = checked
                        ruleChanged(rule)
                    }
                }
                Text_ {
                    text: rule.name
                    color: theme.textColor
                    font.pixelSize: size_.text
                    Layout.fillWidth: true
                }
                Button_ {
                    text_: "↑"
                    onClicked: moveUpRequested()
                    enabled: index > 0
                }
                Button_ {
                    text_: "↓"
                    onClicked: moveDownRequested()
                    enabled: index < rulesRepeater.count - 1
                }
                Button_ {
                    text_: qsTr("删除")
                    onClicked: deleteRequested()
                }
            }

            // 规则类型特定配置
            Loader {
                id: configLoader
                Layout.fillWidth: true
                Layout.fillHeight: true

                sourceComponent: {
                    switch (rule.type) {
                        case "regex_replace": return regexReplaceConfig
                        case "upper_case":
                        case "lower_case":
                        case "title_case":
                        case "capitalize": return caseConversionConfig
                        case "full_to_half":
                        case "half_to_full": return fullHalfConversionConfig
                        case "merge_empty_lines":
                        case "trim_lines": return textProcessingConfig
                        case "python_script": return pythonScriptConfig
                        default: return emptyConfig
                    }
                }
            }
        }

        // 正则替换配置
        Component {
            id: regexReplaceConfig

            ColumnLayout {
                spacing: size_.smallSpacing

                RowLayout {
                    Label {
                        text: qsTr("规则名称：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.name
                        onTextChanged: {
                            rule.name = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("正则表达式：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.pattern || ""
                        onTextChanged: {
                            rule.pattern = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("替换为：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.replacement || ""
                        onTextChanged: {
                            rule.replacement = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    CheckBox {
                        text: qsTr("不区分大小写")
                        checked: rule.case_insensitive || false
                        onCheckedChanged: {
                            rule.case_insensitive = checked
                            ruleChanged(rule)
                        }
                    }
                    CheckBox {
                        text: qsTr("多行模式")
                        checked: rule.multiline || false
                        onCheckedChanged: {
                            rule.multiline = checked
                            ruleChanged(rule)
                        }
                    }
                    CheckBox {
                        text: qsTr("点匹配换行符")
                        checked: rule.dotall || false
                        onCheckedChanged: {
                            rule.dotall = checked
                            ruleChanged(rule)
                        }
                    }
                }
            }
        }

        // 大小写转换配置
        Component {
            id: caseConversionConfig

            ColumnLayout {
                spacing: size_.smallSpacing

                RowLayout {
                    Label {
                        text: qsTr("规则名称：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.name
                        onTextChanged: {
                            rule.name = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("转换类型：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    ComboBox {
                        model: [
                            {key: "upper_case", text: qsTr("全部大写")},
                            {key: "lower_case", text: qsTr("全部小写")},
                            {key: "title_case", text: qsTr("首字母大写")},
                            {key: "capitalize", text: qsTr("句子首字母大写")}
                        ]
                        textRole: "text"
                        valueRole: "key"
                        currentValue: rule.type
                        onCurrentValueChanged: {
                            rule.type = currentValue
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // 全角半角转换配置
        Component {
            id: fullHalfConversionConfig

            ColumnLayout {
                spacing: size_.smallSpacing

                RowLayout {
                    Label {
                        text: qsTr("规则名称：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.name
                        onTextChanged: {
                            rule.name = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("转换类型：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    ComboBox {
                        model: [
                            {key: "full_to_half", text: qsTr("全角转半角")},
                            {key: "half_to_full", text: qsTr("半角转全角")}
                        ]
                        textRole: "text"
                        valueRole: "key"
                        currentValue: rule.type
                        onCurrentValueChanged: {
                            rule.type = currentValue
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // 文本处理配置
        Component {
            id: textProcessingConfig

            ColumnLayout {
                spacing: size_.smallSpacing

                RowLayout {
                    Label {
                        text: qsTr("规则名称：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.name
                        onTextChanged: {
                            rule.name = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("处理类型：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    ComboBox {
                        model: [
                            {key: "merge_empty_lines", text: qsTr("合并空行")},
                            {key: "trim_lines", text: qsTr("去除行首尾空格")}
                        ]
                        textRole: "text"
                        valueRole: "key"
                        currentValue: rule.type
                        onCurrentValueChanged: {
                            rule.type = currentValue
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // Python脚本配置
        Component {
            id: pythonScriptConfig

            ColumnLayout {
                spacing: size_.smallSpacing

                RowLayout {
                    Label {
                        text: qsTr("规则名称：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                    TextField {
                        text: rule.name
                        onTextChanged: {
                            rule.name = text
                            ruleChanged(rule)
                        }
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Label {
                        text: qsTr("Python脚本：")
                        color: theme.textColor
                        font.pixelSize: size_.text
                    }
                }
                TextEdit_ {
                    text: rule.script || "result = text"
                    onTextChanged: {
                        rule.script = text
                        ruleChanged(rule)
                    }
                    Layout.fillWidth: true
                    Layout.preferredHeight: size_.line * 5
                    wrapMode: TextEdit.Wrap
                }
                Text_ {
                    text: qsTr("提示：脚本中可用变量为text，处理结果请赋值给result")
                    color: theme.textColorSecondary
                    font.pixelSize: size_.smallText
                }
            }
        }

        // 空配置
        Component {
            id: emptyConfig

            Text_ {
                text: qsTr("未知规则类型")
                color: theme.textColorSecondary
                font.pixelSize: size_.text
            }
        }
    }
}
