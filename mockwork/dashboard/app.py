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


def refresh():
    """Refresh the dashboard by fetching new layout."""
    data = get_layout()

    if "error" in data:
        return f"❌ Error: {data['error']}", json.dumps(data, indent=2)

    title = data.get("app_state", {}).get("title", "QML App")
    interactors = data.get("interactors", {})

    # Format interactors as markdown table
    lines = [f"## Interactors in **{title}**\n"]
    lines.append("| ID | CUID | Role | Label | Value | Focus | Actions |")
    lines.append("|---|---|---|---|---|---|---|")

    def walk(node, depth=0):
        if node is None:
            return
        if isinstance(node, list):
            for child in node:
                walk(child, depth)
        elif isinstance(node, dict):
            if "cuid" in node and "role" in node:
                cuid = node.get("cuid", "")
                role = node.get("role", "")
                label = node.get("label", node.get("id", "unknown"))
                value = node.get("value", "")
                focus = "⭐" if node.get("focus") else ""
                actions = " ".join([f"[{a}]" for a in ACTION_MAP.get(role, [])])
                lines.append(
                    f"| {node.get('id', '')} | {cuid} | {role} | {label} | {value or '-'} | {focus} | {actions} |"
                )
            for child in node.get("children", []):
                walk(child, depth + 1)

    walk(interactors)
    lines.append("")
    lines.append("**Click action buttons below to interact with components.**")

    return title, "\n".join(lines)


def do_action(cuid, action, value=None):
    """Handle action button click."""
    return perform_action(cuid, action)


with gr.Blocks(title="QML Inspector Dashboard") as demo:
    gr.Markdown("# 🎯 QML Inspector Dashboard")
    gr.Markdown("Interact with your QML application components in real-time.")

    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Layout", variant="primary")
        status_output = gr.Textbox(label="Status", interactive=False)

    title_output = gr.Markdown()
    info_output = gr.Markdown()

    refresh_btn.click(
        fn=refresh,
        outputs=[title_output, info_output],
    )

    # Initial render
    demo.load(fn=refresh, outputs=[title_output, info_output])

    gr.HTML("""
    <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 8px;">
        <h3>Quick Actions</h3>
        <p>Use the CUID from the table above to perform actions:</p>
    </div>
    """)

    with gr.Row():
        cuid_input = gr.Textbox(label="CUID", placeholder="Enter component CUID")
        action_select = gr.Dropdown(
            choices=["fill", "click", "toggle", "select", "focus", "clear"],
            label="Action",
            value="fill",
        )
        value_input = gr.Textbox(label="Value", placeholder="For fill/select actions")
        action_btn = gr.Button("Execute", variant="primary")

    action_output = gr.Textbox(label="Result", interactive=False)

    action_btn.click(
        fn=lambda cuid, action, value: do_action(cuid, action, value),
        inputs=[cuid_input, action_select, value_input],
        outputs=[action_output],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
