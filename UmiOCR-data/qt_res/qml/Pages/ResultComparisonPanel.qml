// =============================================
// =============== 结果对比面板 ===============
// =============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../Widgets"
import "../Configs"

Item {
    property var engineResults: {}  // 各引擎识别结果 {engineName: {text: "", confidence: 0.0, blocks: []}}
    property string currentView: "best"  // 当前视图模式: "best"(最佳结果) | "single"(单引擎) | "compare"(对比模式)
    property string selectedEngine: ""  // 当前选中的引擎
    property var bestResult: null  // 最佳结果
    
    // 面板高度
    height: contentContainer.height + size_.line * 2
    
    // 顶部工具栏
    RowLayout {
        id: toolbar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: size_.smallSpacing
        
        // 视图模式切换
        ComboBox_ {
            id: viewModeCombo
            model: [qsTr("最佳结果"), qsTr("单引擎"), qsTr("对比模式")]
            currentIndex: 0
            
            onCurrentIndexChanged: {
                switch(currentIndex) {
                    case 0:
                        currentView = "best"
                        break
                    case 1:
                        currentView = "single"
                        break
                    case 2:
                        currentView = "compare"
                        break
                }
                updateView()
            }
        }
        
        // 引擎选择器（单引擎模式时显示）
        ComboBox_ {
            id: engineSelector
            Layout.fillWidth: true
            Layout.leftMargin: size_.smallSpacing
            visible: currentView === "single"
            
            onCurrentIndexChanged: {
                selectedEngine = currentText
                updateView()
            }
        }
        
        // 刷新按钮
        Button_ {
            text: qsTr("刷新")
            Layout.leftMargin: size_.smallSpacing
            
            onClicked: {
                updateBestResult()
                updateView()
            }
        }
    }
    
    // 内容容器
    Item {
        id: contentContainer
        anchors.top: toolbar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: size_.smallSpacing
        
        // 最佳结果视图
        Item {
            id: bestResultView
            anchors.fill: parent
            visible: currentView === "best"
            
            ColumnLayout {
                anchors.fill: parent
                
                Text_ {
                    text: qsTr("最佳结果")
                    font.bold: true
                    font.pixelSize: size_.largeFont
                }
                
                // 最佳结果文本
                TextArea_ {
                    id: bestResultText
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: size_.smallSpacing
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                }
                
                // 最佳结果信息
                Text_ {
                    id: bestResultInfo
                    Layout.fillWidth: true
                    Layout.topMargin: size_.smallSpacing
                    font.pixelSize: size_.smallFont
                    color: theme.textSecondary
                }
            }
        }
        
        // 单引擎视图
        Item {
            id: singleEngineView
            anchors.fill: parent
            visible: currentView === "single"
            
            ColumnLayout {
                anchors.fill: parent
                
                Text_ {
                    text: qsTr("%1 识别结果").arg(selectedEngine)
                    font.bold: true
                    font.pixelSize: size_.largeFont
                }
                
                // 引擎结果文本
                TextArea_ {
                    id: singleEngineText
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: size_.smallSpacing
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                }
                
                // 引擎结果信息
                Text_ {
                    id: singleEngineInfo
                    Layout.fillWidth: true
                    Layout.topMargin: size_.smallSpacing
                    font.pixelSize: size_.smallFont
                    color: theme.textSecondary
                }
            }
        }
        
        // 对比模式视图
        Item {
            id: compareView
            anchors.fill: parent
            visible: currentView === "compare"
            
            ColumnLayout {
                anchors.fill: parent
                
                Text_ {
                    text: qsTr("多引擎对比")
                    font.bold: true
                    font.pixelSize: size_.largeFont
                }
                
                // 对比表格
                TableView_ {
                    id: compareTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: size_.smallSpacing
                    
                    model: createCompareModel()
                    
                    TableViewColumn {
                        role: "blockIndex"
                        title: qsTr("序号")
                        width: 60
                    }
                    
                    // 动态创建引擎列
                    Repeater {
                        model: Object.keys(engineResults)
                        
                        delegate: TableViewColumn {
                            role: modelData
                            title: modelData
                            width: 200
                            
                            delegate: Rectangle {
                                width: 200
                                height: size_.line
                                
                                Text_ {
                                    text: model[modelData]
                                    anchors.fill: parent
                                    anchors.margins: size_.smallSpacing
                                    wrapMode: TextEdit.Wrap
                                    color: isDifferent(modelData) ? theme.error : theme.textPrimary
                                }
                            }
                        }
                    }
                    
                    // 最佳结果列
                    TableViewColumn {
                        role: "best"
                        title: qsTr("最佳")
                        width: 200
                        
                        delegate: Rectangle {
                            width: 200
                            height: size_.line
                            
                            Text_ {
                                text: model.best
                                anchors.fill: parent
                                anchors.margins: size_.smallSpacing
                                wrapMode: TextEdit.Wrap
                                color: theme.primary
                            }
                        }
                    }
                }
            }
        }
    }
    
    // 更新视图
    function updateView() {
        switch(currentView) {
            case "best":
                updateBestResultView()
                break
            case "single":
                updateSingleEngineView()
                break
            case "compare":
                updateCompareView()
                break
        }
    }
    
    // 更新最佳结果视图
    function updateBestResultView() {
        if (bestResult) {
            bestResultText.text = bestResult.text
            bestResultInfo.text = qsTr("来自: %1 | 置信度: %2%").arg(bestResult.engine).arg((bestResult.confidence * 100).toFixed(2))
        } else {
            bestResultText.text = qsTr("无结果")
            bestResultInfo.text = ""
        }
    }
    
    // 更新单引擎视图
    function updateSingleEngineView() {
        if (selectedEngine && engineResults[selectedEngine]) {
            singleEngineText.text = engineResults[selectedEngine].text
            singleEngineInfo.text = qsTr("置信度: %1%").arg((engineResults[selectedEngine].confidence * 100).toFixed(2))
        } else {
            singleEngineText.text = qsTr("无结果")
            singleEngineInfo.text = ""
        }
    }
    
    // 更新对比视图
    function updateCompareView() {
        compareTable.model = createCompareModel()
    }
    
    // 创建对比模型
    function createCompareModel() {
        const model = []
        const engines = Object.keys(engineResults)
        
        // 找出所有文本块
        const allBlocks = []
        engines.forEach(engine => {
            if (engineResults[engine].blocks) {
                engineResults[engine].blocks.forEach((block, index) => {
                    if (!allBlocks[index]) {
                        allBlocks[index] = {}
                    }
                    allBlocks[index][engine] = block.text
                })
            }
        })
        
        // 构建模型
        allBlocks.forEach((block, index) => {
            const item = {blockIndex: index + 1}
            
            // 添加各引擎结果
            engines.forEach(engine => {
                item[engine] = block[engine] || ""
            })
            
            // 计算最佳结果
            item.best = getBestBlockResult(block)
            
            model.push(item)
        })
        
        return model
    }
    
    // 判断当前块在指定引擎中是否与其他引擎不同
    function isDifferent(engineName) {
        const currentBlock = compareTable.model.get(compareTable.currentIndex)
        if (!currentBlock) return false
        
        const currentText = currentBlock[engineName]
        const engines = Object.keys(engineResults)
        
        for (let i = 0; i < engines.length; i++) {
            if (engines[i] !== engineName && currentBlock[engines[i]] !== currentText) {
                return true
            }
        }
        
        return false
    }
    
    // 获取文本块的最佳结果
    function getBestBlockResult(block) {
        const engines = Object.keys(block)
        if (engines.length === 0) return ""
        
        // 统计每个文本的出现次数
        const textCounts = {}
        engines.forEach(engine => {
            const text = block[engine]
            if (text) {
                textCounts[text] = (textCounts[text] || 0) + 1
            }
        })
        
        // 找出出现次数最多的文本
        let bestText = ""
        let maxCount = 0
        Object.keys(textCounts).forEach(text => {
            if (textCounts[text] > maxCount) {
                maxCount = textCounts[text]
                bestText = text
            }
        })
        
        return bestText
    }
    
    // 更新最佳结果
    function updateBestResult() {
        if (Object.keys(engineResults).length === 0) {
            bestResult = null
            return
        }
        
        // 找出置信度最高的结果
        let bestEngine = ""
        let maxConfidence = 0
        
        Object.keys(engineResults).forEach(engine => {
            if (engineResults[engine].confidence > maxConfidence) {
                maxConfidence = engineResults[engine].confidence
                bestEngine = engine
            }
        })
        
        bestResult = {
            text: engineResults[bestEngine].text,
            engine: bestEngine,
            confidence: maxConfidence
        }
    }
    
    // 当引擎结果变化时更新
    onEngineResultsChanged: {
        // 更新引擎选择器
        const engines = Object.keys(engineResults)
        engineSelector.model = engines
        if (engines.length > 0 && !selectedEngine) {
            selectedEngine = engines[0]
        }
        
        // 更新最佳结果
        updateBestResult()
        
        // 更新视图
        updateView()
    }
}