import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import "../utils" as Utils

// 多引擎方案管理组件
// 支持保存、加载、删除、导入、导出方案
Item {
    id: root
    width: parent.width
    height: parent.height

    // 输入属性
    property var currentEngineNames: []  // 当前引擎名称列表
    property var currentEngineConfigs: {}  // 当前引擎配置
    property var currentCommonConfig: {}  // 当前通用配置

    // 输出属性
    property var onSchemeLoaded: null  // 方案加载回调

    // 内部状态
    property var schemeList: []  // 方案列表
    property var selectedScheme: ""  // 当前选中的方案

    // 初始化
    Component.onCompleted: {
        refreshSchemeList()
    }

    // 刷新方案列表
    function refreshSchemeList() {
        qmlapp.callPy("mission.mission_multi_ocr_scheme.get_scheme_list", [], function(result) {
            schemeList = result
            schemeListModel.clear()
            for (var i = 0; i < result.length; i++) {
                schemeListModel.append({name: result[i]})
            }
        })
    }

    // 创建新方案
    function createScheme(name, description) {
        if (!name.trim()) {
            Utils.MessageBox.show("错误", "方案名称不能为空！")
            return false
        }

        // 检查是否已存在同名方案
        if (schemeList.indexOf(name) !== -1) {
            Utils.MessageBox.show("错误", "已存在同名方案！")
            return false
        }

        // 创建方案数据
        var schemeData = {
            name: name,
            description: description,
            engine_names: currentEngineNames,
            engine_configs: currentEngineConfigs,
            common_config: currentCommonConfig
        }

        // 保存方案
        qmlapp.callPy("mission.mission_multi_ocr_scheme.save_scheme", [schemeData], function(success) {
            if (success) {
                Utils.MessageBox.show("成功", "方案已创建！")
                refreshSchemeList()
            } else {
                Utils.MessageBox.show("错误", "创建方案失败！")
            }
        })

        return true
    }

    // 加载方案
    function loadScheme(name) {
        if (!name) {
            Utils.MessageBox.show("错误", "请选择要加载的方案！")
            return
        }

        qmlapp.callPy("mission.mission_multi_ocr_scheme.load_scheme", [name], function(schemeData) {
            if (schemeData) {
                selectedScheme = name
                if (onSchemeLoaded) {
                    onSchemeLoaded(schemeData)
                }
                Utils.MessageBox.show("成功", "方案已加载！")
            } else {
                Utils.MessageBox.show("错误", "加载方案失败！")
            }
        })
    }

    // 删除方案
    function deleteScheme(name) {
        if (!name) {
            Utils.MessageBox.show("错误", "请选择要删除的方案！")
            return
        }

        if (!Utils.MessageBox.confirm("确认", "确定要删除方案 '" + name + "' 吗？")) {
            return
        }

        qmlapp.callPy("mission.mission_multi_ocr_scheme.delete_scheme", [name], function(success) {
            if (success) {
                Utils.MessageBox.show("成功", "方案已删除！")
                refreshSchemeList()
                if (selectedScheme === name) {
                    selectedScheme = ""
                }
            } else {
                Utils.MessageBox.show("错误", "删除方案失败！")
            }
        })
    }

    // 导出方案
    function exportScheme(name) {
        if (!name) {
            Utils.MessageBox.show("错误", "请选择要导出的方案！")
            return
        }

        var dialog = Utils.FileDialog.create({
            title: "导出方案",
            selectExisting: false,
            selectFolder: false,
            nameFilters: ["JSON文件 (*.json)", "所有文件 (*)"]
        })

        dialog.accepted.connect(function() {
            var filePath = dialog.fileUrl.replace('file:///', '')
            qmlapp.callPy("mission.mission_multi_ocr_scheme.export_scheme", [name, filePath], function(success) {
                if (success) {
                    Utils.MessageBox.show("成功", "方案已导出到:\n" + filePath)
                } else {
                    Utils.MessageBox.show("错误", "导出方案失败！")
                }
            })
        })

        dialog.open()
    }

    // 导入方案
    function importScheme() {
        var dialog = Utils.FileDialog.create({
            title: "导入方案",
            selectExisting: true,
            selectFolder: false,
            nameFilters: ["JSON文件 (*.json)", "所有文件 (*)"]
        })

        dialog.accepted.connect(function() {
            var filePath = dialog.fileUrl.replace('file:///', '')
            qmlapp.callPy("mission.mission_multi_ocr_scheme.import_scheme", [filePath], function(schemeData) {
                if (schemeData) {
                    Utils.MessageBox.show("成功", "方案已导入！")
                    refreshSchemeList()
                } else {
                    Utils.MessageBox.show("错误", "导入方案失败！")
                }
            })
        })

        dialog.open()
    }

    // 保存当前配置为方案
    function saveCurrentAsScheme() {
        var dialog = NewSchemeDialog.createObject(root)
        dialog.onAccepted.connect(function(name, description) {
            createScheme(name, description)
            dialog.destroy()
        })
        dialog.onRejected.connect(function() {
            dialog.destroy()
        })
        dialog.open()
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
                text: "方案管理"
                font.pixelSize: 20
                font.bold: true
                color: "#333"
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "保存当前配置"
                onClicked: saveCurrentAsScheme()
                enabled: currentEngineNames.length > 0
            }
        }

        // 方案列表
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

                    Text {
                        text: "已保存的方案"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#333"
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "导入"
                        onClicked: importScheme()
                    }
                }

                // 列表内容
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: 8

                    ListView {
                        id: schemeListView
                        width: parent.width
                        height: parent.height
                        model: ListModel { id: schemeListModel }
                        delegate: schemeDelegate
                        spacing: 8
                        highlight: Rectangle {
                            color: "#e8f4fd"
                            radius: 6
                        }
                    }
                }

                // 操作按钮
                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: 8
                    spacing: 8

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "加载"
                        onClicked: {
                            if (schemeListView.currentIndex !== -1) {
                                loadScheme(schemeListView.currentItem.name)
                            }
                        }
                        enabled: schemeListView.currentIndex !== -1
                    }

                    Button {
                        text: "导出"
                        onClicked: {
                            if (schemeListView.currentIndex !== -1) {
                                exportScheme(schemeListView.currentItem.name)
                            }
                        }
                        enabled: schemeListView.currentIndex !== -1
                    }

                    Button {
                        text: "删除"
                        onClicked: {
                            if (schemeListView.currentIndex !== -1) {
                                deleteScheme(schemeListView.currentItem.name)
                            }
                        }
                        enabled: schemeListView.currentIndex !== -1
                    }
                }
            }
        }
    }

    // 方案项委托
    Component {
        id: schemeDelegate

        Rectangle {
            width: parent.width
            height: 50
            color: "#f8f9fa"
            radius: 6
            border.color: "#dee2e6"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: name
                    font.pixelSize: 14
                    color: "#333"
                    Layout.fillWidth: true
                    verticalAlignment: Text.AlignVCenter
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    schemeListView.currentIndex = index
                }
            }
        }
    }

    // 新建方案对话框
    Component {
        id: NewSchemeDialog

        Dialog {
            id: dialog
            title: "新建方案"
            width: 400
            height: 200
            modality: Qt.WindowModal

            property string schemeName: ""
            property string schemeDescription: ""

            signal accepted(string name, string description)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "方案名称"
                        font.pixelSize: 13
                        color: "#333"
                    }

                    TextField {
                        id: nameField
                        Layout.fillWidth: true
                        text: dialog.schemeName
                        placeholderText: "请输入方案名称"
                        onTextChanged: dialog.schemeName = text
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "方案描述（可选）"
                        font.pixelSize: 13
                        color: "#333"
                    }

                    TextField {
                        id: descField
                        Layout.fillWidth: true
                        text: dialog.schemeDescription
                        placeholderText: "请输入方案描述"
                        onTextChanged: dialog.schemeDescription = text
                    }
                }
            }

            standardButtons: Dialog.Ok | Dialog.Cancel

            onAccepted: {
                if (dialog.schemeName.trim()) {
                    accepted(dialog.schemeName.trim(), dialog.schemeDescription.trim())
                } else {
                    Utils.MessageBox.show("错误", "方案名称不能为空！")
                }
            }
        }
    }
}