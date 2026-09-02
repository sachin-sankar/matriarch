import argparse
import sys
import os
import threading
from flask import Flask, jsonify, request
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from lib.inspector import QMLInspector

server = Flask(__name__)
inspector = None

ROLE_MAP = {
    "TextField": "text_input",
    "TextArea": "text_area",
    "Button": "button",
    "CheckBox": "checkbox",
    "Switch": "switch",
    "ComboBox": "dropdown",
}

ACTION_MAP = {
    "text_input": ["fill", "focus", "clear"],
    "text_area": ["fill", "focus", "clear"],
    "button": ["click"],
    "checkbox": ["click", "toggle"],
    "switch": ["click", "toggle"],
    "dropdown": ["select", "focus"],
}


@server.route("/layout", methods=["GET"])
def get_layout():
    if inspector is None:
        return jsonify({"error": "Inspector not initialized"}), 500

    full_tree = inspector.get_layout_safe()
    if "error" in full_tree:
        return jsonify(full_tree), 500

    def process_node(node):
        children = [
            processed
            for child in node.get("children", [])
            if (processed := process_node(child)) is not None
        ]

        role = node.get("role")
        if role:
            label = node["properties"].get("text", node["id"])
            if role == "checkbox" or role == "switch":
                val = node["properties"].get("checked")
            else:
                val = node["properties"].get("text")

            return {
                "cuid": node.get("cuid"),
                "id": node["id"],
                "role": role,
                "label": label,
                "value": val,
                "coordinates": node["coordinates"],
                "accessible_name": node["id"],
                "focus": node["properties"].get("activeFocus", False),
                "children": children,
            }

        return {"id": node["id"], "children": children} if children else None

    processed_tree = process_node(full_tree)
    interactors = processed_tree

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
                "title": props.get("title", "QML App"),
                "dimensions": {"width": app_width, "height": app_height},
            },
            "interactors": interactors,
        }
    )


@server.route("/interact", methods=["POST"])
def interact():
    if inspector is None:
        return jsonify({"error": "Inspector not initialized"}), 500

    data = request.get_json()
    if not data or "cuid" not in data or "action" not in data:
        return jsonify({"error": "Required fields: cuid, action"}), 400

    cuid = data["cuid"]
    action = data["action"]
    value = data.get("value")

    obj = inspector.find_by_cuid(cuid)
    if obj is None:
        return jsonify({"error": f"CUID '{cuid}' not found"}), 404

    class_name = obj.metaObject().className()
    role = next((v for k, v in ROLE_MAP.items() if class_name.startswith(k)), None)

    valid_actions = ACTION_MAP.get(role, [])
    if action not in valid_actions:
        return jsonify(
            {"error": f"Action '{action}' not supported for role '{role}'"}
        ), 400

    result = inspector.perform_action_safe(obj, action, value)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


def run_api():
    server.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch QML application with an inspection server."
    )
    parser.add_argument("qml_file", help="Path to the .qml file to load")
    args = parser.parse_args()

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qml_path = os.path.abspath(args.qml_file)
    engine.load(qml_path)

    if not engine.rootObjects():
        print(f"Error: Could not load QML file at {qml_path}")
        sys.exit(-1)

    inspector = QMLInspector(engine)

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    sys.exit(app.exec())
