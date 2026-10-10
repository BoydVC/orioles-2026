#!/usr/bin/env bash
# Orioles 2026 Camden Yards night wall: ./run.sh start|stop|restart|status|fetch|build|test|ship
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-4278}"; PID=data/server.pid; LOG=data/server.log
running(){ [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
case "${1:-start}" in
  start)
    if running; then echo "already running (pid $(cat $PID)) on http://127.0.0.1:$PORT"; exit 0; fi
    [ -f data/season.json ] || { python3 build_research.py; python3 build.py; }
    PORT=$PORT nohup python3 server.py >>"$LOG" 2>&1 &
    echo $! > "$PID"; sleep 0.6
    running && echo "started pid $(cat $PID) → http://127.0.0.1:$PORT" || { echo "failed; see $LOG"; exit 1; } ;;
  stop) if running; then kill "$(cat $PID)" 2>/dev/null || true; rm -f "$PID"; echo stopped; else echo "not running"; fi ;;
  restart) "$0" stop || true; sleep 0.3; "$0" start ;;
  status) if running; then echo "running pid $(cat $PID) → http://127.0.0.1:$PORT"; else echo "stopped"; fi ;;
  build) python3 build_research.py && python3 build.py && ./screenshot.sh ;;
  ship) python3 build_research.py && python3 build.py && ./run.sh restart && ./screenshot.sh && ./run.sh test ;;
  fetch) ./fetch.sh && "$0" build ;;
  test) python3 tests/smoke_test.py ;;
  *) echo "usage: $0 start|stop|restart|status|fetch|build|ship|test"; exit 2 ;;
esac
