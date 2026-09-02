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
    "title": "",
    "total": 0,
    "success": 0,
    "errors": 0,
    "results": [],
}


def fetch_layout():
    try:
        r = requests.get(f"{API}/layout", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"_error": str(e)}


def post_interact(cuid, action, value=None):
    payload = {"cuid": cuid, "action": action}
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


def prober():
    data = fetch_layout()
    if "_error" in data:
        print(f"Failed to fetch /layout: {data['_error']}")
        sys.exit(1)

    REPORT["title"] = data.get("app_state", {}).get("title", "Unknown")
    interactors = collect_interactors(data.get("interactors"))

    if not interactors:
        print("No interactors found.")
        sys.exit(0)

    print(f"App: {REPORT['title']}")
    print(f"Interactors: {len(interactors)}")
    print()

    for interactor in interactors:
        cuid = interactor["cuid"]
        role = interactor["role"]
        label = interactor.get("label") or interactor.get("id") or "unnamed"
        actions = ACTION_MAP.get(role, [])

        if not actions:
            print(f"[skip] {cuid} ({role}) — no actions mapped")
            continue

        print(f"[{cuid}] {role} — {label}")
        for action in actions:
            value = None
            if action == "fill":
                value = "probed"
            elif action == "select":
                value = "0"
            elif action == "toggle":
                value = None  # server casts bool(value)

            t0 = time.monotonic()
            result = post_interact(cuid, action, value)
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

            REPORT["results"].append(
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
                f"  {action:6s}  {status:30s}  {dt:.0f}ms{('  ' + detail) if detail else ''}"
            )

    print()
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
