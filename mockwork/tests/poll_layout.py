#!/usr/bin/env python3
"""Poll /layout and print diff against previous response."""

import json
import sys
import time

import requests

URL = "http://127.0.0.1:8080/layout"
POLL_INTERVAL = 0.5  # seconds


def load():
    try:
        r = requests.get(URL, timeout=2)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"_error": str(e)}


def diff(a, b, path=""):
    """Yield (path, old, new) for every leaf-level difference between dicts/lists."""
    if type(a) is not type(b):
        yield f"{path} (type change: {type(a).__name__} -> {type(b).__name__})", a, b
        return
    if isinstance(a, dict):
        keys = set(a) | set(b)
        for k in keys:
            p = f"{path}.{k}" if path else k
            if k not in a:
                yield p, "<missing>", b[k]
            elif k not in b:
                yield p, a[k], "<missing>"
            else:
                yield from diff(a[k], b[k], p)
    elif isinstance(a, list):
        maxlen = max(len(a), len(b))
        for i in range(maxlen):
            p = f"{path}[{i}]"
            if i >= len(a):
                yield p, "<missing>", b[i]
            elif i >= len(b):
                yield p, a[i], "<missing>"
            else:
                yield from diff(a[i], b[i], p)
    else:
        if a != b:
            yield path, a, b


def main():
    prev = load()
    if "_error" in prev:
        print(f"[init] error: {prev['_error']}")
        sys.exit(1)

    print(
        f"[init] title={prev['app_state']['title']}  "
        f"interactors={json.dumps(prev['interactors'], default=str)[:120]}"
    )

    while True:
        curr = load()
        if "_error" in curr:
            print(f"[error] {curr['_error']}")
            time.sleep(POLL_INTERVAL)
            continue

        changes = list(diff(prev, curr))
        if changes:
            print(f"\n[change] at {time.strftime('%H:%M:%S')}")
            for path, old, new in changes:
                print(f"  {path}")
                print(f"    -  {old!r}")
                print(f"    +  {new!r}")
            print()

        prev = curr
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
