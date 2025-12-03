// ==============================================
// =============== 统计项组件 ===============
// ==============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: statItem
    
    // 属性
    property string title: ""
    property string value: "0"
    property color color: "#4CAF50"
    
    // 标题
    Label {
        text: title
        font.pointSize: 12
        color: "#666666"
        Layout.alignment: Qt.AlignHCenter
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
    }
    
    // 值
    Label {
        text: value
        font.bold: true
        font.pointSize: 18
        color: statItem.color
        Layout.alignment: Qt.AlignHCenter
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
    }
}