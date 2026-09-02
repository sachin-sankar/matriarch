import argparse
import os
import sys
import threading
from enum import Enum

from fastapi import FastAPI, HTTPException
from lib.inspector import QMLInspector
from pydantic import BaseModel, Field
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="QML Inspector API",
    description="REST API for inspecting and interacting with QML applications",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
inspector = None

ROLE_MAP = {
    "TextField": "text_input",
    "TextArea": "text_area",
    "Text": "text",
    "Button": "button",
    "CheckBox": "checkbox",
    "Switch": "switch",
    "ComboBox": "dropdown",
}

ACTION_MAP = {
    "text_input": ["fill", "focus", "clear"],
    "text_area": ["fill", "focus", "clear"],
    "text": ["focus"],
    "button": ["click"],
    "checkbox": ["click", "toggle"],
    "switch": ["click", "toggle"],
    "dropdown": ["select", "focus"],
}


class InteractionAction(str, Enum):
    """Valid interaction actions."""

    FILL = "fill"
    CLICK = "click"
    TOGGLE = "toggle"
    SELECT = "select"
    FOCUS = "focus"
    CLEAR = "clear"


class InteractRequest(BaseModel):
    """Request body for the /interact endpoint."""

    cuid: str = Field(..., description="Component unique identifier from /layout")
    action: InteractionAction = Field(
        ..., description="Action to perform on the component"
    )
    value: str | None = Field(None, description="Value for fill/select actions")


class InteractResponse(BaseModel):
    """Response body for successful interactions."""

    success: bool
    action: str
    cuid: str


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str


@app.get("/raw", response_description="Raw QML inspection tree without processing")
def get_raw():
    if inspector is None:
        raise HTTPException(status_code=500, detail="Inspector not initialized")
    return inspector.get_layout_safe()


@app.get(
    "/layout",
    response_description="Returns the QML application UI tree with component metadata",
)
def get_layout():
    if inspector is None:
        raise HTTPException(status_code=500, detail="Inspector not initialized")

    full_tree = inspector.get_layout_safe()
    if "error" in full_tree:
        raise HTTPException(status_code=500, detail=full_tree["error"])

    def process_node(node):
        children = [
            processed
            for child in node.get("children", [])
            if (processed := process_node(child)) is not None
        ]

        role = node.get("role")
        if role:
            # Skip QtQuick Controls internal wrapper nodes (e.g. ButtonPanel)
            # that have no text/checked property — they're styling sub-components
            if role == "button" and "text" not in node.get("properties", {}):
                return {"id": node["id"], "children": children} if children else None
            if role in ("checkbox", "switch") and "checked" not in node.get(
                "properties", {}
            ):
                return {"id": node["id"], "children": children} if children else None
            if role in ("text_input", "text_area") and "text" not in node.get(
                "properties", {}
            ):
                return {"id": node["id"], "children": children} if children else None
            label = node["properties"].get("text", node["id"])
            if role == "text":
                val = node["properties"].get("text")
            elif role in ("checkbox", "switch"):
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

    return {
        "app_state": {
            "title": props.get("title", "QML App"),
            "dimensions": {"width": app_width, "height": app_height},
        },
        "interactors": processed_tree,
    }


@app.post(
    "/interact",
    response_model=InteractResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid action for role or missing fields",
        },
        404: {"model": ErrorResponse, "description": "CUID not found"},
        500: {
            "model": ErrorResponse,
            "description": "Inspector not initialized or action failed",
        },
    },
    summary="Interact with a QML component",
    description="Perform an action on a QML component identified by its CUID",
)
def interact(req: InteractRequest):
    if inspector is None:
        raise HTTPException(status_code=500, detail="Inspector not initialized")

    obj = inspector.find_by_cuid(req.cuid)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"CUID '{req.cuid}' not found")

    class_name = obj.metaObject().className()
    role = next((v for k, v in ROLE_MAP.items() if class_name.startswith(k)), None)

    valid_actions = ACTION_MAP.get(role, [])
    if req.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{req.action}' not supported for role '{role}'",
        )

    result = inspector.perform_action_safe(obj, req.action, req.value)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return InteractResponse(
        success=result["success"],
        action=result["action"],
        cuid=result["cuid"],
    )


def run_api():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch QML application with an inspection server."
    )
    parser.add_argument("qml_file", help="Path to the .qml file to load")
    args = parser.parse_args()

    qt_app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qml_path = os.path.abspath(args.qml_file)
    engine.load(qml_path)

    if not engine.rootObjects():
        print(f"Error: Could not load QML file at {qml_path}")
        sys.exit(-1)

    inspector = QMLInspector(engine)

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    sys.exit(qt_app.exec())
