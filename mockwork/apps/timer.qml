import QtQuick
import QtQuick.Controls.Material
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {

    Material.theme: Material.Dark
    Material.accent: "#6c8cff"
    color: "#0f1117"
    id: root
    width: 400
    height: 500
    visible: true
    title: "Timer"
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint

    // Timer state
    property int remainingSeconds: 0
    property bool isRunning: false
    property bool isPaused: false
    // Derived: true only when the countdown is actually advancing.
    // isRunning stays true while paused, so anything that means
    // "actively counting down" must check this instead of isRunning alone.
    readonly property bool isTicking: isRunning && !isPaused

    // Core timer logic
    Timer {
        id: timer
        interval: 1000
        repeat: true
        running: root.isTicking

        onTriggered: {
            if (root.remainingSeconds > 0) {
                root.remainingSeconds--
            }
            if (root.remainingSeconds === 0) {
                root.isRunning = false
                root.isPaused = false
            }
        }
    }

    // Format seconds to MM:SS or HH:MM:SS.
    // Pure integer math, no Date/epoch involved - avoids both the
    // unit-mixing bug and timezone-dependent formatting.
    function formatTime(totalSeconds) {
        var hours = Math.floor(totalSeconds / 3600)
        var minutes = Math.floor((totalSeconds % 3600) / 60)
        var seconds = totalSeconds % 60

        function pad(n) {
            return (n < 10 ? "0" : "") + n
        }

        if (hours > 0) {
            return pad(hours) + ":" + pad(minutes) + ":" + pad(seconds)
        }
        return pad(minutes) + ":" + pad(seconds)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24

        // Timer display
        Text {
            id: display
            text: formatTime(root.remainingSeconds)
            font.pixelSize: 64
            font.bold: true
            font.family: "Monospace"
            Layout.alignment: Qt.AlignHCenter
            color: root.isTicking ? "#4ade80"
                                  : root.isPaused ? "#fbbf24"
                                  : root.remainingSeconds > 0 ? "#ffffff"
                                  : "#6b7280"
        }

        // Preset buttons row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "1m"
                Layout.fillWidth: true
                onClicked: {
                    root.remainingSeconds = 60
                    root.isRunning = false
                    root.isPaused = false
                }
            }
            Button {
                text: "5m"
                Layout.fillWidth: true
                onClicked: {
                    root.remainingSeconds = 300
                    root.isRunning = false
                    root.isPaused = false
                }
            }
            Button {
                text: "10m"
                Layout.fillWidth: true
                onClicked: {
                    root.remainingSeconds = 600
                    root.isRunning = false
                    root.isPaused = false
                }
            }
            Button {
                text: "25m"
                Layout.fillWidth: true
                onClicked: {
                    root.remainingSeconds = 1500
                    root.isRunning = false
                    root.isPaused = false
                }
            }
            Button {
                text: "60m"
                Layout.fillWidth: true
                onClicked: {
                    root.remainingSeconds = 3600
                    root.isRunning = false
                    root.isPaused = false
                }
            }
        }

        Item { Layout.fillHeight: true }

        // Control buttons
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                id: startPauseBtn
                text: root.isTicking ? "Pause"
                                     : root.isPaused ? "Resume"
                                     : "Start"
                highlighted: true
                Layout.fillWidth: true
                enabled: root.remainingSeconds > 0 || root.isPaused

                onClicked: {
                    if (root.isTicking) {
                        // Actively counting down -> pause it.
                        root.isPaused = true
                    } else if (root.isPaused) {
                        // Paused -> resume (this branch was previously
                        // unreachable, since isRunning stayed true and
                        // the check above always caught it first).
                        root.isPaused = false
                    } else {
                        // Fresh start.
                        root.isRunning = true
                        root.isPaused = false
                    }
                }
            }

            Button {
                text: "Reset"
                Layout.fillWidth: true
                // Allow resetting a paused timer too, not just a fully
                // stopped one.
                enabled: root.remainingSeconds > 0 && !root.isTicking

                onClicked: {
                    root.remainingSeconds = 0
                    root.isRunning = false
                    root.isPaused = false
                }
            }
        }
    }
}
