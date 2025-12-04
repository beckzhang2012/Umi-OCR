// ========================================
// =============== 审阅看板页 ===============
// ========================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import QtGraphicalEffects 1.15

Item {
    id: root
    property string ctrlKey: ""
    property var connector: null
    property var records: []
    property var selectedRecords: []
    property var filteredRecords: []
    property string filterStatus: "all"
    property string filterAssignee: ""
    property string searchText: ""
    property string sortBy: "created_at"
    property bool sortDescending: true

    // 状态选项
    property var statusOptions: [
        {key: "all", text: qsTr("全部")},
        {key: "未处理", text: qsTr("未处理")},
        {key: "已校对", text: qsTr("已校对")},
        {key: "待修改", text: qsTr("待修改")},
        {key: "已完成", text: qsTr("已完成")}
    ]

    // 页面初始化
    Component.onCompleted: {
        loadRecords()
    }

    // 加载记录
    function loadRecords() {
        if (connector) {
            records = connector.get_records()
            applyFilters()
        }
    }

    // 应用筛选和排序
    function applyFilters() {
        filteredRecords = records.filter(function(record) {
            // 状态筛选
            if (filterStatus !== "all" && record.status !== filterStatus) {
                return false
            }
            
            // 负责人筛选
            if (filterAssignee && record.assignee !== filterAssignee) {
                return false
            }
            
            // 文本搜索
            if (searchText) {
                const search = searchText.toLowerCase()
                const text = (record.text_summary || "").toLowerCase()
                const source = (record.source_path || "").toLowerCase()
                if (text.indexOf(search) === -1 && source.indexOf(search) === -1) {
                    return false
                }
            }
            
            return true
        })
        
        // 排序
        filteredRecords.sort(function(a, b) {
            let valA = a[sortBy] || ""
            let valB = b[sortBy] || ""
            
            if (sortBy === "confidence") {
                valA = parseFloat(valA) || 0
                valB = parseFloat(valB) || 0
            }
            
            if (valA < valB) return sortDescending ? 1 : -1
            if (valA > valB) return sortDescending ? -1 : 1
            return 0
        })
    }

    // 更新记录
    function updateRecord(recordId, updates) {
        if (connector) {
            for (let key in updates) {
                if (updates.hasOwnProperty(key)) {
                    const methodName = "update_record_" + key
                    if (connector[methodName]) {
                        connector[methodName](recordId, updates[key])
                    }
                }
            }
            loadRecords()
        }
    }

    // 删除记录
    function deleteRecord(recordId) {
        if (connector) {
            connector.delete_record(recordId)
            loadRecords()
        }
    }

    // 批量操作
    function batchUpdateStatus(status) {
        if (connector && selectedRecords.length > 0) {
            connector.batch_update_status(selectedRecords, status)
            loadRecords()
            selectedRecords = []
        }
    }

    function batchDelete() {
        if (connector && selectedRecords.length > 0) {
            connector.batch_delete(selectedRecords)
            loadRecords()
            selectedRecords = []
        }
    }

    function batchExport(format) {
        if (connector && selectedRecords.length > 0) {
            const success = connector.export_records(selectedRecords, format)
            if (success) {
                exportDialog.open()
            }
        }
    }

    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        // 标题栏
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16

            Text {
                text: qsTr("审阅看板")
                font.pixelSize: 24
                font.bold: true
                color: "#333"
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: qsTr("刷新")
                onClicked: loadRecords()
                icon.source: "qrc:/icons/refresh.png"
            }
        }

        // 筛选栏
        Rectangle {
            Layout.fillWidth: true
            color: "#f5f5f5"
            radius: 8
            padding: 16

            GridLayout {
                anchors.fill: parent
                columns: 4
                columnSpacing: 16
                rowSpacing: 12

                // 状态筛选
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("状态筛选")
                        font.bold: true
                        color: "#555"
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: statusOptions
                        textRole: "text"
                        valueRole: "key"
                        currentIndex: 0
                        onCurrentTextChanged: {
                            filterStatus = currentValue
                            applyFilters()
                        }
                    }
                }

                // 负责人筛选
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("负责人")
                        font.bold: true
                        color: "#555"
                    }

                    TextField {
                        Layout.fillWidth: true
                        placeholderText: qsTr("输入负责人姓名")
                        text: filterAssignee
                        onTextChanged: {
                            filterAssignee = text
                            applyFilters()
                        }
                    }
                }

                // 搜索框
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("搜索")
                        font.bold: true
                        color: "#555"
                    }

                    TextField {
                        Layout.fillWidth: true
                        placeholderText: qsTr("搜索文本或来源")
                        text: searchText
                        onTextChanged: {
                            searchText = text
                            applyFilters()
                        }
                        icon.source: "qrc:/icons/search.png"
                        icon.color: "#999"
                    }
                }

                // 排序选项
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("排序")
                        font.bold: true
                        color: "#555"
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: [
                            {key: "created_at", text: qsTr("识别时间")},
                            {key: "confidence", text: qsTr("置信度")},
                            {key: "source_path", text: qsTr("来源路径")}
                        ]
                        textRole: "text"
                        valueRole: "key"
                        currentIndex: 0
                        onCurrentTextChanged: {
                            sortBy = currentValue
                            applyFilters()
                        }
                    }
                }
            }
        }

        // 批量操作栏
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16
            spacing: 8

            Text {
                text: qsTr("批量操作")
                font.bold: true
                color: "#555"
            }

            Button {
                text: qsTr("标记为未处理")
                onClicked: batchUpdateStatus("未处理")
                enabled: selectedRecords.length > 0
            }

            Button {
                text: qsTr("标记为已校对")
                onClicked: batchUpdateStatus("已校对")
                enabled: selectedRecords.length > 0
            }

            Button {
                text: qsTr("标记为待修改")
                onClicked: batchUpdateStatus("待修改")
                enabled: selectedRecords.length > 0
            }

            Button {
                text: qsTr("导出Markdown")
                onClicked: batchExport("markdown")
                enabled: selectedRecords.length > 0
            }

            Button {
                text: qsTr("导出HTML")
                onClicked: batchExport("html")
                enabled: selectedRecords.length > 0
            }

            Button {
                text: qsTr("删除选中")
                onClicked: batchDelete()
                enabled: selectedRecords.length > 0
                color: "#dc3545"
                textColor: "white"
            }

            Item {
                Layout.fillWidth: true
            }

            Text {
                text: qsTr("选中 %1 项").arg(selectedRecords.length)
                color: "#666"
            }
        }

        // 记录列表
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#fff"
            radius: 8
            border.color: "#e0e0e0"
            border.width: 1

            ListView {
                anchors.fill: parent
                anchors.margins: 8
                model: filteredRecords
                delegate: RecordItem {
                    record: modelData
                    onStatusChanged: updateRecord(record.id, {status: status})
                    onTagsChanged: updateRecord(record.id, {tags: tags})
                    onAssigneeChanged: updateRecord(record.id, {assignee: assignee})
                    onNoteChanged: updateRecord(record.id, {note: note})
                    onDelete: deleteRecord(record.id)
                    onToggleSelect: {
                        if (selected) {
                            selectedRecords.push(record.id)
                        } else {
                            const index = selectedRecords.indexOf(record.id)
                            if (index !== -1) {
                                selectedRecords.splice(index, 1)
                            }
                        }
                    }
                }
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AlwaysOn
                }
            }
        }
    }

    // 导出成功对话框
    MessageDialog {
        id: exportDialog
        title: qsTr("导出成功")
        text: qsTr("报告已导出到文档目录")
        icon: MessageDialog.Information
        standardButtons: MessageDialog.Ok
    }
}

// 记录项组件
Component {
    id: RecordItem
    property var record
    property bool selected: false
    signal statusChanged(string status)
    signal tagsChanged(string tags)
    signal assigneeChanged(string assignee)
    signal noteChanged(string note)
    signal delete()
    signal toggleSelect()

    Rectangle {
        width: parent.width
        height: 120
        color: selected ? "#e3f2fd" : "#fff"
        border.color: selected ? "#2196f3" : "#f0f0f0"
        border.width: 1
        radius: 8
        margin: 8

        MouseArea {
            anchors.fill: parent
            onClicked: toggleSelect()
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            // 选择框
            CheckBox {
                checked: selected
                onCheckedChanged: toggleSelect()
            }

            // 缩略图占位
            Rectangle {
                width: 80
                height: 80
                color: "#f5f5f5"
                radius: 4

                Text {
                    anchors.centerIn: parent
                    text: "📄"
                    font.pixelSize: 32
                }
            }

            // 信息区域
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                // 来源路径
                Text {
                    Layout.fillWidth: true
                    text: record.source_path
                    font.pixelSize: 12
                    color: "#666"
                    elide: Text.ElideRight
                }

                // 文本摘要
                Text {
                    Layout.fillWidth: true
                    text: record.text_summary
                    font.pixelSize: 14
                    color: "#333"
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }

                // 底部信息栏
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // 状态
                    Rectangle {
                        color: record.status === "未处理" ? "#fff3cd" :
                               record.status === "已校对" ? "#d4edda" :
                               record.status === "待修改" ? "#f8d7da" : "#d1ecf1"
                        radius: 4
                        padding: 4

                        Text {
                            text: record.status
                            font.pixelSize: 10
                            color: record.status === "未处理" ? "#856404" :
                                   record.status === "已校对" ? "#155724" :
                                   record.status === "待修改" ? "#721c24" : "#0c5460"
                        }
                    }

                    // 置信度
                    Text {
                        text: qsTr("置信度: %1%").arg((record.confidence * 100).toFixed(0))
                        font.pixelSize: 12
                        color: "#666"
                    }

                    // 负责人
                    Text {
                        text: record.assignee ? qsTr("负责人: %1").arg(record.assignee) : ""
                        font.pixelSize: 12
                        color: "#666"
                    }

                    // 识别时间
                    Text {
                        text: record.created_at
                        font.pixelSize: 12
                        color: "#999"
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    // 操作按钮
                    Button {
                        text: qsTr("编辑")
                        onClicked: editDialog.open()
                        font.pixelSize: 12
                        padding: 6
                    }

                    Button {
                        text: qsTr("删除")
                        onClicked: delete()
                        font.pixelSize: 12
                        padding: 6
                        color: "#dc3545"
                        textColor: "white"
                    }
                }
            }
        }

        // 编辑对话框
        Dialog {
            id: editDialog
            title: qsTr("编辑记录")
            width: 500
            height: 400
            modal: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                // 状态
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("状态")
                        font.bold: true
                    }

                    ComboBox {
                        id: editStatus
                        Layout.fillWidth: true
                        model: ["未处理", "已校对", "待修改", "已完成"]
                        currentText: record.status
                    }
                }

                // 标签
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("标签 (逗号分隔)")
                        font.bold: true
                    }

                    TextField {
                        id: editTags
                        Layout.fillWidth: true
                        text: record.tags ? record.tags.join(",") : ""
                    }
                }

                // 负责人
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("负责人")
                        font.bold: true
                    }

                    TextField {
                        id: editAssignee
                        Layout.fillWidth: true
                        text: record.assignee
                    }
                }

                // 备注
                ColumnLayout {
                    Layout.fillWidth: true

                    Text {
                        text: qsTr("备注")
                        font.bold: true
                    }

                    TextArea {
                        id: editNote
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: record.note
                        wrapMode: TextEdit.WordWrap
                    }
                }

                // 按钮
                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    spacing: 8

                    Button {
                        text: qsTr("取消")
                        onClicked: editDialog.close()
                    }

                    Button {
                        text: qsTr("保存")
                        onClicked: {
                            statusChanged(editStatus.currentText)
                            tagsChanged(editTags.text)
                            assigneeChanged(editAssignee.text)
                            noteChanged(editNote.text)
                            editDialog.close()
                        }
                    }
                }
            }
        }
    }
}