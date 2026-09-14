import QtQuick
import QtQuick.Controls.Material
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {

    Material.theme: Material.Dark
    Material.accent: "#6c8cff"
    color: "#0f1117"
    id: root
    width: 900
    height: 550
    visible: true
    title: "QML File Manager"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: "#1e1e1e"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 10

                Label {
                    text: "File Flow"
                    font.pixelSize: 18
                    font.bold: true
                    color: "white"
                }

                Button {
                    text: "My Files"
                    Layout.fillWidth: true
                }

                CheckBox {
                    id: showHiddenCheck
                    objectName: "showHiddenCheck"
                    text: "Show Hidden"
                }

                Item { Layout.fillHeight: true } // Spacer
            }
        }

        // Main Content
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#121212"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15

                TextField {
                    id: pathInput
                    objectName: "pathInput"
                    text: "~"
                    Layout.fillWidth: true
                }

                TextArea {
                    id: fileList
                    objectName: "fileList"
                    text: "Documents/\nDownloads/\nPictures/\nproject_manifest.json"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
        }
    }
}
