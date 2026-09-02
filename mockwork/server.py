import sys
import threading

from flask import Flask, jsonify
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


import math


def safe_json_value(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        # Handle non-finite JSON values (Infinity / NaN)
        if math.isinf(val) or math.isnan(val):
            return str(val)
        return val
    if isinstance(val, (str, list, dict)):
        return val

    # Fallback for complex Qt objects (QRectF, QFont, QColor, QJSValue)
    return str(val)


# ---------------------------------------------------------
# 1. Main-Thread QML Inspector Helper
# ---------------------------------------------------------
class QMLInspector(QObject):
    """Bridge object that safely runs tree inspection on the main GUI thread."""

    # Signal sent from Flask thread to request layout
    request_layout = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._result = None
        self._event = threading.Event()

        # Connect signal so handler runs on the thread where this object lives (Main Thread)
        self.request_layout.connect(self._do_serialize)

    @Slot()
    def _do_serialize(self):
        """Executed EXCLUSIVELY on the Qt Main Thread."""
        try:
            if not self.engine.rootObjects():
                self._result = {"error": "QML Engine root object not found"}
            else:
                root_window = self.engine.rootObjects()[0]
                self._result = self._serialize_qml_item(root_window)
        except Exception as e:
            self._result = {"error": str(e)}
        finally:
            self._event.set()  # Notify Flask thread that data is ready

    def _serialize_qml_item(self, item: QObject) -> dict:
        meta = item.metaObject()
        class_name = meta.className()
        properties = {}

        for i in range(meta.propertyCount()):
            prop = meta.property(i)
            name = prop.name()
            try:
                raw_val = item.property(name)
                properties[name] = safe_json_value(raw_val)
            except Exception:
                pass

        # Define which QML classes map to which semantic roles
        role_map = {
            "TextField": "text_input",
            "TextArea": "text_area",
            "Button": "button",
            "CheckBox": "checkbox",
            "Switch": "switch",
            "ComboBox": "dropdown",
        }

        role = next((v for k, v in role_map.items() if class_name.startswith(k)), None)

        # Extract geometry for interactors
        coords = None
        if role:
            # Try to get x, y, width, height properties if they exist
            try:
                coords = {
                    "x": properties.get("x", 0),
                    "y": properties.get("y", 0),
                    "w": properties.get("width", 0),
                    "h": properties.get("height", 0),
                }
            except Exception:
                pass

        return {
            "id": item.objectName() or str(item),
            "class": class_name,
            "role": role,
            "properties": properties,
            "coordinates": coords,
            "children": [
                self._serialize_qml_item(child)
                for child in item.children()
                if hasattr(child, "metaObject")
            ],
        }

    def get_layout_safe(self, timeout=3.0):
        """Called by Flask thread to wait for main thread execution."""
        self._event.clear()
        self.request_layout.emit()

        # Wait until Qt main thread finishes serialization
        success = self._event.wait(timeout=timeout)
        if not success:
            return {"error": "Qt Main Thread inspection timed out"}
        return self._result


# ---------------------------------------------------------
# 2. REST API Engine
# ---------------------------------------------------------
server = Flask(__name__)
inspector = None


@server.route("/layout", methods=["GET"])
def get_layout():
    if inspector is None:
        return jsonify({"error": "Inspector not initialized"}), 500

    full_tree = inspector.get_layout_safe()
    if "error" in full_tree:
        return jsonify(full_tree), 500

    # Flatten tree into the semantic interaction map
    interactors = []

    def flatten(node):
        if node.get("role"):
            # Extract human-readable label if available
            label = node["properties"].get("text", node["id"])
            # Get current value
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

    return jsonify(
        {
            "app_state": {
                "title": "QML File Manager",
                "dimensions": {"width": 900, "height": 550},
            },
            "interactors": interactors,
        }
    )


def run_api():
    server.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


# ---------------------------------------------------------
# 3. Application Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    import os

    # Use Basic or Material style instead of Fusion
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Material"
    # Start Flask API in background thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Qt Main Application setup
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load("main.qml")  # Ensure correct path to main.qml

    if not engine.rootObjects():
        sys.exit(-1)

    # Initialize inspector on the MAIN THREAD
    inspector = QMLInspector(engine)

    # Start Main Qt Loop
    sys.exit(app.exec())
