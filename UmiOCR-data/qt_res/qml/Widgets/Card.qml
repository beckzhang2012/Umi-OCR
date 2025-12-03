// ==============================================
// =============== 卡片组件 ===============
// ==============================================

import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: card
    
    // 属性
    property color backgroundColor: "#ffffff"
    property color borderColor: "#e0e0e0"
    property int borderWidth: 1
    property int borderRadius: 8
    property int padding: 15
    
    // 样式
    color: backgroundColor
    border.color: borderColor
    border.width: borderWidth
    radius: borderRadius
    
    // 阴影效果
    layer.enabled: true
    layer.effect: DropShadow {
        color: "#000000"
        radius: 8
        samples: 16
        spread: 0.1
        opacity: 0.15
    }
    
    // 内容边距
    Item {
        anchors.fill: parent
        anchors.margins: padding
        
        // 转发子项
        default property alias data: contentItem.data
    }
}