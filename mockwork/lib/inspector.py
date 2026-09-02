import threading
import math
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

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._result = None
        self._event = threading.Event()
        self.request_layout.connect(self._do_serialize)

    @Slot()
    def _do_serialize(self):
        try:
            if not self.engine.rootObjects():
                self._result = {"error": "QML Engine root object not found"}
            else:
                root_window = self.engine.rootObjects()[0]
                self._result = self._serialize_qml_item(root_window, 0, 0)
        except Exception as e:
            self._result = {"error": str(e)}
        finally:
            self._event.set()

    def _serialize_qml_item(self, item: QObject, abs_x=0, abs_y=0) -> dict:
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

        role_map = {
            "TextField": "text_input",
            "TextArea": "text_area",
            "Button": "button",
            "CheckBox": "checkbox",
            "Switch": "switch",
            "ComboBox": "dropdown",
        }

        role = next((v for k, v in role_map.items() if class_name.startswith(k)), None)

        # Calculate absolute coordinates
        # QML properties x, y are relative to parent
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

        return {
            "id": item.objectName() or str(item),
            "class": class_name,
            "role": role,
            "properties": properties,
            "coordinates": coords,
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
