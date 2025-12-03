// =======================================
// =============== 可编辑结果文本 ===============
// =======================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.3
import QtQuick.Layouts 1.15
import "../"

Item {
    id: resultRoot

    property string status_: "" // 状态， text / noText / error
    property alias textLeft: textLeft_.text
    property string textRight: ""
    property alias textMain: richText.text
    property alias activeFocus_: richText.activeFocus // 输入框焦点
    property int index_
    property bool editing: false // 编辑模式
    property var annotations: [] // 标注信息 [{start, end, type, style}]
    property var notes: [] // 备注
    property var tags: [] // 标签
    property var editHistory: [] // 编辑历史
    property var editHistoryIndex: -1 // 当前编辑位置

    // 外部函数
    property var copy: undefined // 复制选中
    property var copyAll: undefined // 复制全部
    property var selectSingle: undefined // 选中单个文本框
    property var selectAll: undefined // 所有文本框全选
    property var selectDel: undefined // 删除单个
    property var selectAllDel: undefined // 清空
    property var saveEdits: saveEditedResult // 保存编辑结果
    property var exportMarkdown: exportToMarkdown // 导出为Markdown

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
            const textPoint = richText.mapFromItem(item, mx, my)
            const textPos = richText.positionAt(textPoint.x, textPoint.y)
            return textPos
        }
    }

    // 将光标移到指定位置并激活焦点。
    function focus(pos=-1) {
        if(pos >= 0 && richText.cursorPosition !== pos) {
            richText.cursorPosition = pos
        }
        if(!richText.activeFocus) {
            richText.forceActiveFocus() // 获取焦点
        }
    }

    // 保存编辑状态
    function saveHistory() {
        if (!editing) return
        
        // 移除当前位置之后的历史记录
        editHistory = editHistory.slice(0, editHistoryIndex + 1)
        
        // 添加新的历史记录
        const historyItem = {
            text: richText.text,
            annotations: JSON.parse(JSON.stringify(annotations)),
            timestamp: Date.now()
        }
        editHistory.push(historyItem)
        editHistoryIndex = editHistory.length - 1
    }

    // 撤销
    function undo() {
        if (editHistoryIndex > 0) {
            editHistoryIndex--
            restoreHistory()
        }
    }

    // 重做
    function redo() {
        if (editHistoryIndex < editHistory.length - 1) {
            editHistoryIndex++
            restoreHistory()
        }
    }

    // 恢复历史状态
    function restoreHistory() {
        const historyItem = editHistory[editHistoryIndex]
        if (historyItem) {
            richText.text = historyItem.text
            annotations = JSON.parse(JSON.stringify(historyItem.annotations))
        }
    }

    // 添加标注
    function addAnnotation(start, end, type) {
        if (!editing || start >= end) return
        
        saveHistory()
        
        const annotation = {
            start: start,
            end: end,
            type: type,
            timestamp: Date.now()
        }
        annotations.push(annotation)
    }

    // 移除标注
    function removeAnnotation(index) {
        if (!editing || index < 0 || index >= annotations.length) return
        
        saveHistory()
        annotations.splice(index, 1)
    }

    // 添加备注
    function addNote(text) {
        if (!editing || !text) return
        
        const note = {
            text: text,
            timestamp: Date.now()
        }
        notes.push(note)
    }

    // 添加标签
    function addTag(tag) {
        if (!editing || !tag) return
        
        if (!tags.includes(tag)) {
            tags.push(tag)
        }
    }

    // 移除标签
    function removeTag(tag) {
        if (!editing) return
        
        const index = tags.indexOf(tag)
        if (index > -1) {
            tags.splice(index, 1)
        }
    }

    // 获取Markdown格式
    function getMarkdown() {
        let mdText = richText.text
        
        // 应用标注
        if (annotations.length > 0) {
            // 按start倒序排列，避免替换时影响位置
            const sortedAnnotations = [...annotations].sort((a, b) => b.start - a.start)
            
            sortedAnnotations.forEach(anno => {
                const prefix = anno.type === 'highlight' ? '**' :
                               anno.type === 'underline' ? '++' :
                               anno.type === 'strike' ? '~~' : ''
                
                const suffix = anno.type === 'highlight' ? '**' :
                               anno.type === 'underline' ? '++' :
                               anno.type === 'strike' ? '~~' : ''
                
                if (prefix && suffix) {
                    mdText = mdText.slice(0, anno.start) + prefix + 
                              mdText.slice(anno.start, anno.end) + suffix + 
                              mdText.slice(anno.end)
                }
            })
        }
        
        // 添加备注
        if (notes.length > 0) {
            mdText += '\n\n---\n\n**备注：**\n'
            notes.forEach((note, index) => {
                mdText += `${index + 1}. ${note.text}\n`
            })
        }
        
        // 添加标签
        if (tags.length > 0) {
            mdText += '\n\n**标签：** ' + tags.map(tag => `#${tag}`).join(' ')
        }
        
        return mdText
    }

    function saveEditedResult() {
            // 调用Python端保存编辑结果
            let result = {
                text: richText.text,
                annotations: annotations,
                notes: notes,
                tags: tags,
                lastModified: new Date().toISOString()
            }
            
            // 调用Python方法保存
            let success = pySideWidget.saveEditedResult(index_, richText.text, annotations, notes, tags)
            if (success) {
                console.log("编辑结果已保存")
                // 显示保存成功提示
                showMessage("保存成功", "编辑结果已保存到文件")
            } else {
                console.error("保存失败")
                showMessage("保存失败", "保存过程中发生错误")
            }
        }
    
    function exportToMarkdown() {
            // 调用Python端导出为Markdown
            let success = pySideWidget.exportToMarkdown(index_, richText.text, annotations, notes, tags)
            if (success) {
                console.log("Markdown导出成功")
                showMessage("导出成功", "已保存为Markdown文件")
            } else {
                console.error("导出失败")
                showMessage("导出失败", "导出过程中发生错误")
            }
        }
    
    function showMessage(title, message) {
            // 显示消息提示
            let msg = Qt.createQmlObject({
                type: "MessageDialog",
                properties: {
                    title: title,
                    text: message,
                    standardButtons: MessageDialog.Ok
                }
            }, parent)
            msg.open()
        }

    // 切换编辑模式
    function toggleEditing() {
        editing = !editing
        if (editing) {
            // 初始化历史记录
            editHistory = [{
                text: richText.text,
                annotations: JSON.parse(JSON.stringify(annotations)),
                timestamp: Date.now()
            }]
            editHistoryIndex = 0
        }
    }

    // 高度适应子组件
    implicitHeight: resultTop.height + (editing ? resultEditingBottom.height : resultBottom.height) + size_.smallSpacing
    height: implicitHeight
    property var onTextHeightChanged // 当文字输入导致高度改变时，调用的函数

    onHeightChanged: { // 高度改变时，通知父级
        // 必须文本框获得焦点时才触发
        if (richText.activeFocus && (typeof onTextHeightChanged === "function"))
            onTextHeightChanged()
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
            anchors.right: editBtn.left
            anchors.bottom: parent.bottom
            anchors.rightMargin: size_.spacing
            anchors.bottomMargin: size_.smallSpacing
            color: theme.subTextColor
            font.pixelSize: size_.smallText
            text: textRight + " | "
        }
        // 编辑按钮
        Text_ {
            id: editBtn
            anchors.right: copyBtn.left
            anchors.bottom: parent.bottom
            anchors.rightMargin: size_.spacing
            anchors.bottomMargin: size_.smallSpacing
            color: editing ? theme.specialTextColor : theme.primaryTextColor
            font.pixelSize: size_.smallText
            text: editing ? qsTr("完成") : qsTr("编辑")
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    toggleEditing()
                }
            }
        }
        // 复制按钮
        Text_ {
            id: copyBtn
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.bottomMargin: size_.smallSpacing
            color: theme.specialTextColor
            font.pixelSize: size_.smallText
            text: qsTr("复制")
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    copy && copy()
                }
            }
        }
    }

    // 非编辑模式下的显示
    Rectangle {
        id: resultBottom
        color: theme.bgColor
        anchors.top: resultTop.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !editing
        radius: size_.baseRadius
        height: textDisplay_.height

        Text_ {
            id: textDisplay_
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: size_.smallSpacing
            wrapMode: Text.Wrap
            text: richText.text
            color: status_==="error"? theme.noColor:theme.textColor
        }
    }

    // 编辑模式下的容器
    Rectangle {
        id: resultEditingBottom
        color: theme.bgColor
        anchors.top: resultTop.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: editing
        radius: size_.baseRadius
        height: editLayout.height

        ColumnLayout {
            id: editLayout
            anchors.fill: parent
            anchors.margins: size_.smallSpacing

            // 富文本编辑器
            TextEdit_ {
                id: richText
                Layout.fillWidth: true
                Layout.fillHeight: true
                readOnly: false
                persistentSelection: true
                color: status_==="error"? theme.noColor:theme.textColor
                onTextChanged: {
                    // 只在编辑模式下保存历史
                    if (editing) {
                        saveHistory()
                    }
                }

                // 按键事件
                Keys.onPressed: {
                    if (event.modifiers & Qt.ControlModifier) {
                        switch (event.key) {
                            case Qt.Key_Z:
                                event.accepted = true
                                undo()
                                break
                            case Qt.Key_Y:
                                event.accepted = true
                                redo()
                                break
                            case Qt.Key_S:
                                event.accepted = true
                                saveEdits && saveEdits()
                                break
                            case Qt.Key_E:
                                event.accepted = true
                                exportMarkdown && exportMarkdown()
                                break
                        }
                    }
                }
            }

            // 编辑工具栏
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: size_.smallSpacing
                visible: richText.selectionStart !== richText.selectionEnd

                RowLayout {
                    Layout.fillWidth: true

                    // 高亮按钮
                    FlatButton {
                        text: qsTr("高亮")
                        onClicked: {
                            addAnnotation(Math.min(richText.selectionStart, richText.selectionEnd), 
                                         Math.max(richText.selectionStart, richText.selectionEnd), 
                                         "highlight")
                        }
                    }

                    // 下划线按钮
                    FlatButton {
                        text: qsTr("下划线")
                        onClicked: {
                            addAnnotation(Math.min(richText.selectionStart, richText.selectionEnd), 
                                         Math.max(richText.selectionStart, richText.selectionEnd), 
                                         "underline")
                        }
                    }

                    // 删除线按钮
                    FlatButton {
                        text: qsTr("删除线")
                        onClicked: {
                            addAnnotation(Math.min(richText.selectionStart, richText.selectionEnd), 
                                         Math.max(richText.selectionStart, richText.selectionEnd), 
                                         "strike")
                        }
                    }

                    // 撤销按钮
                    FlatButton {
                        text: qsTr("撤销")
                        enabled: editHistoryIndex > 0
                        onClicked: undo()
                    }

                    // 重做按钮
                    FlatButton {
                        text: qsTr("重做")
                        enabled: editHistoryIndex < editHistory.length - 1
                        onClicked: redo()
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignRight

                    // 保存按钮
                    FlatButton {
                        text: qsTr("保存")
                        onClicked: saveEdits && saveEdits()
                    }

                    // 导出按钮
                    FlatButton {
                        text: qsTr("导出")
                        onClicked: exportMarkdown && exportMarkdown()
                    }
                }
            }

            // 标签显示
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: size_.smallSpacing
                visible: tags.length > 0

                Text_ {
                    text: qsTr("标签：")
                    color: theme.subTextColor
                    font.pixelSize: size_.smallText
                }

                Repeater {
                    model: tags
                    delegate: Text_ {
                        text: "#" + modelData
                        color: theme.primaryTextColor
                        font.pixelSize: size_.smallText
                        Layout.rightMargin: size_.smallSpacing
                        MouseArea {
                            anchors.fill: parent
                            onClicked: removeTag(modelData)
                        }
                    }
                }
            }

            // 备注显示
            ColumnLayout {
                Layout.fillWidth: true
                Layout.topMargin: size_.smallSpacing
                visible: notes.length > 0

                Text_ {
                    text: qsTr("备注：")
                    color: theme.subTextColor
                    font.pixelSize: size_.smallText
                }

                Repeater {
                    model: notes
                    delegate: Text_ {
                        text: modelData.text
                        color: theme.primaryTextColor
                        font.pixelSize: size_.smallText
                        Layout.topMargin: size_.tinySpacing
                    }
                }
            }
        }
    }
}