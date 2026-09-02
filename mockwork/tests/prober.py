#!/usr/bin/env python3
"""Probe /layout and exercise every action on every interactor."""

import json
import sys
import time
from datetime import datetime

import requests

API = "http://127.0.0.1:8080"

ACTION_MAP = {
    "text_input": ["fill", "focus", "clear"],
    "text_area": ["fill", "focus", "clear"],
    "button": ["click"],
    "checkbox": ["click", "toggle"],
    "switch": ["click", "toggle"],
    "dropdown": ["select", "focus"],
}

REPORT = {
    "apps": {},
    "total": 0,
    "success": 0,
    "errors": 0,
}


def fetch_windows():
    """Fetch list of loaded apps."""
    try:
        r = requests.get(f"{API}/windows", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"_error": str(e)}


def fetch_layout(app_name=None):
    """Fetch layout for a specific app or default."""
    try:
        url = f"{API}/layout"
        if app_name:
            url += f"?app={app_name}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"_error": str(e)}


def post_interact(cuid, action, app_name=None, value=None):
    payload = {"cuid": cuid, "action": action}
    if app_name:
        payload["app"] = app_name
    if value is not None:
        payload["value"] = value
    try:
        r = requests.post(f"{API}/interact", json=payload, timeout=10)
        r.raise_for_status()
        return {"ok": True, "status": r.status_code, "body": r.json()}
    except requests.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"ok": False, "status": e.response.status_code, "detail": detail}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


def collect_interactors(node, out=None):
    if out is None:
        out = []
    if node is None:
        return out
    if isinstance(node, list):
        for child in node:
            collect_interactors(child, out)
        return out
    if isinstance(node, dict):
        if "cuid" in node and "role" in node:
            out.append(node)
        for child in node.get("children", []):
            collect_interactors(child, out)
    return out


def probe_app(app_name, windows):
    """Probe a single app."""
    data = fetch_layout(app_name)
    if "_error" in data:
        print(f"  Failed to fetch /layout for {app_name}: {data['_error']}")
        return

    title = data.get("app_state", {}).get("title", app_name)
    interactors = collect_interactors(data.get("interactors"))

    if not interactors:
        print(f"  No interactors found in {app_name}")
        return

    print(f"\n  App: {title} ({app_name})")
    print(f"  Interactors: {len(interactors)}")

    app_results = {"title": title, "interactors": len(interactors), "results": []}
    REPORT["apps"][app_name] = app_results

    for interactor in interactors:
        cuid = interactor["cuid"]
        role = interactor["role"]
        label = interactor.get("label") or interactor.get("id") or "unnamed"
        actions = ACTION_MAP.get(role, [])

        if not actions:
            print(f"    [skip] {cuid} ({role}) — no actions mapped")
            continue

        print(f"    [{cuid}] {role} — {label}")
        for action in actions:
            value = None
            if action == "fill":
                value = "probed"
            elif action == "select":
                value = "0"
            elif action == "toggle":
                value = None  # server casts bool(value)

            t0 = time.monotonic()
            result = post_interact(cuid, action, app_name, value)
            dt = (time.monotonic() - t0) * 1000

            REPORT["total"] += 1
            if result.get("ok"):
                REPORT["success"] += 1
                status = f"ok ({result.get('status', '')})"
                detail = ""
            else:
                REPORT["errors"] += 1
                status = f"FAIL ({result.get('status', result.get('error', ''))})"
                detail = result.get("detail", "")

            app_results["results"].append(
                {
                    "cuid": cuid,
                    "role": role,
                    "label": label,
                    "action": action,
                    "value": value,
                    "status": status,
                    "detail": detail,
                    "ms": round(dt, 1),
                }
            )
            print(
                f"      {action:6s}  {status:30s}  {dt:.0f}ms{('  ' + detail) if detail else ''}"
            )


def prober():
    windows_resp = fetch_windows()
    if "_error" in windows_resp:
        print(f"Failed to fetch /windows: {windows_resp['_error']}")
        sys.exit(1)

    # Handle both old (dict) and new (WindowsResponse) formats
    if isinstance(windows_resp, dict) and "windows" in windows_resp:
        windows = windows_resp["windows"]
    elif isinstance(windows_resp, dict):
        windows = windows_resp
    else:
        print("Unexpected /windows response format")
        sys.exit(1)

    if not windows:
        print("No apps loaded. Start server with: uv run server.py apps/timer.qml")
        sys.exit(0)

    print(f"Found {len(windows)} app(s): {', '.join(windows.keys())}\n")

    for app_name in windows:
        probe_app(app_name, windows)

    print(f"\n{'=' * 60}")
    print(
        f"Results: {REPORT['success']}/{REPORT['total']} OK, {REPORT['errors']} errors"
    )

    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = f"prober-report-{now}.json"
    with open(report_file, "w") as f:
        json.dump(REPORT, f, indent=2, default=str)
    print(f"Report written to {report_file}")


if __name__ == "__main__":
    prober()
