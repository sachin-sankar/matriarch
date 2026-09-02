@server app="mockwork/apps/timer.qml":
    uv run mockwork/server.py {{app}}

@server-many *args="":
    uv run mockwork/server.py {{args}}

inspect:
  xdg-open mockwork/tests/layout_tester.html
