import threading
import tkinter as tk

import customtkinter as ctk

# Import the standalone File Manager application
from app import FileManagerApp
from flask import Flask, jsonify


# ---------------------------------------------------------
# 1. Widget Serialization Engine
# ---------------------------------------------------------
def serialize_widget(widget: tk.Widget) -> dict:
    """Recursively walks the Tkinter tree and extracts layout, props, and live control values."""

    # Static Configuration Attributes
    props = {}
    for key in widget.keys():
        try:
            val = str(widget.cget(key))
            props[key] = val
        except Exception:
            pass

    # Dynamic Runtime Control Values
    dynamic_state = {}

    if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox, tk.Entry)):
        try:
            if isinstance(widget, ctk.CTkTextbox):
                dynamic_state["value"] = widget.get("1.0", "end-1c")
            else:
                dynamic_state["value"] = widget.get()
        except Exception:
            pass

    elif isinstance(widget, (ctk.CTkCheckBox, ctk.CTkSwitch, tk.Checkbutton)):
        try:
            dynamic_state["value"] = widget.get()
            dynamic_state["is_checked"] = bool(widget.get())
        except Exception:
            pass

    elif isinstance(widget, (ctk.CTkSlider, ctk.CTkProgressBar, tk.Scale)):
        try:
            dynamic_state["value"] = widget.get()
        except Exception:
            pass

    elif isinstance(widget, (ctk.CTkOptionMenu, ctk.CTkComboBox, tk.OptionMenu)):
        try:
            dynamic_state["value"] = widget.get()
        except Exception:
            pass

    # Geometry Layout Specs
    geo_manager = widget.winfo_manager()
    layout_info = {}
    if geo_manager == "pack":
        layout_info = widget.pack_info()
    elif geo_manager == "grid":
        layout_info = widget.grid_info()
    elif geo_manager == "place":
        layout_info = widget.place_info()

    return {
        "id": str(widget),
        "class": widget.winfo_class(),
        "geometry": {
            "manager": geo_manager,
            "width": widget.winfo_width(),
            "height": widget.winfo_height(),
            "x": widget.winfo_x(),
            "y": widget.winfo_y(),
            "params": {k: str(v) for k, v in layout_info.items()},
        },
        "props": props,
        "state": dynamic_state,
        "children": [serialize_widget(child) for child in widget.winfo_children()],
    }


# ---------------------------------------------------------
# 2. REST API Setup
# ---------------------------------------------------------
server = Flask(__name__)
app_instance = None  # Holds the global GUI reference


@server.route("/layout", methods=["GET"])
def get_layout():
    if app_instance is None:
        return jsonify({"error": "Application not initialized"}), 500

    return jsonify(serialize_widget(app_instance))


def run_api():
    server.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


# ---------------------------------------------------------
# 3. Application Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Start Flask in a background daemon thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    print("API Server active at http://localhost:8080/layout")

    # 2. Instantiate and launch the GUI application on the main thread
    ctk.set_appearance_mode("Dark")
    app_instance = FileManagerApp()
    app_instance.mainloop()
