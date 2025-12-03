// =======================================
// =============== 结果文本 ===============
// =======================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

// 标注类型枚举
property string ANNOTATION_HIGHLIGHT: "highlight"
property string ANNOTATION_UNDERLINE: "underline"
property string ANNOTATION_STRIKETHROUGH: "strikethrough"

Item {
    id: resultRoot

    property string status_: "" // 状态， text / noText / error
    property alias textLeft: textLeft_.text
    property string textRight: ""
    property alias textMain: textMain_.text
    property alias activeFocus_: textMain_.activeFocus // 输入框焦点
    property int index_
    property bool isEditMode: false // 是否处于编辑模式
    property var annotations: [] // 标注列表
    property string note: "" // 备注
    property var tags: [] // 标签列表

    // 编辑工具栏的可见性
    property bool showEditToolbar: isEditMode && textMain_.activeFocus

    // 当前选中的文本范围
    property int currentSelectionStart: -1
    property int currentSelectionEnd: -1
    // 选取文字
    property int selectL: -1
    property int selectR: -1
    property int selectUpdate: 0 // 只要有变化，就刷新选中
    // 外部函数
    property var copy: undefined // 复制选中
    property var copyAll: undefined // 复制全部
    property var selectSingle: undefined // 选中单个文本框
    property var selectAll: undefined // 所有文本框全选
    property var selectDel: undefined // 删除单个
    property var selectAllDel: undefined // 清空
    // 编辑相关的外部函数
    property var editText: undefined // 编辑文字
    property var addAnnotation: undefined // 添加标注
    property var deleteAnnotation: undefined // 删除标注
    property var addNote: undefined // 添加备注
    property var addTag: undefined // 添加标签
    property var deleteTag: undefined // 删除标签
    property var undo: undefined // 撤销
    property var redo: undefined // 重做

    // 传入一个相对于item的坐标，返回该坐标位于this组件的什么位置。
    // undefined:不在组件中 | -1:顶部信息栏 | 0~N:所在字符的下标
    function where(item, mx, my) {
        const localPoint = this.mapFromItem(item, mx, my)
        if(!this.contains(localPoint)) {
            return undefined
        }
        if(resultTop.contains(localPoint)) {
            return -1
        }
        else {
            const textPoint = textMain_.mapFromItem(item, mx, my)
            const textPos = textMain_.positionAt(textPoint.x, textPoint.y)
            return textPos
        }
    }
    // 将光标移到指定位置并激活焦点。
    function focus(pos=-1) {
        if(pos >= 0 && textMain_.cursorPosition !== pos) {
            textMain_.cursorPosition = pos
        }
        if(!textMain_.activeFocus) {
            textMain_.forceActiveFocus() // 获取焦点
        }
    }
    // 更新选中的文本范围
    function updateCurrentSelection() {
        if (textMain_.selectedText.length > 0) {
            currentSelectionStart = textMain_.selectionStart
            currentSelectionEnd = textMain_.selectionEnd
        } else {
            currentSelectionStart = -1
            currentSelectionEnd = -1
        }
    }

    function toUpdateSelect() {
        if(selectL<0 || selectR<0)
            textMain_.deselect()
        else
            textMain_.select(selectL, selectR)
    }
    onSelectUpdateChanged: toUpdateSelect()
    TableView.onReused: toUpdateSelect()
    Component.onCompleted: toUpdateSelect()

    // 进入编辑模式
    function enterEditMode() {
        isEditMode = true
        textMain_.forceActiveFocus()
    }

    // 退出编辑模式
    function exitEditMode(saveChanges) {
        isEditMode = false
        // 这里可以添加保存更改的逻辑
    }

    // 更新标注显示
    function updateAnnotations(newAnnotations) {
        annotations = newAnnotations
        // 这里可以添加更新标注显示的逻辑
    }

    // 更新备注显示
    function updateNote(newNote) {
        note = newNote
        // 这里可以添加更新备注显示的逻辑
    }

    // 更新标签显示
    function updateTags(newTags) {
        tags = newTags
        // 这里可以添加更新标签显示的逻辑
    }
    

    // 高度适应子组件
    implicitHeight: resultTop.height + (showEditToolbar ? editToolbar.height : 0) + resultBottom.height + size_.smallSpacing
    height: resultTop.height + (showEditToolbar ? editToolbar.height : 0) + resultBottom.height + size_.smallSpacing
    property var onTextHeightChanged // 当文字输入导致高度改变时，调用的函数

    onHeightChanged: { // 高度改变时，通知父级
        // 必须文本框获得焦点时才触发
        if(textMain_.activeFocus && (typeof onTextHeightChanged === "function"))
            onTextHeightChanged()
    }

    // 编辑工具栏
    Row {
        id: editToolbar
        visible: showEditToolbar
        anchors.top: resultTop.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: size_.smallSpacing
        anchors.rightMargin: size_.smallSpacing
        height: size_.line * 1.2
        spacing: size_.smallSpacing

        // 撤销按钮
        IconButton {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: height
            icon_: "undo"
            color: theme.textColor
            toolTip: qsTr("撤销")
            onClicked: {
                if (typeof undo === "function")
                    undo()
            }
        }

        // 重做按钮
        IconButton {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: height
            icon_: "redo"
            color: theme.textColor
            toolTip: qsTr("重做")
            onClicked: {
                if (typeof redo === "function")
                    redo()
            }
        }

        Rectangle {
            height: parent.height
            width: 1
            color: theme.borderColor
        }

        // 高亮按钮
        IconButton {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: height
            icon_: "format-color-highlight"
            color: theme.textColor
            toolTip: qsTr("高亮")
            onClicked: {
                if (currentSelectionStart >= 0 && currentSelectionEnd >= 0 && typeof addAnnotation === "function") {
                    addAnnotation(ANNOTATION_HIGHLIGHT, currentSelectionStart, currentSelectionEnd, "yellow")
                }
            }
        }

        // 下划线按钮
        IconButton {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: height
            icon_: "format-text-underline"
            color: theme.textColor
            toolTip: qsTr("下划线")
            onClicked: {
                if (currentSelectionStart >= 0 && currentSelectionEnd >= 0 && typeof addAnnotation === "function") {
                    addAnnotation(ANNOTATION_UNDERLINE, currentSelectionStart, currentSelectionEnd)
                }
            }
        }

        // 删除线按钮
        IconButton {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: height
            icon_: "format-text-strikethrough"
            color: theme.textColor
            toolTip: qsTr("删除线")
            onClicked: {
                if (currentSelectionStart >= 0 && currentSelectionEnd >= 0 && typeof addAnnotation === "function") {
                    addAnnotation(ANNOTATION_STRIKETHROUGH, currentSelectionStart, currentSelectionEnd)
                }
            }
        }
    }

    // 顶部信息
    Item {
        id: resultTop
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: size_.smallSpacing
        anchors.rightMargin: size_.smallSpacing
        height: size_.smallLine + size_.spacing*2

        // 图片名称
        Text_ {
            id: textLeft_
            anchors.left: parent.left
            anchors.right: textRight_.left
            anchors.bottom: parent.bottom
            anchors.rightMargin: size_.spacing
            anchors.bottomMargin: size_.smallSpacing
            color: theme.subTextColor
            font.pixelSize: size_.smallText
            font.family: theme.dataFontFamily
            clip: true
            elide: Text.ElideLeft
        }
        // 日期时间
        Text_ {
            id: textRight_
            anchors.right: btnRight.left
            anchors.bottom: parent.bottom
            anchors.bottomMargin: size_.smallSpacing
            color: theme.subTextColor
            font.pixelSize: size_.smallText
            text: textRight + " | "
        }
        // 复制按钮
        Text_ {
            id: btnRight
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.bottomMargin: size_.smallSpacing
            color: theme.specialTextColor
            font.pixelSize: size_.smallText
            text: qsTr("复制")
        }
    }

    // 下方主要文字内容
    Rectangle {
        id: resultBottom
        color: theme.bgColor
        anchors.top: resultTop.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        // anchors.topMargin: size_.smallSpacing
        radius: size_.baseRadius
        height: textMain_.height

        TextEdit_ {
            id: textMain_
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: size_.smallSpacing
            anchors.rightMargin: size_.smallSpacing
            readOnly: false // 可编辑
            persistentSelection: true // 丢失焦点时，保留选区
            color: status_==="error"? theme.noColor:theme.textColor

            // 按键事件。响应并拦截：单双击 Ctrl+C ，双击 Ctrl+A
            property int keyDoubleTime: 300 // 双击毫秒
            property int lastUpTime: -1 // 上次按键抬起的时间戳。需要截取后8位以免int放不下
            property int lastKey: -1 // 上次按键的键值
            property var listeningKeys: [Qt.Key_A, Qt.Key_C, Qt.Key_D, Qt.Key_Z, Qt.Key_Y]
            Keys.onPressed: {
                if (event.modifiers & Qt.ControlModifier) {
                    if (listeningKeys.includes(event.key)) {
                        event.accepted = true // 拦截按键
                        const t = Date.now() & 0xFFFFFFFF
                        
                        // 撤销/重做
                        if (event.key === Qt.Key_Z) {
                            if (typeof undo === "function")
                                undo()
                        } else if (event.key === Qt.Key_Y) {
                            if (typeof redo === "function")
                                redo()
                        }
                        // 其他快捷键
                        else {
                            // 双击
                            if(t - lastUpTime <= keyDoubleTime && lastKey==event.key) {
                                event.key===Qt.Key_A && resultRoot.selectAll && resultRoot.selectAll()
                                event.key===Qt.Key_C && resultRoot.copyAll && resultRoot.copyAll()
                                event.key===Qt.Key_D && resultRoot.selectAllDel && resultRoot.selectAllDel()
                            }
                            else { // 单击
                                event.key===Qt.Key_A && resultRoot.selectSingle && resultRoot.selectSingle()
                                event.key===Qt.Key_C && resultRoot.copy && resultRoot.copy()
                            }
                        }
                    }
                }
            }
            Keys.onReleased: {
                if (listeningKeys.includes(event.key)) {
                    lastUpTime = Date.now() & 0xFFFFFFFF
                    lastKey = event.key
                }
            }

            // 当文本选择变化时，更新当前选择范围
            onSelectionStartChanged: {
                updateCurrentSelection()
            }

            onSelectionEndChanged: {
                updateCurrentSelection()
            }

            // 当文本内容变化时，通知Python进行保存
            onTextChanged: {
                if (isEditMode && typeof editText === "function") {
                    editText(text)
                }
            }
        }
    }
}