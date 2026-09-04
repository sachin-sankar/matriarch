import QtQuick
import QtQuick.Controls.Material
import QtQuick.Controls
import QtQuick.Layouts

// Notes / to-do app designed to be driven by the QML Inspector API agent.
//
// Inspector-visibility rules baked in:
//   - every interactive element is a Button / TextField / CheckBox
//     (the roles the /layout pruner exposes);
//   - rows are created with createObject(parent) so they are REAL QObject
//     children of the list (Repeater delegates are NOT reliably visible to
//     QObject-tree walkers - they get no QObject parent);
//   - every row labels its OWN buttons with the task text
//     ("Edit: buy milk", "Delete: buy milk") so the agent can tell rows apart;
//   - task text lives in the row CheckBox label, done state in its checked
//     value, and the totals in the pending label -> everything readable
//     through GET /layout, everything actionable through POST /interact.
ApplicationWindow {

    Material.theme: Material.Dark
    Material.accent: "#6c8cff"
    color: "#0f1117"
    id: root
    width: 540
    height: 640
    visible: true
    title: "Notes"

    property var todos: []          // [{task: string, done: bool}]
    property var rowPool: []        // live row objects - grown, never destroyed
    property int editingIndex: -1
    property int pendingCount: 0
    property int totalCount: 0      // notify-capable mirror of todos.length

    function updateCounts() {
        var p = 0
        for (var i = 0; i < root.todos.length; i++) {
            if (!root.todos[i].done) p++
        }
        root.pendingCount = p
        root.totalCount = root.todos.length
    }

    function rebuild() {
        // Update rows IN PLACE from the todos array and grow the pool as
        // needed. Rows are NEVER destroyed: a destroyed-but-not-yet-deleted
        // QML item poisons the QObject tree and segfaults anything that walks
        // it (e.g. the inspector serializing a concurrent /layout request).
        // Surplus rows are hidden and neutralized instead.
        var i
        for (i = 0; i < root.todos.length; i++) {
            var row
            if (i < root.rowPool.length) {
                row = root.rowPool[i]
            } else {
                row = rowComp.createObject(listCol)
                root.rowPool.push(row)
            }
            row.rowIndex = i
            row.taskText = root.todos[i].task
            row.isDone = root.todos[i].done
            row.alive = true
            row.visible = true
        }
        for (i = root.todos.length; i < root.rowPool.length; i++) {
            var g = root.rowPool[i]
            g.alive = false
            g.visible = false
            g.rowIndex = -1
            g.taskText = ""
            g.isDone = false
        }
        updateCounts()
    }

    function addTodo(t) {
        t = t.trim()
        if (t === "") return false
        root.todos.push({ task: t, done: false })
        rebuild()
        return true
    }

    function setTask(i, t) {
        if (i < 0 || i >= root.todos.length) return
        root.todos[i].task = t
        rebuild()
    }

    function setDone(i, d) {
        if (i < 0 || i >= root.todos.length) return
        root.todos[i].done = d ? true : false
        updateCounts()
    }

    function startEdit(i) {
        if (i < 0 || i >= root.todos.length) return
        root.editingIndex = i
        notesInput.text = root.todos[i].task
        notesInput.forceActiveFocus()
    }

    function cancelEdit() {
        root.editingIndex = -1
        notesInput.text = ""
    }

    function removeTodo(i) {
        if (i < 0 || i >= root.todos.length) return
        root.todos.splice(i, 1)
        if (root.editingIndex === i) cancelEdit()
        else if (root.editingIndex > i) root.editingIndex--
        rebuild()
    }

    Component {
        id: rowComp

        RowLayout {
            property int rowIndex: -1
            property string taskText: ""
            property bool isDone: false
            property bool alive: true

            spacing: 6
            Layout.fillWidth: true

            // Task text + done state in ONE element:
            // label = task text, value = checked (agent-readable)
            CheckBox {
                objectName: "todoDone_" + rowIndex
                Layout.fillWidth: true
                text: taskText
                checked: isDone
                onToggled: if (alive) root.setDone(rowIndex, checked)
            }

            Button {
                objectName: "todoEdit_" + rowIndex
                text: "Edit: " + taskText
                onClicked: if (alive) root.startEdit(rowIndex)
            }

            Button {
                objectName: "todoDelete_" + rowIndex
                text: "Delete: " + taskText
                onClicked: if (alive) root.removeTodo(rowIndex)
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        Label {
            text: "Notes"
            font.pixelSize: 26
            font.bold: true
        }

        // Pending readout - the agent reads "Pending: 1 of 3" from /layout
        Label {
            id: notesPending
            objectName: "notesPending"
            text: root.totalCount === 0
                  ? "Nothing here yet"
                  : "Pending: " + root.pendingCount + " of " + root.totalCount
            font.pixelSize: 14
            color: root.pendingCount > 0 ? "#fbbf24" : "#4ade80"
        }

        // Add / update row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: notesInput
                objectName: "notesInput"
                placeholderText: "Type a task..."
                Layout.fillWidth: true
                onAccepted: notesAddBtn.clicked()
            }

            Button {
                id: notesAddBtn
                objectName: "notesAddBtn"
                highlighted: true
                text: root.editingIndex >= 0 ? "Update task" : "Add todo"
                onClicked: {
                    var t = notesInput.text.trim()
                    if (t === "") {
                        // empty Update = cancel edit
                        root.cancelEdit()
                        return
                    }
                    if (root.editingIndex >= 0) {
                        root.setTask(root.editingIndex, t)
                        root.editingIndex = -1
                    } else {
                        root.addTodo(t)
                    }
                    notesInput.text = ""
                }
            }

            Button {
                id: notesCancelBtn
                objectName: "notesCancelBtn"
                text: "Cancel edit"
                visible: root.editingIndex >= 0
                onClicked: root.cancelEdit()
            }
        }

        // The list: always fully instantiated, no virtualization, so the
        // inspector sees every row even offscreen.
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                id: listCol
                width: root.width - 60
                spacing: 6

                Label {
                    objectName: "notesEmpty"
                    text: root.totalCount === 0 ? "No todos yet - add one above" : ""
                    color: "#6b7280"
                }
            }
        }
    }
}
