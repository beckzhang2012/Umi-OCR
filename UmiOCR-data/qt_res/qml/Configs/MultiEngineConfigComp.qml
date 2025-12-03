// =============================================
// =============== 多引擎对比配置组件 ===============
// =============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."
import "../Widgets"
import "../Configs"

ConfigItemComp {
    property var engineList: []  // 可用引擎列表
    property var selectedEngines: []  // 已选引擎列表
    property int maxEngines: 3  // 最大引擎数量
    
    // 高度根据已选引擎数量动态调整
    height: (advanced&&!configs.advanced) ? 0 : (size_.line + size_.spacing) * (selectedEngines.length + 2)
    
    // 标题
    Text_ {
        text: qsTr("多引擎对比")
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: size_.smallSpacing
        anchors.rightMargin: size_.line
        anchors.verticalCenter: parent.verticalCenter
        clip: true
    }
    
    // 启用多引擎对比开关
    CheckBox_ {
        id: enableMultiEngine
        text: qsTr("启用多引擎对比")
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.leftMargin: size_.line
        anchors.topMargin: size_.line
        
        checked: value() || false
        
        onCheckedChanged: {
            value(checked)
            engineSelector.visible = checked
            if (!checked) {
                selectedEngines = []
            }
        }
    }
    
    // 引擎选择器容器
    Item {
        id: engineSelector
        anchors.top: enableMultiEngine.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: size_.line
        anchors.topMargin: size_.smallSpacing
        
        visible: enableMultiEngine.checked
        height: (size_.line + size_.smallSpacing) * (selectedEngines.length + 2)
        
        // 已选引擎列表
        Repeater {
            id: engineRepeater
            model: selectedEngines
            
            delegate: Row {
                width: parent.width
                height: size_.line
                
                Text_ {
                    text: modelData
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - size_.line - size_.smallSpacing
                }
                
                Button_ {
                    text: qsTr("×")
                    width: size_.line
                    height: size_.line
                    anchors.right: parent.right
                    
                    onClicked: {
                        selectedEngines.splice(index, 1)
                        engineRepeater.model = selectedEngines
                    }
                }
            }
        }
        
        // 添加引擎按钮
        Button_ {
            id: addEngineBtn
            text: qsTr("添加引擎")
            anchors.top: engineRepeater.bottom
            anchors.left: parent.left
            anchors.topMargin: size_.smallSpacing
            
            enabled: selectedEngines.length < maxEngines && engineList.length > 0
            
            onClicked: {
                enginePopup.visible = true
            }
        }
        
        // 引擎选择弹窗
        Popup {
            id: enginePopup
            modal: true
            focus: true
            visible: false
            width: parent.width
            height: Math.min(engineList.length * size_.line, 300)
            
            anchors.centerIn: parent
            
            ListView {
                id: engineListView
                anchors.fill: parent
                model: engineList
                
                delegate: ItemDelegate {
                    text: modelData
                    width: parent.width
                    
                    onClicked: {
                        if (selectedEngines.indexOf(modelData) === -1) {
                            selectedEngines.push(modelData)
                            engineRepeater.model = selectedEngines
                        }
                        enginePopup.visible = false
                    }
                }
            }
        }
        
        // 提示信息
        Text_ {
            text: qsTr("最多选择%1个引擎进行对比").arg(maxEngines)
            anchors.top: addEngineBtn.bottom
            anchors.left: parent.left
            anchors.topMargin: size_.smallSpacing
            font.pixelSize: size_.smallFont
            color: theme.textSecondary
        }
    }
    
    // 初始化引擎列表
    Component.onCompleted: {
        // 从Python获取可用引擎列表
        const engines = callPy("getAvailableEngines")
        if (engines && engines.length > 0) {
            engineList = engines
        }
        
        // 加载已保存的配置
        const savedConfig = value()
        if (savedConfig && savedConfig.selectedEngines) {
            selectedEngines = savedConfig.selectedEngines
            enableMultiEngine.checked = true
        }
    }
    
    // 重写value函数，保存多引擎配置
    function value(v=undefined) {
        if (v === undefined) {
            // 获取
            return {
                enabled: enableMultiEngine.checked,
                selectedEngines: selectedEngines
            }
        } else {
            // 设置
            if (v.enabled) {
                enableMultiEngine.checked = true
                if (v.selectedEngines) {
                    selectedEngines = v.selectedEngines
                    engineRepeater.model = selectedEngines
                }
            } else {
                enableMultiEngine.checked = false
                selectedEngines = []
            }
            configs.setValue(key, v)
        }
    }
}