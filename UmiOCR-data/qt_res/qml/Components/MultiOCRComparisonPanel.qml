import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import QtQuick.Controls.Material 2.15

Item {
    id: multiOCRPanel
    width: 800
    height: 600

    property var pythonBridge: null
    property bool isMultiEngineMode: false
    property var selectedEngines: []
    property var availableEngines: []
    property var comparisonProfiles: []
    property string selectedProfile: ""
    property string comparisonStrategy: "confidence"
    property var currentComparisonResult: null
    property int currentClusterIndex: 0

    signal engineSelectionChanged(var engines)
    signal profileSelected(string profileName)
    signal strategyChanged(string strategy)
    signal compareResultsRequested()
    signal exportReportRequested(string format)
    signal closePanelRequested()

    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // 标题栏
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: "多引擎OCR对比"
                font.pixelSize: 18
                font.bold: true
            }

            Spacer {
                Layout.fillWidth: true
            }

            Button {
                text: "关闭"
                onClicked: closePanelRequested()
            }
        }

        // 模式切换
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: "多引擎模式:"
            }

            Switch {
                id: multiEngineSwitch
                checked: isMultiEngineMode
                onCheckedChanged: {
                    isMultiEngineMode = checked
                    pythonBridge.setMultiEngineMode(checked)
                }
            }

            Spacer {
                Layout.fillWidth: true
            }

            Button {
                text: "方案管理"
                onClicked: profileManagerDialog.open()
            }
        }

        // 方案选择
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            visible: isMultiEngineMode

            Label {
                text: "选择方案:"
            }

            ComboBox {
                id: profileComboBox
                Layout.fillWidth: true
                model: comparisonProfiles
                textRole: "name"
                currentIndex: comparisonProfiles.findIndex(function(profile) {
                    return profile.name === selectedProfile
                })
                onCurrentIndexChanged: {
                    if (currentIndex >= 0) {
                        selectedProfile = comparisonProfiles[currentIndex].name
                        profileSelected(selectedProfile)
                    }
                }
            }

            Button {
                text: "刷新"
                onClicked: pythonBridge.refreshProfiles()
            }
        }

        // 引擎选择
        Item {
            Layout.fillWidth: true
            height: engineSelectionColumn.height
            visible: isMultiEngineMode

            ColumnLayout {
                id: engineSelectionColumn
                Layout.fillWidth: true
                spacing: 5

                Label {
                    text: "选择引擎 (最多3个):"
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 5

                    Repeater {
                        model: availableEngines

                        Item {
                            width: engineButton.width
                            height: engineButton.height

                            Button {
                                id: engineButton
                                text: modelData.name
                                checkable: true
                                checked: selectedEngines.some(function(engine) {
                                    return engine.key === modelData.key
                                })
                                onClicked: {
                                    if (checked) {
                                        // 最多选择3个引擎
                                        if (selectedEngines.length < 3) {
                                            selectedEngines.push(modelData)
                                        } else {
                                            checked = false
                                            pythonBridge.showMessage("最多只能选择3个引擎进行对比")
                                        }
                                    } else {
                                        selectedEngines = selectedEngines.filter(function(engine) {
                                            return engine.key !== modelData.key
                                        })
                                    }
                                    engineSelectionChanged(selectedEngines)
                                }
                            }
                        }
                    }
                }

                Label {
                    text: "已选择 " + selectedEngines.length + "/3 个引擎"
                    font.pixelSize: 12
                    color: "#666"
                }
            }
        }

        // 策略选择
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            visible: isMultiEngineMode

            Label {
                text: "合并策略:"
            }

            ComboBox {
                id: strategyComboBox
                Layout.fillWidth: true
                model: [
                    { text: "置信度优先", value: "confidence" },
                    { text: "投票选择", value: "vote" },
                    { text: "结果合并", value: "merge" }
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: model.findIndex(function(item) {
                    return item.value === comparisonStrategy
                })
                onCurrentIndexChanged: {
                    if (currentIndex >= 0) {
                        comparisonStrategy = model[currentIndex].value
                        strategyChanged(comparisonStrategy)
                    }
                }
            }

            Button {
                text: "开始对比"
                enabled: selectedEngines.length >= 2
                onClicked: compareResultsRequested()
            }
        }

        // 对比结果展示
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentComparisonResult !== null && isMultiEngineMode

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                // 统计信息
                Rectangle {
                    Layout.fillWidth: true
                    height: 80
                    color: "#f5f5f5"
                    border.color: "#ddd"
                    border.width: 1
                    radius: 5

                    GridLayout {
                        anchors.fill: parent
                        columns: 4
                        rows: 2
                        spacing: 10
                        padding: 10

                        Label {
                            text: "总聚类数:"
                            font.bold: true
                        }
                        Label {
                            text: currentComparisonResult.data.statistics.total_clusters
                        }
                        Label {
                            text: "差异聚类数:"
                            font.bold: true
                        }
                        Label {
                            text: currentComparisonResult.data.statistics.clusters_with_differences
                            color: currentComparisonResult.data.statistics.clusters_with_differences > 0 ? "#dc3545" : "#28a745"
                        }
                        Label {
                            text: "差异率:"
                            font.bold: true
                        }
                        Label {
                            text: (currentComparisonResult.data.statistics.difference_rate * 100).toFixed(1) + "%"
                        }
                        Label {
                            text: "平均置信度:"
                            font.bold: true
                        }
                        Label {
                            text: currentComparisonResult.data.statistics.engine_confidences ? 
                                Object.values(currentComparisonResult.data.statistics.engine_confidences).reduce((a, b) => a + b, 0) / 
                                Object.values(currentComparisonResult.data.statistics.engine_confidences).length : "0.0"
                        }
                    }
                }

                // 聚类导航
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        text: "上一个"
                        enabled: currentClusterIndex > 0
                        onClicked: {
                            if (currentClusterIndex > 0) {
                                currentClusterIndex--
                            }
                        }
                    }

                    Label {
                        text: "聚类 " + (currentClusterIndex + 1) + " / " + currentComparisonResult.data.clusters.length
                    }

                    Button {
                        text: "下一个"
                        enabled: currentClusterIndex < currentComparisonResult.data.clusters.length - 1
                        onClicked: {
                            if (currentClusterIndex < currentComparisonResult.data.clusters.length - 1) {
                                currentClusterIndex++
                            }
                        }
                    }

                    Spacer {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "导出报告"
                        onClicked: exportReportDialog.open()
                    }
                }

                // 聚类详情
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#ffffff"
                    border.color: "#ddd"
                    border.width: 1
                    radius: 5

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        padding: 10

                        Item {
                            Layout.fillWidth: true
                            height: 40

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Label {
                                    text: "差异类型:"
                                    font.bold: true
                                }
                                Label {
                                    text: currentCluster.difference_type
                                    color: currentCluster.has_difference ? "#dc3545" : "#28a745"
                                }

                                Spacer {
                                    Layout.fillWidth: true
                                }

                                Label {
                                    text: "参考文本:"
                                    font.bold: true
                                }
                                Label {
                                    text: currentCluster.reference_text
                                    color: "#007bff"
                                }
                            }
                        }

                        // 引擎结果对比
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            GridLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                columns: selectedEngines.length
                                spacing: 5

                                Repeater {
                                    model: selectedEngines

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 5

                                        Label {
                                            text: modelData.name
                                            font.bold: true
                                            horizontalAlignment: Text.AlignHCenter
                                            color: "#4CAF50"
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            color: "#f9f9f9"
                                            border.color: "#ddd"
                                            border.width: 1
                                            radius: 3

                                            TextArea {
                                                anchors.fill: parent
                                                readOnly: true
                                                text: getEngineResult(modelData.key)
                                                wrapMode: TextArea.Wrap
                                                font.family: "等宽字体"
                                                font.pixelSize: 12
                                                padding: 5
                                                background: Rectangle { color: "transparent" }
                                            }
                                        }

                                        Label {
                                            text: "置信度: " + getEngineConfidence(modelData.key)
                                            font.pixelSize: 11
                                            color: "#666"
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                    }
                                }
                            }
                        }

                        // 差异详情
                        Item {
                            Layout.fillWidth: true
                            height: 60
                            visible: currentCluster.has_difference

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 5

                                Label {
                                    text: "差异详情:"
                                    font.bold: true
                                    color: "#dc3545"
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 5

                                    Repeater {
                                        model: currentCluster.unique_texts

                                        Rectangle {
                                            height: 20
                                            color: "#fff3cd"
                                            border.color: "#ffc107"
                                            border.width: 1
                                            radius: 3

                                            Label {
                                                anchors.centerIn: parent
                                                text: modelData
                                                font.pixelSize: 11
                                                padding: 3
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

        // 空状态提示
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentComparisonResult === null && isMultiEngineMode

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 10

                Label {
                    text: "暂无对比结果"
                    font.pixelSize: 16
                    color: "#666"
                }

                Label {
                    text: "选择至少2个引擎并点击\"开始对比\""
                    font.pixelSize: 12
                    color: "#999"
                }
            }
        }

        // 单引擎模式提示
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !isMultiEngineMode

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 10

                Label {
                    text: "单引擎模式"
                    font.pixelSize: 16
                    color: "#666"
                }

                Label {
                    text: "开启多引擎模式以进行OCR结果对比"
                    font.pixelSize: 12
                    color: "#999"
                }
            }
        }
    }

    // 当前聚类数据
    property var currentCluster: currentComparisonResult !== null && 
        currentComparisonResult.data.clusters.length > 0 ? 
        currentComparisonResult.data.clusters[currentClusterIndex] : null

    function getEngineResult(engineKey) {
        if (!currentCluster || !currentCluster.blocks_by_engine[engineKey]) {
            return "[未识别]";
        }
        
        const blocks = currentCluster.blocks_by_engine[engineKey];
        if (blocks.length === 0) {
            return "[未识别]";
        }
        
        return blocks[0].text;
    }

    function getEngineConfidence(engineKey) {
        if (!currentCluster || !currentCluster.blocks_by_engine[engineKey]) {
            return "0.00";
        }
        
        const blocks = currentCluster.blocks_by_engine[engineKey];
        if (blocks.length === 0) {
            return "0.00";
        }
        
        return blocks[0].score.toFixed(2);
    }

    // 方案管理对话框
    Dialog {
        id: profileManagerDialog
        title: "多引擎方案管理"
        width: 600
        height: 400
        modal: true
        visible: false

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            // 方案列表
            ListView {
                id: profileListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: comparisonProfiles

                delegate: Rectangle {
                    width: parent.width
                    height: 60
                    color: ListView.isCurrentItem ? "#e3f2fd" : "#ffffff"
                    border.color: "#ddd"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        padding: 10
                        spacing: 5

                        Label {
                            text: modelData.name
                            font.bold: true
                        }
                        Label {
                            text: modelData.description
                            font.pixelSize: 11
                            color: "#666"
                        }
                        RowLayout {
                            spacing: 5

                            Label {
                                text: "引擎数: " + modelData.engine_count
                                font.pixelSize: 10
                                color: "#999"
                            }
                            Label {
                                text: "策略: " + modelData.strategy
                                font.pixelSize: 10
                                color: "#999"
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            profileListView.currentIndex = index
                        }
                    }
                }
            }

            // 方案操作按钮
            RowLayout {
                Layout.fillWidth: true
                spacing: 5

                Button {
                    text: "新建"
                    onClicked: createProfileDialog.open()
                }
                Button {
                    text: "编辑"
                    enabled: profileListView.currentIndex >= 0
                    onClicked: {
                        if (profileListView.currentIndex >= 0) {
                            editProfileDialog.profile = comparisonProfiles[profileListView.currentIndex]
                            editProfileDialog.open()
                        }
                    }
                }
                Button {
                    text: "删除"
                    enabled: profileListView.currentIndex >= 0
                    onClicked: {
                        if (profileListView.currentIndex >= 0) {
                            const profileName = comparisonProfiles[profileListView.currentIndex].name
                            pythonBridge.deleteProfile(profileName)
                        }
                    }
                }
                Button {
                    text: "复制"
                    enabled: profileListView.currentIndex >= 0
                    onClicked: {
                        if (profileListView.currentIndex >= 0) {
                            const profileName = comparisonProfiles[profileListView.currentIndex].name
                            duplicateProfileDialog.originalName = profileName
                            duplicateProfileDialog.open()
                        }
                    }
                }
                Button {
                    text: "导出"
                    enabled: profileListView.currentIndex >= 0
                    onClicked: {
                        if (profileListView.currentIndex >= 0) {
                            const profileName = comparisonProfiles[profileListView.currentIndex].name
                            pythonBridge.exportProfile(profileName)
                        }
                    }
                }
                Button {
                    text: "导入"
                    onClicked: pythonBridge.importProfile()
                }
            }
        }
    }

    // 新建方案对话框
    Dialog {
        id: createProfileDialog
        title: "新建多引擎方案"
        width: 400
        height: 300
        modal: true
        visible: false

        ColumnLayout {
            spacing: 10
            padding: 10

            TextField {
                id: newProfileName
                placeholderText: "方案名称"
                Layout.fillWidth: true
            }

            TextArea {
                id: newProfileDescription
                placeholderText: "方案描述"
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                wrapMode: TextArea.Wrap
            }

            RowLayout {
                spacing: 10

                Button {
                    text: "确定"
                    onClicked: {
                        if (newProfileName.text.trim()) {
                            pythonBridge.createProfile({
                                name: newProfileName.text.trim(),
                                description: newProfileDescription.text.trim()
                            })
                            createProfileDialog.close()
                            newProfileName.text = ""
                            newProfileDescription.text = ""
                        }
                    }
                }

                Button {
                    text: "取消"
                    onClicked: {
                        createProfileDialog.close()
                        newProfileName.text = ""
                        newProfileDescription.text = ""
                    }
                }
            }
        }
    }

    // 编辑方案对话框
    Dialog {
        id: editProfileDialog
        title: "编辑多引擎方案"
        width: 500
        height: 400
        modal: true
        visible: false
        property var profile: null

        ColumnLayout {
            spacing: 10
            padding: 10

            TextField {
                id: editProfileName
                text: profile ? profile.name : ""
                Layout.fillWidth: true
            }

            TextArea {
                id: editProfileDescription
                text: profile ? profile.description : ""
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                wrapMode: TextArea.Wrap
            }

            Label {
                text: "选择引擎:"
                font.bold: true
            }

            Flow {
                Layout.fillWidth: true
                spacing: 5

                Repeater {
                    model: availableEngines

                    Item {
                        width: editEngineButton.width
                        height: editEngineButton.height

                        Button {
                            id: editEngineButton
                            text: modelData.name
                            checkable: true
                            checked: profile && profile.engines.some(function(engine) {
                                return engine.key === modelData.key
                            })
                            onClicked: {
                                // 这里需要处理引擎选择的逻辑
                                pythonBridge.updateProfileEngines(profile.name, modelData.key, checked)
                            }
                        }
                    }
                }
            }

            Label {
                text: "合并策略:"
                font.bold: true
            }

            ComboBox {
                id: editStrategyComboBox
                Layout.fillWidth: true
                model: [
                    { text: "置信度优先", value: "confidence" },
                    { text: "投票选择", value: "vote" },
                    { text: "结果合并", value: "merge" }
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: model.findIndex(function(item) {
                    return item.value === (profile ? profile.strategy : "confidence")
                })
            }

            RowLayout {
                spacing: 10

                Button {
                    text: "确定"
                    onClicked: {
                        if (editProfileName.text.trim() && profile) {
                            pythonBridge.updateProfile({
                                name: profile.name,
                                newName: editProfileName.text.trim(),
                                description: editProfileDescription.text.trim(),
                                strategy: editStrategyComboBox.currentValue
                            })
                            editProfileDialog.close()
                        }
                    }
                }

                Button {
                    text: "取消"
                    onClicked: editProfileDialog.close()
                }
            }
        }
    }

    // 复制方案对话框
    Dialog {
        id: duplicateProfileDialog
        title: "复制多引擎方案"
        width: 400
        height: 200
        modal: true
        visible: false
        property string originalName: ""

        ColumnLayout {
            spacing: 10
            padding: 10

            Label {
                text: "新方案名称:"
            }

            TextField {
                id: duplicateProfileName
                placeholderText: "输入新方案名称"
                Layout.fillWidth: true
            }

            Label {
                text: "新方案描述:"
            }

            TextField {
                id: duplicateProfileDescription
                placeholderText: "输入新方案描述（可选）"
                Layout.fillWidth: true
            }

            RowLayout {
                spacing: 10

                Button {
                    text: "确定"
                    onClicked: {
                        if (duplicateProfileName.text.trim()) {
                            pythonBridge.duplicateProfile(
                                duplicateProfileDialog.originalName,
                                duplicateProfileName.text.trim(),
                                duplicateProfileDescription.text.trim()
                            )
                            duplicateProfileDialog.close()
                            duplicateProfileName.text = ""
                            duplicateProfileDescription.text = ""
                        }
                    }
                }

                Button {
                    text: "取消"
                    onClicked: {
                        duplicateProfileDialog.close()
                        duplicateProfileName.text = ""
                        duplicateProfileDescription.text = ""
                    }
                }
            }
        }
    }

    // 导出报告对话框
    Dialog {
        id: exportReportDialog
        title: "导出对比报告"
        width: 300
        height: 200
        modal: true
        visible: false

        ColumnLayout {
            spacing: 10
            padding: 10

            Label {
                text: "选择报告格式:"
            }

            ComboBox {
                id: reportFormatComboBox
                Layout.fillWidth: true
                model: [
                    { text: "JSON格式", value: "json" },
                    { text: "文本格式", value: "text" },
                    { text: "HTML格式", value: "html" }
                ]
                textRole: "text"
                valueRole: "value"
            }

            RowLayout {
                spacing: 10

                Button {
                    text: "导出"
                    onClicked: {
                        exportReportRequested(reportFormatComboBox.currentValue)
                        exportReportDialog.close()
                    }
                }

                Button {
                    text: "取消"
                    onClicked: exportReportDialog.close()
                }
            }
        }
    }
}
