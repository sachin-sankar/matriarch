import math
import re
import threading

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine


def safe_json_value(val):
    """Converts PySide/Qt data types to strict JSON-compliant primitives."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if math.isinf(val) or math.isnan(val):
            return str(val)
        return val
    if isinstance(val, (str, list, dict)):
        return val
    return str(val)


class QMLInspector(QObject):
    """Bridge object that safely runs tree inspection on the main GUI thread."""

    request_layout = Signal()
    perform_action = Signal(QObject, str, object)

    def __init__(self, engine: QQmlApplicationEngine):
        super().__init__()
        self.engine = engine
        self._result = None
        self._event = threading.Event()
        self._cuid_to_obj: dict[str, QObject] = {}
        self.request_layout.connect(self._do_serialize)
        self.perform_action.connect(self._do_perform_action)

    @Slot()
    def _do_serialize(self):
        self._cuid_to_obj.clear()
        try:
            if not self.engine.rootObjects():
                self._result = {"error": "QML Engine root object not found"}
            else:
                root_window = self.engine.rootObjects()[0]
                self._result = self._serialize_qml_item(root_window)
        except Exception as e:  # noqa: BLE001
            self._result = {"error": str(e)}
        finally:
            self._event.set()

    @Slot(QObject, str, object)
    def _do_perform_action(self, obj, action, value):
        try:
            meta = obj.metaObject()
            class_name = meta.className()

            if (
                class_name.startswith("TextField")
                and action == "fill"
                or class_name.startswith("TextArea")
                and action == "fill"
            ):
                obj.setProperty("text", str(value))
                self._result = {
                    "success": True,
                    "action": "fill",
                    "cuid": self._get_cuid(obj),
                }
            elif class_name.startswith("Button") and action == "click":
                obj.click()
                self._result = {
                    "success": True,
                    "action": "click",
                    "cuid": self._get_cuid(obj),
                }
            elif (
                class_name.startswith("CheckBox")
                and action in ("click", "toggle")
                or class_name.startswith("Switch")
                and action in ("click", "toggle")
            ):
                obj.click()
                self._result = {
                    "success": True,
                    "action": action,
                    "cuid": self._get_cuid(obj),
                }
            elif class_name.startswith("ComboBox") and action == "select":
                try:
                    obj.setCurrentIndex(int(value) if value else 0)
                    self._result = {
                        "success": True,
                        "action": "select",
                        "cuid": self._get_cuid(obj),
                    }
                except ValueError, TypeError:
                    self._result = {"error": f"Invalid index: {value}"}
            elif class_name.startswith(("TextField", "TextArea")) and action == "focus":
                obj.forceActiveFocus()
                self._result = {
                    "success": True,
                    "action": "focus",
                    "cuid": self._get_cuid(obj),
                }
            elif class_name.startswith(("TextField", "TextArea")) and action == "clear":
                obj.setProperty("text", "")
                self._result = {
                    "success": True,
                    "action": "clear",
                    "cuid": self._get_cuid(obj),
                }
            else:
                self._result = {"error": f"No handler for {class_name}/{action}"}
        except Exception as e:  # noqa: BLE001
            self._result = {"error": str(e)}
        finally:
            self._event.set()

    def _get_cuid(self, obj: QObject) -> str:
        match = re.search(r"0x[0-9a-fA-F]+", str(obj))
        return match.group(0) if match else str(id(obj))

    def find_by_cuid(self, cuid: str):
        """Find QObject by CUID stored during last layout."""
        return self._cuid_to_obj.get(cuid)

    def perform_action_safe(self, obj, action: str, value=None, timeout=3.0):
        self._event.clear()
        self.perform_action.emit(obj, action, value)
        success = self._event.wait(timeout=timeout)
        if not success:
            return {"error": "Action timed out"}
        return self._result

    def _serialize_qml_item(self, item: QObject, abs_x=0, abs_y=0) -> dict:
        meta = item.metaObject()
        class_name = meta.className()
        properties = {}

        for i in range(meta.propertyCount()):
            prop = meta.property(i)
            name = str(prop.name())
            try:
                raw_val = item.property(name)
                properties[name] = safe_json_value(raw_val)
            except Exception:  # noqa: BLE001, S110
                pass
        role_map = {
            "TextField": "text_input",
            "TextArea": "text_area",
            "QQuickText": "text",
            "Text": "text",
            "Button": "button",
            "CheckBox": "checkbox",
            "Switch": "switch",
            "ComboBox": "dropdown",
        }

        role = next((v for k, v in role_map.items() if class_name.startswith(k)), None)

        rel_x = properties.get("x", 0)
        rel_y = properties.get("y", 0)
        actual_abs_x = abs_x + rel_x
        actual_abs_y = abs_y + rel_y

        coords = None
        if role:
            try:
                coords = {
                    "x": actual_abs_x,
                    "y": actual_abs_y,
                    "w": properties.get("width", 0),
                    "h": properties.get("height", 0),
                }
            except Exception:  # noqa: BLE001, S110
                pass

        match = re.search(r"0x[0-9a-fA-F]+", str(item))
        cuid = match.group(0) if match else str(id(item))
        self._cuid_to_obj[cuid] = item

        return {
            "id": item.objectName() or re.sub(r"\s+at\s+0x[0-9a-f]+>", "", str(item)),
            "class": class_name,
            "role": role,
            "properties": properties,
            "coordinates": coords,
            "cuid": cuid,
            "children": [
                self._serialize_qml_item(child, actual_abs_x, actual_abs_y)
                for child in item.children()
                if hasattr(child, "metaObject")
            ],
        }

    def get_layout_safe(self, timeout=3.0):
        self._event.clear()
        self.request_layout.emit()
        success = self._event.wait(timeout=timeout)
        if not success:
            return {"error": "Qt Main Thread inspection timed out"}
        return self._result


class App:
    """Manages a single QML app instance with its inspector."""

    def __init__(self, name: str, qml_path: str):
        import os

        self.name = name
        self.qml_path = os.path.abspath(os.path.expanduser(qml_path))
        self.qt_app: QObject | None = None  # Will be set on main thread
        self.engine: QQmlApplicationEngine | None = None
        self.inspector: QMLInspector | None = None
        self._loaded = threading.Event()
        self._error: str | None = None

    def load(self) -> bool:
        """Load the QML app. Must be called from main thread."""
        try:
            self.engine = QQmlApplicationEngine()
            self.engine.load(self.qml_path)

            if not self.engine.rootObjects():
                self._error = f"Could not load QML file at {self.qml_path}"
                return False

            self.inspector = QMLInspector(self.engine)
            self._loaded.set()
            return True
        except Exception as e:  # noqa: BLE001
            self._error = str(e)
            return False

    def get_layout(self, timeout=3.0) -> dict:
        if not self._loaded.wait(timeout=timeout):
            return {"error": f"App '{self.name}' not loaded"}
        if self.inspector is None:
            return {"error": f"Inspector not initialized for '{self.name}'"}
        return self.inspector.get_layout_safe(timeout)

    def interact(self, cuid: str, action: str, value=None, timeout=3.0) -> dict:
        if not self._loaded.wait(timeout=timeout):
            return {"error": f"App '{self.name}' not loaded"}
        if self.inspector is None:
            return {"error": f"Inspector not initialized for '{self.name}'"}
        obj = self.inspector.find_by_cuid(cuid)
        if obj is None:
            return {"error": f"CUID '{cuid}' not found in app '{self.name}'"}
        return self.inspector.perform_action_safe(obj, action, value, timeout)

    def is_alive(self) -> bool:
        return self._loaded.is_set() and self.engine is not None
