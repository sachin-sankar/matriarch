import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1000
    height: 800
    visible: true
    title: "MCP Mocker - Component Stress Test"

    ScrollView {
        anchors.fill: parent
        contentWidth: 1000
        contentHeight: 1200

        ColumnLayout {
            width: 900
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 20

            Label {
                text: "QML Component Library Mocker"
                font.pixelSize: 24
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            // --- Section 1: Inputs ---
            GroupBox {
                title: "Text Inputs"
                Layout.fillWidth: true
                ColumnLayout {
                    spacing: 10
                    TextField {
                        id: mockPathInput
                        placeholderText: "Enter path here..."
                        Layout.fillWidth: true
                        text: "/home/user/docs"
                    }
                    TextArea {
                        id: mockTextArea
                        placeholderText: "Multi-line input..."
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        text: "Line 1\nLine 2\nLine 3"
                    }
                }
            }

            // --- Section 2: Binary / Toggles ---
            GroupBox {
                title: "Toggles & Selection"
                Layout.fillWidth: true
                GridLayout {
                    columns: 2
                    CheckBox {
                        id: mockCheck1
                        text: "Enable Feature A"
                        checked: true
                    }
                    CheckBox {
                        id: mockCheck2
                        text: "Disable Feature B"
                        checked: false
                    }
                    Switch {
                        id: mockSwitch1
                        text: "System Mode"
                        checked: true
                    }
                    Switch {
                        id: mockSwitch2
                        text: "Debug Mode"
                        checked: false
                    }
                }
            }

            // --- Section 3: Selection & Lists ---
            GroupBox {
                title: "Selection Controls"
                Layout.fillWidth: true
                ColumnLayout {
                    spacing: 10
                    ComboBox {
                        id: mockCombo
                        model: ["Option 1", "Option 2", "Option 3"]
                        currentIndex: 1
                        Layout.fillWidth: true
                    }
                    ListView {
                        id: mockListView
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        model: ["Item A", "Item B", "Item C", "Item D"]
                        delegate: ItemDelegate {
                            text: modelData
                            width: parent.width
                        }
                    }
                }
            }

            // --- Section 4: Action Elements ---
            GroupBox {
                title: "Actions"
                Layout.fillWidth: true
                RowLayout {
                    spacing: 10
                    Button {
                        id: mockBtnSave
                        text: "Save Changes"
                        highlighted: true
                    }
                    Button {
                        id: mockBtnCancel
                        text: "Cancel"
                    }
                    Button {
                        id: mockBtnDelete
                        text: "Delete All"
                        onClicked: console.log("Delete clicked")
                    }
                }
            }

            // --- Section 5: Display Only ---
            GroupBox {
                title: "Informational"
                Layout.fillWidth: true
                ColumnLayout {
                    Label {
                        text: "Status: Active"
                        color: "green"
                    }
                    Label {
                        text: "Warning: Low Memory"
                        color: "red"
                    }
                }
            }
        }
    }
}
