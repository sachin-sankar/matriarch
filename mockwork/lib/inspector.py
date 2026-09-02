import math
import re
import threading

from PySide6.QtCore import QObject, Signal, Slot


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

    def __init__(self, engine):
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
        except Exception as e:
            self._result = {"error": str(e)}
        finally:
            self._event.set()

    @Slot(QObject, str, object)
    def _do_perform_action(self, obj, action, value):
        try:
            class_name = obj.metaObject().className()

            if action == "fill":
                if hasattr(obj, "setProperty"):
                    obj.setProperty("text", value)
                else:
                    raise AttributeError(f"No setProperty on {class_name}")
            elif action == "click":
                if hasattr(obj, "click"):
                    obj.click()
                elif class_name.startswith(("CheckBox", "Switch")) and hasattr(
                    obj, "toggle"
                ):
                    obj.toggle()
                else:
                    raise AttributeError(f"No click/toggle on {class_name}")
            elif action == "toggle":
                if hasattr(obj, "setChecked"):
                    obj.setChecked(bool(value))
                elif hasattr(obj, "toggle"):
                    obj.toggle()
                else:
                    raise AttributeError(f"No setChecked/toggle on {class_name}")
            elif action == "select":
                if hasattr(obj, "setCurrentIndex"):
                    obj.setCurrentIndex(int(value))
                else:
                    raise AttributeError(f"No setCurrentIndex on {class_name}")
            elif action == "focus":
                if hasattr(obj, "setFocus"):
                    obj.setFocus()
                else:
                    raise AttributeError(f"No setFocus on {class_name}")
            elif action == "clear":
                if hasattr(obj, "clear"):
                    obj.clear()
                else:
                    raise AttributeError(f"No clear on {class_name}")

            self._result = {"success": True, "action": action, "cuid": obj.objectName()}
        except Exception as e:
            self._result = {"error": str(e)}
        finally:
            self._event.set()

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
            except Exception:
                pass
        role_map = {
            "TextField": "text_input",
            "TextArea": "text_area",
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
            except Exception:
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
