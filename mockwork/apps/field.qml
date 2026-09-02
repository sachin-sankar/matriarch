import QtQuick
import QtQuick.Controls.Material
import QtQuick.Controls
ApplicationWindow {

    Material.theme: Material.Dark
    Material.accent: "#6c8cff"
    color: "#0f1117"
    width: 400
    height: 300
    visible: true
    title: "Simple Input App"

    Column {
        anchors.centerIn: parent
        spacing: 20

        Label {
            text: "Enter some text:"
            anchors.horizontalCenter: parent.horizontalCenter
        }

        TextField {
            id: mainInput
            objectName: "mainInput"
            placeholderText: "Type here..."
            width: 200
        }
    }
}
