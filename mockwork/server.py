import argparse
import os
import sys
import threading
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from lib.inspector import App
from pydantic import BaseModel, Field
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

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

mcp = FastApiMCP(app, describe_all_responses=True)

# Global registry of loaded apps
apps: dict[str, App] = {}

ROLE_MAP = {
    "TextField": "text_input",
    "TextArea": "text_area",
    "QQuickText": "text",
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

    app: Optional[str] = Field(None, description="App name (defaults to first app)")
    cuid: str = Field(..., description="Component unique identifier from /layout")
    action: InteractionAction = Field(
        ..., description="Action to perform on the component"
    )
    value: Optional[str] = Field(None, description="Value for fill/select actions")


class InteractResponse(BaseModel):
    """Response body for successful interactions."""

    success: bool
    action: str
    cuid: str


class WindowInfo(BaseModel):
    """Information about a loaded QML app window."""

    name: str
    qml_path: str
    alive: bool
    error: Optional[str] = None


class WindowsResponse(BaseModel):
    """Response body for the /windows endpoint."""

    windows: dict[str, WindowInfo]
    total: int


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    """Error response model."""

    detail: str
    """Error response model."""

    detail: str
    """Error response model."""

    detail: str


def _get_app(req: Request) -> Optional[App]:
    """Get the requested app or default to first."""
    app_name = req.query_params.get("app")
    if app_name:
        return apps.get(app_name)
    if apps:
        return next(iter(apps.values()))
    return None


@app.get(
    "/windows",
    response_model=WindowsResponse,
    response_description="List all loaded QML apps",
)
def get_windows():
    return WindowsResponse(
        windows={
            name: WindowInfo(
                name=name,
                qml_path=a.qml_path,
                alive=a.is_alive(),
                error=a._error,
            )
            for name, a in apps.items()
        },
        total=len(apps),
    )


@app.get("/raw", response_description="Raw QML inspection tree without processing")
def get_raw(req: Request):
    a = _get_app(req)
    if a is None:
        raise HTTPException(status_code=500, detail="No apps loaded")
    layout = a.get_layout()
    if "error" in layout:
        raise HTTPException(status_code=500, detail=layout["error"])
    return layout


@app.get(
    "/layout",
    response_description="Returns the QML application UI tree with component metadata",
)
def get_layout(req: Request):
    a = _get_app(req)
    if a is None:
        raise HTTPException(status_code=500, detail="No apps loaded")
    full_tree = a.get_layout()
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
        404: {"model": ErrorResponse, "description": "CUID not found or app not found"},
        500: {
            "model": ErrorResponse,
            "description": "Inspector not initialized or action failed",
        },
    },
    summary="Interact with a QML component",
    description="Perform an action on a QML component identified by its CUID",
)
def interact(req: InteractRequest):
    app_name = req.app
    if app_name:
        a = apps.get(app_name)
        if a is None:
            raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    elif not apps:
        raise HTTPException(status_code=500, detail="No apps loaded")
    else:
        a = next(iter(apps.values()))

    result = a.interact(req.cuid, req.action.value, req.value)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return InteractResponse(
        success=result["success"],
        action=result["action"],
        cuid=result["cuid"],
    )


mcp.mount()
mcp.setup_server()


def run_api():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch QML application(s) with an inspection server."
    )
    parser.add_argument(
        "qml_files",
        nargs="+",
        help="Path(s) to the .qml file(s) to load",
    )
    args = parser.parse_args()

    qt_app = QGuiApplication(sys.argv)

    for i, qml_file in enumerate(args.qml_files):
        app_name = os.path.basename(qml_file).replace(".qml", "")
        if i > 0:
            app_name = f"{app_name}_{i}"
        qml_path = os.path.abspath(qml_file)

        a = App(app_name, qml_path)
        if a.load():
            apps[app_name] = a
            print(f"Loaded: {app_name} from {qml_path}")
        else:
            print(f"Error loading {app_name}: {a._error}")

    if not apps:
        print("Error: No apps could be loaded")
        sys.exit(-1)

    print(f"Loaded {len(apps)} app(s): {', '.join(apps.keys())}")
    print("Windows endpoint: http://127.0.0.1:8080/windows")

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    sys.exit(qt_app.exec())
