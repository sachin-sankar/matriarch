#!/usr/bin/env python3
"""Gradio dashboard for QML Inspector API."""

import json

import gradio as gr
import requests

API_URL = "http://127.0.0.1:8080"


ACTION_MAP = {
    "text_input": ["fill", "focus", "clear"],
    "text_area": ["fill", "focus", "clear"],
    "button": ["click"],
    "checkbox": ["click", "toggle"],
    "switch": ["click", "toggle"],
    "dropdown": ["select", "focus"],
}


def get_layout():
    """Fetch layout from API."""
    try:
        r = requests.get(f"{API_URL}/layout", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def flatten_interactors(node, depth=0):
    """Recursively flatten interactors tree into list."""
    items = []
    if node is None:
        return items
    if isinstance(node, list):
        for child in node:
            items.extend(flatten_interactors(child, depth))
    elif isinstance(node, dict):
        if "cuid" in node and "role" in node:
            items.append(node)
        for child in node.get("children", []):
            items.extend(flatten_interactors(child, depth + 1))
    return items


def perform_action(cuid, action, value=None):
    """Perform an action on a component."""
    try:
        payload = {"cuid": cuid, "action": action}
        if value is not None:
            payload["value"] = value
        r = requests.post(f"{API_URL}/interact", json=payload, timeout=10)
        r.raise_for_status()
        result = r.json()
        return f"✅ {result.get('action', action)} on {cuid[:4]}..."
    except requests.RequestException as e:
        return f"❌ Error: {e}"


# Global state
_current_data = {}
_interactor_components = []


def refresh():
    """Refresh the dashboard by fetching new layout."""
    global _current_data
    _current_data = get_layout()

    if "error" in _current_data:
        return (
            f"❌ Error: {_current_data['error']}",
            json.dumps(_current_data, indent=2),
            [],
        )

    title = _current_data.get("app_state", {}).get("title", "QML App")
    interactors = flatten_interactors(_current_data.get("interactors"))

    # Build component rows
    rows = []
    for item in interactors:
        cuid = item.get("cuid", "")
        role = item.get("role", "")
        label = item.get("label", item.get("id", "unknown"))
        value = item.get("value", "")
        focus = item.get("focus", False)
        actions = ACTION_MAP.get(role, [])

        # Distinct styling for focused items
        if focus:
            html_content = f"""
            <div style="background: #FFF3CD; border: 2px solid #FFC107; padding: 10px; border-radius: 8px; margin: 5px 0;">
                <strong>{label}</strong><br>
                <small>
                    ID: <code>{item.get("id", "")}</code> |
                    CUID: <code>{cuid}</code> |
                    Role: <code>{role}</code> |
                    Value: <code>{value or "(empty)"}</code>
                    <span style="color: #FFC107; font-weight: bold;"> ⭐ FOCUSED</span>
                </small>
            </div>
            """
        else:
            html_content = f"""
            <div style="background: #F8F9FA; border: 1px solid #DEE2E6; padding: 10px; border-radius: 8px; margin: 5px 0;">
                <strong>{label}</strong><br>
                <small>
                    ID: <code>{item.get("id", "")}</code> |
                    CUID: <code>{cuid}</code> |
                    Role: <code>{role}</code> |
                    Value: <code>{value or "(empty)"}</code>
                </small>
            </div>
            """

        # Create action buttons
        with gr.Row():
            gr.HTML(html_content)
            action_btns = []
            for action in actions:
                btn = gr.Button(
                    f"{action.capitalize()}", variant="secondary", size="sm"
                )
                btn.click(
                    fn=lambda c=cuid, a=action: perform_action(c, a),
                    outputs=[status_output],
                )
                action_btns.append(btn)
            _interactor_components.extend(action_btns)

        rows.append(None)  # Placeholder

    return title, json.dumps(_current_data, indent=2, default=str), rows


def clear_interactors():
    """Clear interactors container."""
    return []


with gr.Blocks(title="QML Inspector Dashboard") as demo:
    gr.Markdown("# 🎯 QML Inspector Dashboard")
    gr.Markdown("Interact with your QML application components in real-time.")

    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Layout", variant="primary")
        status_output = gr.Textbox(label="Status", interactive=False)

    title_output = gr.Markdown()
    raw_output = gr.JSON(label="Raw API Response")

    with gr.Column() as interactors_container:
        gr.Markdown("## Interactors")

    refresh_btn.click(
        fn=refresh, outputs=[title_output, raw_output, interactors_container]
    )

    # Initial render
    demo.load(fn=refresh, outputs=[title_output, raw_output, interactors_container])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
