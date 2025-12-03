// ==========================================
// =============== 多引擎OCR接口管理 ===============
// ==========================================

import QtQuick 2.15

Item {

    // 缓存全局配置，如引擎路径、账号密钥等
    property var globalOptions: {
        "title": qsTr("多引擎文字识别"),
        "type": "group",

        "btns": {
            "title": qsTr("操作"),
            "btnsList": [
                {"text":qsTr("强制终止任务"), "onClicked": stopAllMissions, "textColorKey":"noColor"},
                {"text":qsTr("应用修改"), "onClicked": applyConfigs, "textColorKey":"yesColor"},
            ],
        },
        "engines": {
            "title": qsTr("启用的引擎"),
            "optionsList": [],
        },
    }

    // ========================= 【外部接口】 =========================

    // 应用更改，showSuccess=false时不显示成功提示
    function applyConfigs(showSuccess=true) {

        // 成功应用修改之后的刷新函数
        function successUpdate() {
            // 刷新qml各个页面的独立配置
            for (let key in deployDict) {
                const p = deployDict[key].page
                if(!p.configDict) { // 页面已经不存在了，则从记录字典中删除
                    delete deployDict[key]
                    continue
                }
                const k = deployDict[key].configKey
                p.configDict[k] = localOptions // 刷新页面设置
                p.reload() // 刷新页面UI
            }
        }

        // 验证
        if(Object.keys(localOptions).length === 0){
            const s = qsTr("没有可用的 OCR 插件。")
            qmlapp.popup.message("", s, "error")
            return
        }

        // 获取当前启用的引擎列表
        const enabledEngines = qmlapp.globalConfigs.getValue("multi_ocr.engines")
        if(!enabledEngines || enabledEngines.length === 0) {
            const s = qsTr("请至少选择一个OCR引擎。")
            qmlapp.popup.message("", s, "error")
            return
        }

        // 验证py是否有执行中的任务
        const pyStatus = qmlapp.msnConnector.callPy("multi_ocr", "getStatus", [])
        const msnLen = Object.keys(pyStatus.missionListsLength).length
        if(msnLen > 0) { // 当前执行中的任务队列数量 > 0
            let n = 0
            for(let k in pyStatus.missionListsLength)
                n += pyStatus.missionListsLength[k]
            const s = qsTr("当前已有%1组任务队列、共%2个任务正在执行。您可【强制终止任务】后修改配置。").arg(msnLen).arg(n)
            qmlapp.popup.message(qsTr("无法修改 多引擎文字识别设置"), s, "warning")
            return
        }

        // 从全局配置中，提取出目前启用引擎对应的配置项
        const allDict = qmlapp.globalConfigs.getValueDict()
        const info = {"multi_engines": enabledEngines} // 汇聚为配置信息
        
        for(let engine of enabledEngines) {
            const ocrk = "ocr." + engine
            for(let k in allDict) { // 从全局配置中，提取以该api开头的键/值
                if(k.startsWith(ocrk)) {
                    info[k] = allDict[k]
                }
            }
        }

        // 将配置信息发送给py，然后验证操作是否成功
        const msg = qmlapp.msnConnector.callPy("multi_ocr", "setEngines", [enabledEngines, info])

        // 成功，写入记录
        if(msg.startsWith("[Success]")) {
            successUpdate()
            if(showSuccess) { // 显示弹窗
                qmlapp.popup.simple(qsTr("多引擎文字识别设置应用成功"), qsTr("当前启用的引擎：%1").arg(enabledEngines.join(", ")))
            }
        }
        else {
            qmlapp.popup.message(qsTr("多引擎文字识别设置应用失败"), msg, "error")
        }
    }

    // 终止所有任务
    function stopAllMissions() {
        const pyStatus = qmlapp.msnConnector.callPy("multi_ocr", "getStatus", [])
        const msnLen = Object.keys(pyStatus.missionListsLength).length
        if(msnLen == 0) { // 无任务
            qmlapp.popup.simple(qsTr("当前没有运行中的任务"), "")
            return
        }

        let n = 0
        for(let k in pyStatus.missionListsLength)
            n += pyStatus.missionListsLength[k]
        const s = qsTr("当前已有%1组任务队列、共%2个任务正在执行。\n要强制终止全部任务吗？").arg(msnLen).arg(n)

        const argd = {yesText: qsTr("强制终止任务")}
        const callback = (flag)=>{ if(flag) qmlapp.msnConnector.callPy("multi_ocr", "stopAllMissions", []) }
        qmlapp.popup.dialog("", s, callback, "warning", argd)
    }

    // 部署进一个Configs的配置项里，可动态改变配置页。
    // 传入configs页引用和所在字典键（只能在最外层）
    function deploy(page, configKey) {
        // 记录已部署页面
        const pageId = page.toString()
        deployDict[pageId] = { 
            "page": page,
            "configKey": configKey,
        }
        // 返回初始配置字典
        return localOptions
    }

    // 初始化1：传入python ocr信息，整理信息，返回全局配置字典
    function init1(options) {
        localOptions = {
            "title": qsTr("多引擎文字识别"),
            "type": "group",
        }
        
        // 收集所有可用引擎
        const allEngines = []
        for (var key in options) {
            allEngines.push([key, options[key].global_options ? options[key].global_options.title : key])
        }
        
        globalOptions.engines.optionsList = allEngines
        qmlapp.globalConfigs.configDict.multi_ocr = globalOptions // 写入全局预配置
    }
    
    // 初始化2：应用更改
    function init2() {
        applyConfigs(false)
        console.log("MultiOcrManager 初始化多引擎OCR管理器完毕！")
    }

    // ========================= 【内部】 =========================
    property var deployDict: {} // 存放 部署了配置的页面
    property var localOptions: {} // 缓存局部配置

    Component.onCompleted: {
        deployDict = {}
    }
}
