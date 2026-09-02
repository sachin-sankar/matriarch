import argparse

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

    def process_node(node):
        # Filter out nulls immediately during child processing
        children = [
            processed
            for child in node.get("children", [])
            if (processed := process_node(child)) is not None
        ]

        # Extract semantic data for this node
        role = node.get("role")
        if role:
            label = node["properties"].get("text", node["id"])
            # For toggles, strictly use the 'checked' property for the value
            if role == "checkbox" or role == "switch":
                val = node["properties"].get("checked")
            else:
                val = node["properties"].get("text")

            return {
                "id": node["id"],
                "role": role,
                "label": label,
                "value": val,
                "coordinates": node["coordinates"],
                "accessible_name": node["id"],
                "children": children,
            }

        # If not an interactor, just return the children (or null if no children)
        return (
            {
                "id": node["id"],
                "children": children,
            }
            if children
            else None
        )

    processed_tree = process_node(full_tree)

    # Note: Shadow filtering is complex on a tree.
    # For now, we return the semantic tree structure.
    interactors = processed_tree

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
    parser = argparse.ArgumentParser(
        description="Launch QML application with an inspection server."
    )
    parser.add_argument("qml_file", help="Path to the .qml file to load")
    args = parser.parse_args()

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Load the provided QML file
    qml_path = os.path.abspath(args.qml_file)
    engine.load(qml_path)

    if not engine.rootObjects():
        print(f"Error: Could not load QML file at {qml_path}")
        sys.exit(-1)

    # Initialize the inspector with the engine
    inspector = QMLInspector(engine)

    # Run API in a separate thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    sys.exit(app.exec())
