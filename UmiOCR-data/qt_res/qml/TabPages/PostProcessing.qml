import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import "../common"

Item {
    id: root
    width: parent.width
    height: parent.height
    
    property var controller
    
    // 状态变量
    property var currentRuleSet: {}
    property var previewResults: []
    property var availableStepTypes: []
    property var caseTypes: []
    property var ocrTypes: []
    property string selectedSetId: ""
    property string previewText: ""
    
    // 对话框状态
    property bool showAddSetDialog: false
    property bool showEditSetDialog: false
    property bool showAddStepDialog: false
    property bool showEditStepDialog: false
    property bool showExportDialog: false
    property bool showImportDialog: false
    
    // 对话框数据
    property var dialogSetData: {}
    property var dialogStepData: {}
    property string dialogStepType: ""
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        
        // 顶部工具栏
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            
            Label {
                text: qsTr("后处理规则")
                font.pixelSize: 20
                font.bold: true
            }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: qsTr("添加规则集")
                onClicked: {
                    dialogSetData = { name: "", description: "", bind_types: [] }
                    showAddSetDialog = true
                }
            }
            
            Button {
                text: qsTr("导入")
                onClicked: showImportDialog = true
            }
            
            Button {
                text: qsTr("导出")
                enabled: selectedSetId !== ""
                onClicked: showExportDialog = true
            }
        }
        
        // 主内容区域
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 10
            spacing: 10
            
            // 左侧：规则集列表
            ColumnLayout {
                Layout.width: 250
                Layout.fillHeight: true
                spacing: 10
                
                Label {
                    text: qsTr("规则集列表")
                    font.bold: true
                }
                
                ListView {
                    id: ruleSetsListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: controller ? controller.ruleSets : []
                    delegate: ItemDelegate {
                        width: parent.width
                        text: model.name
                        checked: model.id === selectedSetId
                        onPressed: {
                            selectedSetId = model.id
                            currentRuleSet = controller.getRuleSet(model.id)
                        }
                        
                        Menu {
                            id: ruleSetMenu
                            
                            MenuItem {
                                text: qsTr("编辑")
                                onClicked: {
                                    dialogSetData = {
                                        name: model.name,
                                        description: model.description,
                                        bind_types: model.bind_types
                                    }
                                    showEditSetDialog = true
                                }
                            }
                            
                            MenuItem {
                                text: qsTr("删除")
                                onClicked: {
                                    if (confirmDialog(qsTr("确定要删除这个规则集吗？"))) {
                                        controller.deleteRuleSet(model.id)
                                        if (selectedSetId === model.id) {
                                            selectedSetId = ""
                                            currentRuleSet = {}
                                        }
                                    }
                                }
                            }
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.RightButton
                            onClicked: {
                                if (mouse.button === Qt.RightButton) {
                                    ruleSetMenu.popup()
                                }
                            }
                        }
                    }
                }
            }
            
            // 中间：规则编辑器
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10
                
                // 规则集信息
                GroupBox {
                    Layout.fillWidth: true
                    title: qsTr("规则集信息")
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("名称：")
                                Layout.alignment: Qt.AlignVCenter
                            }
                            
                            TextField {
                                Layout.fillWidth: true
                                text: currentRuleSet.name || ""
                                readOnly: true
                            }
                        }
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("描述：")
                                Layout.alignment: Qt.AlignTop
                            }
                            
                            TextArea {
                                Layout.fillWidth: true
                                Layout.maximumHeight: 80
                                text: currentRuleSet.description || ""
                                readOnly: true
                            }
                        }
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("绑定类型：")
                                Layout.alignment: Qt.AlignVCenter
                            }
                            
                            Label {
                                text: (currentRuleSet.bind_types || []).map(function(type) {
                                    for (var i = 0; i < ocrTypes.length; i++) {
                                        if (ocrTypes[i].value === type) {
                                            return ocrTypes[i].name
                                        }
                                    }
                                    return type
                                }).join(", ") || qsTr("未绑定")
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                        }
                    }
                }
                
                // 规则步骤列表
                GroupBox {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: qsTr("规则步骤")
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        
                        Button {
                            text: qsTr("添加步骤")
                            enabled: selectedSetId !== ""
                            onClicked: {
                                if (availableStepTypes.length === 0) {
                                    availableStepTypes = controller.getAvailableStepTypes()
                                }
                                showAddStepDialog = true
                            }
                        }
                        
                        ListView {
                            id: stepsListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: currentRuleSet.steps || []
                            delegate: Item {
                                width: parent.width
                                height: 60
                                
                                Rectangle {
                                    anchors.fill: parent
                                    color: index % 2 === 0 ? "#f0f0f0" : "#ffffff"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 5
                                        spacing: 10
                                        
                                        CheckBox {
                                            checked: model.enabled
                                            onCheckedChanged: {
                                                controller.toggleStepInSet(selectedSetId, model.id)
                                            }
                                            Layout.alignment: Qt.AlignVCenter
                                        }
                                        
                                        Label {
                                            text: model.name
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                        }
                                        
                                        Label {
                                            text: getStepTypeName(model.type)
                                            color: "#666666"
                                            Layout.alignment: Qt.AlignVCenter
                                        }
                                        
                                        Button {
                                            text: qsTr("编辑")
                                            onClicked: {
                                                dialogStepData = model
                                                showEditStepDialog = true
                                            }
                                        }
                                        
                                        Button {
                                            text: qsTr("删除")
                                            onClicked: {
                                                if (confirmDialog(qsTr("确定要删除这个步骤吗？"))) {
                                                    controller.removeStepFromSet(selectedSetId, model.id)
                                                }
                                            }
                                        }
                                    }
                                    
                                    // 拖拽排序
                                    MouseArea {
                                        anchors.fill: parent
                                        drag.target: parent
                                        drag.axis: Drag.YAxis
                                        onReleased: {
                                            var newIndex = Math.round(y / 60)
                                            if (newIndex >= 0 && newIndex < stepsListView.count && newIndex !== index) {
                                                controller.moveStepInSet(selectedSetId, index, newIndex)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            // 右侧：实时预览
            ColumnLayout {
                Layout.width: 300
                Layout.fillHeight: true
                spacing: 10
                
                GroupBox {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: qsTr("实时预览")
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        
                        Label {
                            text: qsTr("输入文本：")
                            font.bold: true
                        }
                        
                        TextArea {
                            Layout.fillWidth: true
                            Layout.maximumHeight: 100
                            text: previewText
                            onTextChanged: {
                                previewText = text
                                if (selectedSetId !== "" && text.trim() !== "") {
                                    controller.previewText(selectedSetId, text)
                                }
                            }
                        }
                        
                        Label {
                            text: qsTr("处理结果：")
                            font.bold: true
                        }
                        
                        ListView {
                            id: previewListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: previewResults
                            delegate: Item {
                                width: parent.width
                                height: 80
                                
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 5
                                    
                                    Label {
                                        text: model.step_name
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    
                                    TextArea {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        text: model.result
                                        readOnly: true
                                        wrapMode: TextArea.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // 添加规则集对话框
    Dialog {
        id: addSetDialog
        visible: showAddSetDialog
        title: qsTr("添加规则集")
        modality: Qt.WindowModal
        
        ColumnLayout {
            width: 400
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("名称：")
                    Layout.alignment: Qt.AlignVCenter
                }
                
                TextField {
                    Layout.fillWidth: true
                    text: dialogSetData.name
                    onTextChanged: dialogSetData.name = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("描述：")
                    Layout.alignment: Qt.AlignTop
                }
                
                TextArea {
                    Layout.fillWidth: true
                    Layout.maximumHeight: 80
                    text: dialogSetData.description
                    onTextChanged: dialogSetData.description = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("绑定类型：")
                    Layout.alignment: Qt.AlignTop
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    
                    Repeater {
                        model: ocrTypes
                        delegate: CheckBox {
                            text: model.name
                            checked: dialogSetData.bind_types.indexOf(model.value) !== -1
                            onCheckedChanged: {
                                if (checked) {
                                    dialogSetData.bind_types.push(model.value)
                                } else {
                                    var index = dialogSetData.bind_types.indexOf(model.value)
                                    if (index !== -1) {
                                        dialogSetData.bind_types.splice(index, 1)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (dialogSetData.name.trim() === "") {
                messageDialog(qsTr("请输入规则集名称"))
                return
            }
            
            var setId = controller.addRuleSet(dialogSetData)
            if (setId) {
                selectedSetId = setId
                currentRuleSet = controller.getRuleSet(setId)
            }
            showAddSetDialog = false
        }
        onRejected: {
            showAddSetDialog = false
        }
    }
    
    // 编辑规则集对话框
    Dialog {
        id: editSetDialog
        visible: showEditSetDialog
        title: qsTr("编辑规则集")
        modality: Qt.WindowModal
        
        ColumnLayout {
            width: 400
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("名称：")
                    Layout.alignment: Qt.AlignVCenter
                }
                
                TextField {
                    Layout.fillWidth: true
                    text: dialogSetData.name
                    onTextChanged: dialogSetData.name = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("描述：")
                    Layout.alignment: Qt.AlignTop
                }
                
                TextArea {
                    Layout.fillWidth: true
                    Layout.maximumHeight: 80
                    text: dialogSetData.description
                    onTextChanged: dialogSetData.description = text
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("绑定类型：")
                    Layout.alignment: Qt.AlignTop
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    
                    Repeater {
                        model: ocrTypes
                        delegate: CheckBox {
                            text: model.name
                            checked: dialogSetData.bind_types.indexOf(model.value) !== -1
                            onCheckedChanged: {
                                if (checked) {
                                    dialogSetData.bind_types.push(model.value)
                                } else {
                                    var index = dialogSetData.bind_types.indexOf(model.value)
                                    if (index !== -1) {
                                        dialogSetData.bind_types.splice(index, 1)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (dialogSetData.name.trim() === "") {
                messageDialog(qsTr("请输入规则集名称"))
                return
            }
            
            controller.updateRuleSet(selectedSetId, dialogSetData)
            currentRuleSet = controller.getRuleSet(selectedSetId)
            showEditSetDialog = false
        }
        onRejected: {
            showEditSetDialog = false
        }
    }
    
    // 添加步骤对话框
    Dialog {
        id: addStepDialog
        visible: showAddStepDialog
        title: qsTr("添加步骤")
        modality: Qt.WindowModal
        
        ColumnLayout {
            width: 400
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("步骤类型：")
                    Layout.alignment: Qt.AlignVCenter
                }
                
                ComboBox {
                    Layout.fillWidth: true
                    model: availableStepTypes
                    textRole: "name"
                    valueRole: "type"
                    onCurrentTextChanged: {
                        dialogStepType = currentValue
                    }
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("步骤名称：")
                    Layout.alignment: Qt.AlignVCenter
                }
                
                TextField {
                    Layout.fillWidth: true
                    text: dialogStepData.name
                    onTextChanged: dialogStepData.name = text
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (dialogStepData.name.trim() === "") {
                messageDialog(qsTr("请输入步骤名称"))
                return
            }
            
            if (!dialogStepType) {
                messageDialog(qsTr("请选择步骤类型"))
                return
            }
            
            var stepId = controller.addStepToSet(selectedSetId, dialogStepType, dialogStepData.name)
            if (stepId) {
                currentRuleSet = controller.getRuleSet(selectedSetId)
                // 预览文本
                if (previewText.trim() !== "") {
                    controller.previewText(selectedSetId, previewText)
                }
            }
            showAddStepDialog = false
        }
        onRejected: {
            showAddStepDialog = false
        }
    }
    
    // 编辑步骤对话框
    Dialog {
        id: editStepDialog
        visible: showEditStepDialog
        title: qsTr("编辑步骤")
        modality: Qt.WindowModal
        
        ColumnLayout {
            width: 500
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                
                Label {
                    text: qsTr("步骤名称：")
                    Layout.alignment: Qt.AlignVCenter
                }
                
                TextField {
                    Layout.fillWidth: true
                    text: dialogStepData.name
                    onTextChanged: dialogStepData.name = text
                }
            }
            
            // 根据步骤类型显示不同的参数设置
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    // 正则替换
                    ColumnLayout {
                        visible: dialogStepData.type === "regex_replace"
                        spacing: 10
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("正则表达式：")
                                Layout.alignment: Qt.AlignTop
                            }
                            
                            TextField {
                                Layout.fillWidth: true
                                text: dialogStepData.params.pattern || ""
                                onTextChanged: {
                                    dialogStepData.params.pattern = text
                                }
                            }
                        }
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("替换为：")
                                Layout.alignment: Qt.AlignTop
                            }
                            
                            TextField {
                                Layout.fillWidth: true
                                text: dialogStepData.params.replacement || ""
                                onTextChanged: {
                                    dialogStepData.params.replacement = text
                                }
                            }
                        }
                    }
                    
                    // 大小写转换
                    ColumnLayout {
                        visible: dialogStepData.type === "case_convert"
                        spacing: 10
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("转换类型：")
                                Layout.alignment: Qt.AlignVCenter
                            }
                            
                            ComboBox {
                                Layout.fillWidth: true
                                model: caseTypes
                                textRole: "name"
                                valueRole: "value"
                                currentIndex: caseTypes.findIndex(function(type) {
                                    return type.value === (dialogStepData.params.case_type || "upper")
                                })
                                onCurrentTextChanged: {
                                    dialogStepData.params.case_type = currentValue
                                }
                            }
                        }
                    }
                    
                    // 移除标点
                    ColumnLayout {
                        visible: dialogStepData.type === "remove_punctuation"
                        spacing: 10
                        
                        CheckBox {
                            text: qsTr("保留中文标点")
                            checked: dialogStepData.params.keep_chinese || false
                            onCheckedChanged: {
                                dialogStepData.params.keep_chinese = checked
                            }
                        }
                        
                        CheckBox {
                            text: qsTr("保留英文标点")
                            checked: dialogStepData.params.keep_english || false
                            onCheckedChanged: {
                                dialogStepData.params.keep_english = checked
                            }
                        }
                    }
                    
                    // 自定义Python
                    ColumnLayout {
                        visible: dialogStepData.type === "custom_python"
                        spacing: 10
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Label {
                                text: qsTr("Python代码：")
                                Layout.alignment: Qt.AlignTop
                            }
                            
                            TextArea {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: dialogStepData.params.code || ""
                                onTextChanged: {
                                    dialogStepData.params.code = text
                                }
                            }
                        }
                    }
                }
            }
        }
        
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (dialogStepData.name.trim() === "") {
                messageDialog(qsTr("请输入步骤名称"))
                return
            }
            
            controller.updateStepInSet(selectedSetId, dialogStepData.id, dialogStepData)
            currentRuleSet = controller.getRuleSet(selectedSetId)
            // 预览文本
            if (previewText.trim() !== "") {
                controller.previewText(selectedSetId, previewText)
            }
            showEditStepDialog = false
        }
        onRejected: {
            showEditStepDialog = false
        }
    }
    
    // 导出对话框
    FileDialog {
        id: exportDialog
        visible: showExportDialog
        title: qsTr("导出规则集")
        selectExisting: false
        selectFolder: false
        nameFilters: [qsTr("JSON文件 (*.json)")]
        defaultSuffix: "json"
        
        onAccepted: {
            var error = controller.exportRuleSet(selectedSetId, fileUrl.toLocalFile())
            if (error) {
                messageDialog(qsTr("导出失败：") + error)
            } else {
                messageDialog(qsTr("导出成功"))
            }
            showExportDialog = false
        }
        onRejected: {
            showExportDialog = false
        }
    }
    
    // 导入对话框
    FileDialog {
        id: importDialog
        visible: showImportDialog
        title: qsTr("导入规则集")
        selectExisting: true
        selectFolder: false
        nameFilters: [qsTr("JSON文件 (*.json)")]
        
        onAccepted: {
            var error = controller.importRuleSet(fileUrl.toLocalFile())
            if (error) {
                messageDialog(qsTr("导入失败：") + error)
            } else {
                messageDialog(qsTr("导入成功"))
            }
            showImportDialog = false
        }
        onRejected: {
            showImportDialog = false
        }
    }
    
    // 辅助函数
    function getStepTypeName(type) {
        for (var i = 0; i < availableStepTypes.length; i++) {
            if (availableStepTypes[i].type === type) {
                return availableStepTypes[i].name
            }
        }
        return type
    }
    
    function confirmDialog(message) {
        var dialog = createMessageDialog(message, qsTr("确认"), MessageDialog.Warning)
        dialog.standardButtons = MessageDialog.Ok | MessageDialog.Cancel
        return dialog.exec() === MessageDialog.Ok
    }
    
    function messageDialog(message) {
        var dialog = createMessageDialog(message, qsTr("提示"), MessageDialog.Information)
        dialog.exec()
    }
    
    function createMessageDialog(message, title, icon) {
        var dialog = Qt.createQmlObject('import QtQuick.Dialogs 1.3; MessageDialog {}', root)
        dialog.text = message
        dialog.title = title
        dialog.icon = icon
        dialog.standardButtons = MessageDialog.Ok
        return dialog
    }
    
    // 初始化
    Component.onCompleted: {
        if (controller) {
            // 获取可用类型
            availableStepTypes = controller.getAvailableStepTypes()
            caseTypes = controller.getCaseTypes()
            ocrTypes = controller.getOCRTypes()
            
            // 连接预览结果信号
            controller.previewResultsChanged.connect(function(results) {
                previewResults = results
            })
        }
    }
}