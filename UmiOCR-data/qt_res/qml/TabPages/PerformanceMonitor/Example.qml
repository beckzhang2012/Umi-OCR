import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// 性能监控页面使用示例
// 这个文件展示了如何在应用中集成PerformanceMonitor页面

ApplicationWindow {
    visible: true
    width: 1200
    height: 800
    title: qsTr("Umi-OCR 性能监控示例")
    
    // 主布局
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        
        // 顶部导航栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#2196F3"
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 20
                
                Text_ {
                    text: qsTr("Umi-OCR")
                    fontSize: 20
                    fontWeight: Font.Bold
                    color: "#FFFFFF"
                }
                
                Text_ {
                    text: qsTr("性能监控示例")
                    fontSize: 16
                    color: "#FFFFFF"
                }
            }
        }
        
        // 页面内容区域
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#F5F5F5"
            
            // 加载PerformanceMonitor页面
            Loader {
                anchors.fill: parent
                source: "PerformanceMonitor.qml"
            }
        }
    }
}

// 自定义文本组件
Component {
    id: textComponent
    
    Text {
        property int fontSize: 14
        property color color: "#333333"
        
        font.pointSize: fontSize
        color: color
        wrapMode: Text.WordWrap
    }
}