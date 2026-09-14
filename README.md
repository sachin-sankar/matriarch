<p align="center">
  <img src="banner.svg" alt="Matriarch Banner" width="100%" />
</p>

# Matriarch

Headless & live inspection, accessibility tree extraction, and programmatic UI interaction runtime for Qt Quick / QML applications via REST and Model Context Protocol (MCP).

Matriarch bridges live QML scene graphs running in PySide6 to external agentic toolkits and testing harnesses via FastAPI and FastApiMCP.

---

## Features

- **Live Scene Graph Inspection**: Serializes Qt Quick / QML hierarchies across render threads safely using Qt Signals & Slots.
- **Accessibility & Role Mapping**: Translates QML components (`Button`, `TextField`, `Slider`, `CheckBox`, etc.) into semantic accessibility roles, bounding boxes, absolute window coordinates, and interaction capabilities.
- **Programmatic Interaction**: Trigger actions (`click`, `toggle`, `fill`, `select`, `clear`, `scroll`) on live UI elements using target CUIDs (Component Unique IDs).
- **Dual Interface**:
  - **REST API** (`/windows`, `/raw`, `/layout`, `/interact`)
  - **MCP Server** integration for AI agents and LLM tool calling.
- **Multi-App Hosting**: Load and switch between multiple QML applications within a single runtime instance.

---

## Requirements

- Python >= 3.14 (or compatible PySide6 environment)
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

---

## Quickstart

### 1. Enter Environment (Nix / NixOS)

If you are using Nix or running on NixOS (for PySide6/Qt shared libraries and FHS environment):

```bash
nix-shell
```

### 2. Install Dependencies

Using `uv`:
```bash
uv sync
```

Or using standard `pip`:
```bash
pip install -e .
```

### 3. Run an Application with Matriarch Server

Run a sample QML app with the inspection/interaction server:

```bash
uv run mockwork/server.py mockwork/apps/timer.qml
```

Run multiple applications simultaneously:

```bash
uv run mockwork/server.py mockwork/apps/timer.qml mockwork/apps/notes.qml mockwork/apps/filemanager.qml
```

Using `just`:
```bash
just server                     # runs timer.qml by default
just server-many app1.qml app2.qml
```

---

## API Reference

The server starts by default on `http://0.0.0.0:8080`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/windows` | Lists all loaded QML applications, window titles, dimensions, and statuses. |
| `GET` | `/raw?app=<name>` | Raw dump of serialized QML QObject tree properties. |
| `GET` | `/layout?app=<name>` | Semantic accessibility tree with roles, bounds, and supported actions. |
| `POST` | `/interact` | Executes a UI action (`click`, `toggle`, `fill`, `select`, etc.) on a component CUID. |

### Interaction Payload Example

```json
POST /interact
{
  "app": "timer.qml",
  "cuid": "0x7f8a1234abcd",
  "action": "click"
}
```

For input fields (`fill`):
```json
POST /interact
{
  "app": "notes.qml",
  "cuid": "0x7f8a1234abcd",
  "action": "fill",
  "value": "Hello world"
}
```

---

## Testing & Visual Inspection

- **Automated Interaction Prober**:
  ```bash
  uv run mockwork/tests/prober.py
  ```
- **Live Layout Visualizer**:
  ```bash
  just inspect
  # or open mockwork/tests/layout_tester.html in a browser
  ```

---

## Project Structure

```text
├── mockwork/
│   ├── apps/          # Sample QML apps (timer, notes, filemanager, etc.)
│   ├── lib/
│   │   └── inspector.py # Thread-safe QML tree serializer & action dispatcher
│   ├── tests/         # Prober suite and HTML/JS layout inspector
│   └── server.py      # FastAPI + FastApiMCP server & PySide6 bootstrap
├── pyproject.toml
├── justfile
└── shell.nix
```
