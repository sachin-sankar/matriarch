import sys
import os
import threading
from flask import Flask, jsonify
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from lib.inspector import QMLInspector

server = Flask(__name__)
inspector = None


@server.route("/layout", methods=["GET"])
def get_layout():
    if inspector is None:
        return jsonify({"error": "Inspector not initialized"}), 500

    full_tree = inspector.get_layout_safe()
    if "error" in full_tree:
        return jsonify(full_tree), 500

    interactors = []

    def flatten(node):
        if node.get("role"):
            label = node["properties"].get("text", node["id"])
            val = node["properties"].get("text") or node["properties"].get("checked")
            interactors.append(
                {
                    "id": node["id"],
                    "role": node["role"],
                    "label": label,
                    "value": val,
                    "coordinates": node["coordinates"],
                    "accessible_name": node["id"],
                }
            )
        for child in node.get("children", []):
            flatten(child)

    flatten(full_tree)

    # Root node is the root window
    props = full_tree.get("properties", {})
    app_width = props.get("width") or 900
    app_height = props.get("height") or 550

    if app_width == 0 or app_height == 0:

        def find_root_dims(node):
            nonlocal app_width, app_height
            if "Window" in node.get("class", ""):
                p = node.get("properties", {})
                app_width = p.get("width") or app_width
                app_height = p.get("height") or app_height
            for child in node.get("children", []):
                find_root_dims(child)

        find_root_dims(full_tree)

    return jsonify(
        {
            "app_state": {
                "title": "QML File Manager",
                "dimensions": {"width": app_width, "height": app_height},
            },
            "interactors": interactors,
        }
    )


def run_api():
    server.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Updated path to the refactored qml file
    qml_file = os.path.abspath("apps/filemanager.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    # Initialize the inspector with the engine
    inspector = QMLInspector(engine)

    # Run API in a separate thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    sys.exit(app.exec())
