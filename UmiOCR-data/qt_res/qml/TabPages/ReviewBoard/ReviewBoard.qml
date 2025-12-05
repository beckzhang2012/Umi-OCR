import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

import "./../.." as Umi

TabPage {
    id: reviewBoardPage
    
    title: qsTr("审阅看板")
    
    // 数据源
    property var reviewItems: []
    property var filteredItems: []
    
    // 过滤和排序条件
    property var currentFilters: {
        status: "",
        assignee: "",
        tags: [],
        search: ""
    }
    
    property var currentSort: {
        key: "timestamp",
        order: "desc"
    }
    
    // 选中的项目
    property var selectedItems: []
    
    // 状态选项
    property var statusOptions: [
        { value: "", label: qsTr("全部状态") },
        { value: "未处理", label: qsTr("未处理") },
        { value: "已校对", label: qsTr("已校对") },
        { value: "待修改", label: qsTr("待修改") },
        { value: "已完成", label: qsTr("已完成") }
    ]
    
    // 标签选项
    property var tagOptions: [
        { value: "发票", label: qsTr("发票") },
        { value: "合同", label: qsTr("合同") },
        { value: "简历", label: qsTr("简历") },
        { value: "报告", label: qsTr("报告") },
        { value: "其他", label: qsTr("其他") }
    ]
    
    // 初始化
    Component.onCompleted: {
        // 从Python控制器加载数据
        loadReviewData();
    }
    
    // 加载审阅数据
    function loadReviewData() {
        var items = callPy("get_review_items");
        if (items) {
            reviewItems = items;
            applyFiltersAndSort();
        }
    }
    
    // 应用过滤和排序
    function applyFiltersAndSort() {
        var filters = {
            status: currentFilters.status,
            assignee: currentFilters.assignee,
            tags: currentFilters.tags,
            search: currentFilters.search
        };
        
        var sort = [currentSort.key, currentSort.order];
        
        filteredItems = callPy("filter_items", [filters, sort[0], sort[1]]);
    }
    
    // 更新项目
    function updateItem(itemId, updates) {
        callPy("update_item", [itemId, updates]);
        loadReviewData();
    }
    
    // 删除项目
    function deleteItem(itemId) {
        callPy("delete_item", [itemId]);
        loadReviewData();
    }
    
    // 批量更新项目
    function batchUpdateItems(itemIds, updates) {
        callPy("batch_update_items", [itemIds, updates]);
        loadReviewData();
    }
    
    // 批量删除项目
    function batchDeleteItems(itemIds) {
        callPy("batch_delete_items", [itemIds]);
        loadReviewData();
    }
    
    // 导出为Markdown
    function exportAsMarkdown() {
        var filePath = Umi.Widgets.FileDialog_.getSaveFileUrl("*.md", qsTr("Markdown文件"));
        if (filePath) {
            var success = callPy("export_markdown", [filteredItems, filePath]);
            if (success) {
                Umi.Widgets.MessageSimple.showMessage(qsTr("导出成功"), qsTr("Markdown报告已导出"));
            } else {
                Umi.Widgets.MessageSimple.showMessage(qsTr("导出失败"), qsTr("Markdown报告导出失败"));
            }
        }
    }
    
    // 导出为HTML
    function exportAsHtml() {
        var filePath = Umi.Widgets.FileDialog_.getSaveFileUrl("*.html", qsTr("HTML文件"));
        if (filePath) {
            var success = callPy("export_html", [filteredItems, filePath]);
            if (success) {
                Umi.Widgets.MessageSimple.showMessage(qsTr("导出成功"), qsTr("HTML报告已导出"));
            } else {
                Umi.Widgets.MessageSimple.showMessage(qsTr("导出失败"), qsTr("HTML报告导出失败"));
            }
        }
    }
    
    // 选择项目
    function selectItem(itemId) {
        if (selectedItems.indexOf(itemId) === -1) {
            selectedItems.push(itemId);
        } else {
            selectedItems.splice(selectedItems.indexOf(itemId), 1);
        }
    }
    
    // 全选/取消全选
    function selectAll() {
        if (selectedItems.length === filteredItems.length) {
            selectedItems = [];
        } else {
            selectedItems = filteredItems.map(function(item) { return item.id; });
        }
    }
    
    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        
        // 工具栏
        RowLayout {
            id: toolbar
            
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            
            // 筛选器
            RowLayout {
                id: filterBar
                
                spacing: 10
                
                // 状态筛选
                ComboBox {
                    id: statusFilter
                    
                    model: statusOptions
                    textRole: "label"
                    valueRole: "value"
                    
                    currentIndex: 0
                    
                    onCurrentIndexChanged: {
                        currentFilters.status = statusFilter.currentValue;
                        applyFiltersAndSort();
                    }
                }
                
                // 负责人筛选
                TextField {
                    id: assigneeFilter
                    
                    placeholderText: qsTr("负责人")
                    
                    onTextChanged: {
                        currentFilters.assignee = assigneeFilter.text;
                        applyFiltersAndSort();
                    }
                }
                
                // 标签筛选
                ComboBox {
                    id: tagFilter
                    
                    model: tagOptions
                    textRole: "label"
                    valueRole: "value"
                    
                    currentIndex: -1
                    
                    onCurrentIndexChanged: {
                        if (tagFilter.currentIndex === -1) {
                            currentFilters.tags = [];
                        } else {
                            currentFilters.tags = [tagFilter.currentValue];
                        }
                        applyFiltersAndSort();
                    }
                }
                
                // 搜索框
                TextField {
                    id: searchFilter
                    
                    placeholderText: qsTr("搜索")
                    
                    onTextChanged: {
                        currentFilters.search = searchFilter.text;
                        applyFiltersAndSort();
                    }
                }
            }
            
            // 排序器
            RowLayout {
                id: sortBar
                
                spacing: 5
                
                // 排序字段
                ComboBox {
                    id: sortField
                    
                    model: [
                        { value: "timestamp", label: qsTr("时间") },
                        { value: "confidence", label: qsTr("置信度") },
                        { value: "status", label: qsTr("状态") },
                        { value: "assignee", label: qsTr("负责人") }
                    ]
                    
                    textRole: "label"
                    valueRole: "value"
                    
                    currentIndex: 0
                    
                    onCurrentIndexChanged: {
                        currentSort.key = sortField.currentValue;
                        applyFiltersAndSort();
                    }
                }
                
                // 排序方向
                Button {
                    id: sortOrder
                    
                    text: currentSort.order === "desc" ? qsTr("降序") : qsTr("升序")
                    
                    onClicked: {
                        currentSort.order = currentSort.order === "desc" ? "asc" : "desc";
                        applyFiltersAndSort();
                    }
                }
            }
            
            // 批量操作按钮
            RowLayout {
                id: batchOperationBar
                
                spacing: 5
                
                // 全选按钮
                Button {
                    id: selectAllButton
                    
                    text: qsTr("全选")
                    
                    onClicked: {
                        selectAll();
                    }
                }
                
                // 批量标记状态按钮
                ComboBox {
                    id: batchStatus
                    
                    model: statusOptions.slice(1) // 排除"全部状态"
                    textRole: "label"
                    valueRole: "value"
                    
                    onCurrentIndexChanged: {
                        if (selectedItems.length > 0) {
                            batchUpdateItems(selectedItems, { status: batchStatus.currentValue });
                        }
                    }
                }
                
                // 批量导出按钮
                MenuButton {
                    id: batchExportButton
                    
                    text: qsTr("导出")
                    
                    menu: Menu {
                        MenuItem {
                            text: qsTr("导出为Markdown")
                            onClicked: {
                                exportAsMarkdown();
                            }
                        }
                        MenuItem {
                            text: qsTr("导出为HTML")
                            onClicked: {
                                exportAsHtml();
                            }
                        }
                    }
                }
                
                // 批量删除按钮
                Button {
                    id: batchDeleteButton
                    
                    text: qsTr("删除")
                    
                    onClicked: {
                        if (selectedItems.length > 0) {
                            Umi.Widgets.MessageBox.showConfirm(qsTr("确认删除"), qsTr("您确定要删除选中的项目吗？"), function(confirmed) {
                                if (confirmed) {
                                    batchDeleteItems(selectedItems);
                                    selectedItems = [];
                                }
                            });
                        }
                    }
                }
            }
        }
        
        // 内容区域
        ScrollView {
            id: contentScrollView
            
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            // 审阅项列表
            ListView {
                id: reviewItemListView
                
                model: filteredItems
                delegate: ReviewItemDelegate {
                    itemData: modelData
                    isSelected: selectedItems.indexOf(modelData.id) !== -1
                    
                    onSelectedChanged: {
                        selectItem(modelData.id);
                    }
                    
                    onItemUpdated: {
                        updateItem(modelData.id, arguments[0]);
                    }
                    
                    onItemDeleted: {
                        deleteItem(modelData.id);
                    }
                }
                
                spacing: 10
                
                // 空状态
                Component.onCompleted: {
                    if (filteredItems.length === 0) {
                        // 显示空状态
                    }
                }
            }
        }
    }
}

// 审阅项委托
Component {
    id: reviewItemDelegate
    
    Item {
        id: reviewItemDelegate
        
        property var itemData: {}
        property bool isSelected: false
        
        signal selectedChanged()
        signal itemUpdated(var updates)
        signal itemDeleted()
        
        width: ListView.view.width
        height: 150
        
        // 背景
        Rectangle {
            id: background
            
            anchors.fill: parent
            color: isSelected ? Umi.Themes.ThemeManager.accentColor : "#f5f5f5"
            border.color: isSelected ? Umi.Themes.ThemeManager.accentColor : "#ddd"
            border.width: 1
            radius: 5
            
            MouseArea {
                id: mouseArea
                
                anchors.fill: parent
                
                onClicked: {
                    isSelected = !isSelected;
                    selectedChanged();
                }
            }
        }
        
        // 布局
        RowLayout {
            id: itemLayout
            
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10
            
            // 缩略图
            Image {
                id: thumbnailImage
                
                source: itemData.thumbnail_path
                fillMode: Image.PreserveAspectFit
                
                Layout.preferredWidth: 100
                Layout.preferredHeight: 100
            }
            
            // 内容
            ColumnLayout {
                id: contentLayout
                
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 5
                
                // 来源和时间
                RowLayout {
                    id: sourceTimeLayout
                    
                    Layout.fillWidth: true
                    
                    // 来源
                    Text {
                        id: sourceText
                        
                        text: itemData.source_path
                        elide: Text.ElideMiddle
                        
                        Layout.fillWidth: true
                    }
                    
                    // 时间
                    Text {
                        id: timeText
                        
                        text: new Date(itemData.timestamp * 1000).toLocaleString()
                        font.pointSize: 10
                        color: "#666"
                    }
                }
                
                // 文本摘要
                Text {
                    id: summaryText
                    
                    text: itemData.text_content.substring(0, 200) + (itemData.text_content.length > 200 ? "..." : "")
                    elide: Text.ElideRight
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    
                    Layout.fillWidth: true
                    Layout.preferredHeight: 60
                }
                
                // 状态和置信度
                RowLayout {
                    id: statusConfidenceLayout
                    
                    Layout.fillWidth: true
                    
                    // 状态
                    ComboBox {
                        id: statusCombo
                        
                        model: [
                            { value: "未处理", label: qsTr("未处理") },
                            { value: "已校对", label: qsTr("已校对") },
                            { value: "待修改", label: qsTr("待修改") },
                            { value: "已完成", label: qsTr("已完成") }
                        ]
                        
                        textRole: "label"
                        valueRole: "value"
                        
                        currentIndex: model.findIndex(function(item) { return item.value === itemData.status; })
                        
                        onCurrentIndexChanged: {
                            itemUpdated({ status: statusCombo.currentValue });
                        }
                    }
                    
                    // 置信度
                    Text {
                        id: confidenceText
                        
                        text: qsTr("置信度: ") + (itemData.confidence * 100).toFixed(2) + "%"
                        font.pointSize: 10
                        color: "#666"
                    }
                }
                
                // 负责人和标签
                RowLayout {
                    id: assigneeTagsLayout
                    
                    Layout.fillWidth: true
                    
                    // 负责人
                    TextField {
                        id: assigneeField
                        
                        placeholderText: qsTr("负责人")
                        text: itemData.assignee
                        
                        Layout.preferredWidth: 150
                        
                        onEditingFinished: {
                            itemUpdated({ assignee: assigneeField.text });
                        }
                    }
                    
                    // 标签
                    ComboBox {
                        id: tagCombo
                        
                        model: [
                            { value: "发票", label: qsTr("发票") },
                            { value: "合同", label: qsTr("合同") },
                            { value: "简历", label: qsTr("简历") },
                            { value: "报告", label: qsTr("报告") },
                            { value: "其他", label: qsTr("其他") }
                        ]
                        
                        textRole: "label"
                        valueRole: "value"
                        
                        currentIndex: itemData.tags.length > 0 ? model.findIndex(function(item) { return item.value === itemData.tags[0]; }) : -1
                        
                        onCurrentIndexChanged: {
                            var tags = tagCombo.currentIndex === -1 ? [] : [tagCombo.currentValue];
                            itemUpdated({ tags: tags });
                        }
                    }
                    
                    // 删除按钮
                    Button {
                        id: deleteButton
                        
                        text: qsTr("删除")
                        font.pointSize: 10
                        
                        onClicked: {
                            Umi.Widgets.MessageBox.showConfirm(qsTr("确认删除"), qsTr("您确定要删除这个项目吗？"), function(confirmed) {
                                if (confirmed) {
                                    itemDeleted();
                                }
                            });
                        }
                    }
                }
            }
        }
    }
}