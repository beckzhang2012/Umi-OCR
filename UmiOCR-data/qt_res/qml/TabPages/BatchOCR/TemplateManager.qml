// ===============================================
// =============== 模板管理器组件 ===============
// ===============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../Widgets"
import "../../Popup_"

Item {
    id: templateManager
    property var configsComp: null // 配置组件引用
    
    // 模板列表模型
    ListModel {
        id: templatesModel
    }
    
    // 当前选中的模板索引
    property int selectedTemplateIndex: -1
    
    // 搜索关键字
    property string searchKeyword: ""
    
    // 初始化加载模板列表
    Component.onCompleted: {
        loadTemplates()
    }
    
    // 加载模板列表
    function loadTemplates() {
        const result = qmlapp.tagPagesConnector.callPyFunc("listTemplates", [])
        if (result.startsWith("[Success]")) {
            const data = JSON.parse(result.substring(10))
            templatesModel.clear()
            for (let i in data) {
                templatesModel.append(data[i])
            }
        }
    }
    
    // 保存模板
    function saveTemplate() {
        // 弹出对话框输入模板名称和描述
        qmlapp.popup.inputDialog(qsTr("保存模板"), "", qsTr("模板名称"), 
            function(name) {
                if (name.trim() === "") return
                
                qmlapp.popup.inputDialog(qsTr("保存模板"), "", qsTr("模板描述"), 
                    function(description) {
                        // 获取当前配置
                        const configs = configsComp.getValueDict()
                        
                        // 调用Python保存模板
                        const result = qmlapp.tagPagesConnector.callPyFunc(
                            "saveTemplate", [name.trim(), description, configs]
                        )
                        
                        if (result.startsWith("[Success]")) {
                            qmlapp.popup.simple(qsTr("模板保存成功"), "")
                            loadTemplates()
                        } else {
                            qmlapp.popup.message(qsTr("保存模板失败"), result.substring(8), "error")
                        }
                    }
                )
            }
        )
    }
    
    // 加载模板
    function loadTemplate(name) {
        if (!name) return
        
        // 调用Python加载模板
        const result = qmlapp.tagPagesConnector.callPyFunc("loadTemplate", [name])
        
        if (result.startsWith("[Success]")) {
            const templateData = JSON.parse(result.substring(10))
            
            if (templateData && templateData.configs) {
                // 加载配置到界面
                for (let key in templateData.configs) {
                    configsComp.setValue(key, templateData.configs[key])
                }
                qmlapp.popup.simple(qsTr("模板加载成功"), "")
            } else {
                qmlapp.popup.message(qsTr("加载模板失败"), qsTr("模板配置数据损坏"), "error")
            }
        } else {
            qmlapp.popup.message(qsTr("加载模板失败"), result.substring(8), "error")
        }
    }
    
    // 删除模板
    function deleteTemplate(name) {
        if (!name) return
        
        // 确认对话框
        qmlapp.popup.dialog("", qsTr("确定要删除模板 '%1' 吗？").arg(name), 
            function(flag) {
                if (flag) {
                    const result = qmlapp.tagPagesConnector.callPyFunc("deleteTemplate", [name])
                    
                    if (result.startsWith("[Success]")) {
                        qmlapp.popup.simple(qsTr("模板删除成功"), "")
                        loadTemplates()
                        selectedTemplateIndex = -1
                    } else {
                        qmlapp.popup.message(qsTr("删除模板失败"), result.substring(8), "error")
                    }
                }
            }, "warning", {yesText: qsTr("删除"), noText: qsTr("取消")}
        )
    }
    
    // 重命名模板
    function renameTemplate(oldName) {
        if (!oldName) return
        
        qmlapp.popup.inputDialog(qsTr("重命名模板"), "", qsTr("新模板名称"), 
            function(newName) {
                if (newName.trim() === "" || newName === oldName) return
                
                const result = qmlapp.tagPagesConnector.callPyFunc("renameTemplate", [oldName, newName.trim()])
                
                if (result.startsWith("[Success]")) {
                    qmlapp.popup.simple(qsTr("模板重命名成功"), "")
                    loadTemplates()
                } else {
                    qmlapp.popup.message(qsTr("重命名模板失败"), result.substring(8), "error")
                }
            }
        )
    }
    
    // 搜索模板
    function filterTemplates() {
        if (searchKeyword.trim() === "") {
            // 清除过滤
            for (let i = 0; i < templatesModel.count; i++) {
                templatesModel.setProperty(i, "visible", true)
            }
            return
        }
        
        const keyword = searchKeyword.toLowerCase()
        for (let i = 0; i < templatesModel.count; i++) {
            const name = templatesModel.get(i).name.toLowerCase()
            const description = templatesModel.get(i).description.toLowerCase()
            const visible = name.includes(keyword) || description.includes(keyword)
            templatesModel.setProperty(i, "visible", visible)
        }
    }
    
    // 主布局
    Column {
        anchors.fill: parent
        spacing: size_.spacing
        
        // 顶部操作栏
        Row {
            id: toolbar
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: size_.spacing
            
            Button_ {
                text_: qsTr("保存为模板")
                onClicked: templateManager.saveTemplate()
            }
            
            Button_ {
                text_: qsTr("加载模板")
                enabled: selectedTemplateIndex !== -1
                onClicked: {
                    const selected = templatesView.currentItem
                    if (selected) {
                        loadTemplate(selected.templateName)
                    }
                }
            }
            
            Button_ {
                text_: qsTr("重命名")
                enabled: selectedTemplateIndex !== -1
                onClicked: {
                    const selected = templatesView.currentItem
                    if (selected) {
                        renameTemplate(selected.templateName)
                    }
                }
            }
            
            Button_ {
                text_: qsTr("删除")
                enabled: selectedTemplateIndex !== -1
                onClicked: {
                    const selected = templatesView.currentItem
                    if (selected) {
                        deleteTemplate(selected.templateName)
                    }
                }
            }
        }
        
        // 搜索栏
        TextField_ {
            id: searchField
            anchors.left: parent.left
            anchors.right: parent.right
            placeholderText: qsTr("搜索模板...")
            onTextChanged: {
                searchKeyword = text
                filterTemplates()
            }
        }
        
        // 模板列表
        ScrollView {
            id: templatesView
            anchors.fill: parent
            anchors.topMargin: size_.spacing
            clip: true
            
            ListView {
                model: templatesModel
                delegate: TemplateItem {
                    visible: model.visible
                    templateName: model.name
                    templateDescription: model.description
                    onSelected: {
                        selectedTemplateIndex = index
                    }
                    onDoubleClicked: {
                        loadTemplate(model.name)
                    }
                }
            }
        }
    }
}

// 模板列表项组件
Component {
    id: TemplateItem
    
    Item {
        property string templateName: ""
        property string templateDescription: ""
        
        signal selected()
        signal doubleClicked()
        
        height: size_.line * 2
        
        Rectangle {
            anchors.fill: parent
            color: hovered ? theme.subBgColor : theme.bgColor
            radius: size_.panelRadius
        }
        
        Text_ {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: size_.spacing
            anchors.topMargin: size_.smallSpacing
            text: templateName
            color: theme.textColor
            font.bold: true
        }
        
        Text_ {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: size_.spacing
            anchors.bottomMargin: size_.smallSpacing
            text: templateDescription
            color: theme.subTextColor
            font.pixelSize: size_.fontSize - 2
            elide: Text.ElideRight
        }
        
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onEntered: parent.hovered = true
            onExited: parent.hovered = false
            onClicked: {
                selected()
            }
            onDoubleClicked: {
                doubleClicked()
            }
        }
    }
}
