@server app="mockwork/apps/timer.qml":
    uv run mockwork/server.py {{app}}

@server-many:
    uv run mockwork/server.py $(arg-list)

inspect:
  xdg-open mockwork/tests/layout_tester.html
