@server app="mockwork/apps/timer.qml":
    uv run mockwork/server.py {{app}}

inspect:
  xdg-open mockwork/tests/layout_tester.html
