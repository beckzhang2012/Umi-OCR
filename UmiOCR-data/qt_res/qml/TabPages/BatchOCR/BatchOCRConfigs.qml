// ==============================================
// =============== 批量OCR的配置项 ===============
// ==============================================

import QtQuick 2.15
import "../../Configs"

Configs {
    category_: "BatchOCR"
    signal clickIgnoreArea() // 打开忽略区域

    // 模板管理
    property var templates: []
    property string searchKeyword: ""

    // 初始化加载模板
    Component.onCompleted: {
        loadTemplates()
    }

    // 加载所有模板
    function loadTemplates() {
        templates = tabPage.callPy("get_all_templates")
    }

    // 搜索模板
    function searchTemplates() {
        if(!searchKeyword.trim()) {
            loadTemplates()
            return
        }
        const result = tabPage.callPy("search_templates", searchKeyword.trim())
        if(result.success) {
            templates = result.data
        } else {
            templates = []
        }
    }

    // 保存为模板
    function saveAsTemplate() {
        let dlg = Dialog_ {
            title: qsTr("保存为模板"),
            width: 400,
            height: 220,
            
            contentItem: Column {
                spacing: size_.spacing
                padding: size_.spacing
                
                TextField {
                    id: templateNameInput
                    width: parent.width
                    placeholderText: qsTr("模板名称")
                    focus: true
                }
                
                TextArea {
                    id: templateDescInput
                    width: parent.width
                    height: 80
                    placeholderText: qsTr("模板描述（可选）")
                }
            },
            
            btnsList: [
                {"text":qsTr("取消")},
                {
                    "text":qsTr("保存"),
                    "onClicked": function() {
                        const templateName = templateNameInput.text.trim()
                        if (!templateName) {
                            qmlapp.popup.message(qsTr("提示"), qsTr("请输入模板名称"), "warning")
                            return
                        }
                        const config = getValueDict()
                        const result = tabPage.callPy("save_template", templateName, templateDescInput.text.trim() || "", config)
                        if(result.success) {
                            qmlapp.popup.simple(qsTr("模板保存成功"), result.msg)
                            loadTemplates()
                        } else {
                            qmlapp.popup.message(qsTr("保存失败"), result.msg, "error")
                        }
                        dlg.close()
                    }
                }
            ]
        }
        dlg.open()
    }

    // 加载模板
    function loadTemplate(template) {
        // 填充所有配置项
        for(let key in template.config) {
            setValue(key, template.config[key], true)
        }
        qmlapp.popup.simple(qsTr("模板加载成功"), qsTr("已应用模板: ") + template.name)
    }

    // 删除模板
    function deleteTemplate(template) {
        qmlapp.popup.dialog(qsTr("确认删除"), qsTr("确定要删除模板 '%1' 吗?").arg(template.name), function(flag) {
            if(flag) {
                const result = tabPage.callPy("delete_template", template.id)
                if(result.success) {
                    qmlapp.popup.simple(qsTr("删除成功"), result.msg)
                    loadTemplates()
                } else {
                    qmlapp.popup.message(qsTr("删除失败"), result.msg, "error")
                }
            }
        }, "warning")
    }

    configDict: {
        // 模板管理
        "templates": {
            "title": qsTr("模板管理"),
            "type": "group",
            "enabledFold": false,
            
            "saveBtn": {
                "title": qsTr("保存为模板"),
                "btnsList": [
                    {"text":qsTr("保存模板"), "onClicked": saveAsTemplate},
                ],
            },
            
            "search": {
                "title": qsTr("搜索模板"),
                "type": "text",
                "default": "",
                "onChanged": function(val) {
                    searchKeyword = val
                    Qt.callLater(searchTemplates)
                }
            },
            
            "templateList": {
                "title": qsTr("模板列表"),
                "type": "custom",
                "component": Component {
                    Item {
                        anchors.fill: parent
                        
                        ListView {
                            id: templateListView
                            anchors.fill: parent
                            anchors.margins: size_.smallSpacing
                            model: templates
                            
                            delegate: Item {
                                width: parent.width
                                height: size_.line * 3.5
                                
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: size_.smallSpacing
                                    spacing: size_.smallSpacing
                                    
                                    Text {
                                        text: modelData.name
                                        font.bold: true
                                        color: theme.textColor
                                        elide: Text.ElideRight
                                    }
                                    
                                    Text {
                                        text: modelData.description
                                        color: theme.textSecondaryColor
                                        font.pixelSize: theme.fontSizeSmall
                                        elide: Text.ElideRight
                                        height: size_.line
                                    }
                                    
                                    Row {
                                        spacing: size_.smallSpacing
                                        
                                        Button_ {
                                            text: qsTr("加载")
                                            onClicked: loadTemplate(modelData)
                                        }
                                        
                                        Button_ {
                                            text: qsTr("删除")
                                            color: "#ff6b6b"
                                            onClicked: deleteTemplate(modelData)
                                        }
                                    }
                                }
                                
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    height: 1
                                    color: theme.borderColor
                                }
                            }
                            
                            ScrollBar.vertical: ScrollBar {}
                            
                            header: Item {
                                height: size_.line
                                visible: templates.length === 0
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: qsTr("暂无模板，请先创建")
                                    color: theme.textSecondaryColor
                                }
                            }
                        }
                    }
                }
            }
        },
        
        // OCR参数
        "ocr": qmlapp.globalConfigs.ocrManager.deploy(this, "ocr"), 

        // 后处理
        "tbpu": {
            "title": qsTr("OCR文本后处理"),
            "type": "group",

            "parser": qmlapp.globalConfigs.utilsDicts.getTbpuParser(),
            "btns": {
                "title": qsTr("忽略区域"),
                "btnsList": [
                    {"text":qsTr("进入设置"), "onClicked": clickIgnoreArea},
                ],
            },
            "ignoreArea": {
                "type": "var",
                "save": false,
            },
        },

        // 任务参数
        "mission": {
            "title": qsTr("批量任务"),
            "type": "group",

            "recurrence": {
                "title": qsTr("递归读取子文件夹"),
                "toolTip": qsTr("导入文件夹时，导入子文件夹中全部图片"),
                "default": false,
            },
            "dirType": {
                "title": qsTr("保存到"),
                "optionsList": [
                    ["source", qsTr("图片原目录")],
                    ["specify", qsTr("指定目录")],
                ],
            },
            "dir": {
                "title": qsTr("指定目录"),
                "toolTip": qsTr("必须先指定“保存到指定目录”才生效"),
                "type": "file",
                "selectExisting": true, // 选择现有
                "selectFolder": true, // 选择文件夹
                "dialogTitle": qsTr("OCR结果保存目录"),
            },
            "fileNameFormat": {
                "title": qsTr("文件名格式"),
                "toolTip": qsTr("无需填写拓展名。支持插入以下占位符：\n%date 日期时间\n%name 原文件夹名/文件名\n举例：[OCR]_%name_%date\n生成：[OCR]_我的图片_2023-09-01_12-13.txt\n添加占位符可以避免旧文件被新文件覆盖。"),
                "default": "[OCR]_%name_%date",
                "advanced": true, // 高级选项
            },
            "datetimeFormat": {
                "title": qsTr("日期时间格式"),
                "toolTip": qsTr("文件名中 %date 的日期格式。支持插入以下占位符：\n%Y 年、 %m 月、 %d 日、 %H 小时、 \n%M 分钟、 %S 秒 、 %unix 时间戳 \n举例：%Y年%m月%d日_%H-%M\n生成：2023年09月01日_12-13.txt"),
                "default": "%Y%m%d_%H%M",
                "advanced": true, // 高级选项
            },

            "filesType": {
                "title": qsTr("保存文件类型"),
                "type": "group",
                "enabledFold": true,
                "fold": false,

                "txt": {
                    "title": qsTr("txt 标准格式"),
                    "toolTip": qsTr("含原图片文件名和识别文字"),
                    "default": true,
                },
                "txtPlain": {
                    "title": qsTr("p.txt 纯文字格式"),
                    "toolTip": qsTr("仅输出识别文字，不含图片标题"),
                    "default": false,
                },
                "txtIndividual": {
                    "title": qsTr("txt 单独文件"),
                    "toolTip": qsTr("对每张图片，生成同名txt文件，仅输出识别文字"),
                    "default": false,
                },
                "md": {
                    "title": qsTr("md 图文混排"),
                    "toolTip": qsTr("Markdown图文混排格式，可用Markdown阅读器浏览文件"),
                    "default": false,
                },
                "csv": {
                    "title": qsTr("csv 表格文件(Excel)"),
                    "toolTip": qsTr("将图片信息和识别内容写入csv表格文件。可用Excel打开，另存为xlsx格式。"),
                    "default": false,
                },
                "jsonl": {
                    "title": qsTr("jsonl 原始信息"),
                    "toolTip": qsTr("每行为一条json数据，便于第三方程序读取操作"),
                    "default": false,
                },
            },

            "ignoreBlank": {
                "title": qsTr("输出忽略空白图片"),
                "toolTip": qsTr("若图片没有文字或识别失败，也不会输出错误提示信息"),
                "default": true,
            },
        },

        // 任务完成后续操作
        "postTaskActions": qmlapp.globalConfigs.utilsDicts.getPostTaskActions(),

        "other": {
            "title": qsTr("其它"),
            "type": "group",

            "simpleNotificationType": qmlapp.globalConfigs.utilsDicts.getSimpleNotificationType()
        },
    }
}


/*
输出文件类型
    .txt 标准格式
    .txt 纯文本格式
    .txt 多个独立文件
    .jsonl 原始信息
*/