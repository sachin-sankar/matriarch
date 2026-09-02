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


def render_dashboard():
    """Render the dashboard from current layout."""
    data = get_layout()
    if "error" in data:
        return f"❌ Error: {data['error']}", "", []

    title = data.get("app_state", {}).get("title", "QML App")
    interactors = flatten_interactors(data.get("interactors"))

    rows = []
    for item in interactors:
        cuid = item.get("cuid", "")
        role = item.get("role", "")
        label = item.get("label", item.get("id", "unknown"))
        value = item.get("value", "")
        focus = item.get("focus", False)
        actions = ACTION_MAP.get(role, [])

        # Distinct background for focused items
        if focus:
            bg_color = "#FFF3CD"  # Light yellow
            border = "2px solid #FFC107"
        else:
            bg_color = "#F8F9FA"
            border = "1px solid #DEE2E6"

        action_buttons = []
        for action in actions:
            if action == "fill":
                btn = gr.Button(f"Fill ({action})", variant="primary", size="sm")
                btn.click(
                    fn=lambda c=cuid, a=action: perform_action(c, a, None),
                    outputs=[status_output],
                )
                action_buttons.append(btn)
            elif action == "toggle":
                btn = gr.Button(f"Toggle ({action})", variant="secondary", size="sm")
                btn.click(
                    fn=lambda c=cuid, a=action: perform_action(c, a, None),
                    outputs=[status_output],
                )
                action_buttons.append(btn)
            elif action == "select":
                btn = gr.Button(f"Select ({action})", variant="secondary", size="sm")
                btn.click(
                    fn=lambda c=cuid, a=action: perform_action(c, a, None),
                    outputs=[status_output],
                )
                action_buttons.append(btn)
            else:
                btn = gr.Button(
                    f"{action.capitalize()}", variant="secondary", size="sm"
                )
                btn.click(
                    fn=lambda c=cuid, a=action: perform_action(c, a, None),
                    outputs=[status_output],
                )
                action_buttons.append(btn)

        with gr.Row():
            with gr.Column(scale=2):
                gr.HTML(f"""
                <div style="background: {bg_color}; border: {border}; padding: 10px; border-radius: 8px; margin: 5px 0;">
                    <strong>{label}</strong><br>
                    <small>
                        ID: <code>{item.get("id", "")}</code> |
                        CUID: <code>{cuid}</code> |
                        Role: <code>{role}</code> |
                        Value: <code>{value or "(empty)"}</code>
                        {'<span style="color: #FFC107; font-weight: bold;"> ⭐ FOCUSED</span>' if focus else ""}
                    </small>
                </div>
                """)
            with gr.Column(scale=1):
                for btn in action_buttons:
                    btn.render()

    return title, json.dumps(data, indent=2, default=str), rows


def perform_action(cuid, action, value):
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


def refresh():
    """Refresh the dashboard."""
    return render_dashboard()


with gr.Blocks(title="QML Inspector Dashboard") as demo:
    gr.Markdown("# 🎯 QML Inspector Dashboard")
    gr.Markdown("Interact with your QML application components in real-time.")

    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Layout", variant="primary")
        status_output = gr.Textbox(label="Status", interactive=False)

    title_output = gr.Markdown()
    raw_output = gr.JSON(label="Raw API Response", interactive=False)

    with gr.Column() as interactors_container:
        gr.Markdown("## Interactors")

    refresh_btn.click(
        fn=refresh, outputs=[title_output, raw_output, interactors_container]
    )

    # Initial render
    demo.load(fn=refresh, outputs=[title_output, raw_output, interactors_container])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
