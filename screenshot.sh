#!/usr/bin/env bash
# Desktop + phone screenshots from offline snapshot + live server on :4278.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-4278}"
CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)"
mkdir -p screenshots dist
shot() {
  local url="$1" out="$2" size="$3"
  local prof; prof="$(mktemp -d /tmp/oriolesshot.XXXX)"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --run-all-compositor-stages-before-draw --virtual-time-budget=12000 \
    --window-size="$size" --user-data-dir="$prof" --screenshot="$out" "$url" >/dev/null 2>&1
  rm -rf "$prof"; echo "  $out ($(wc -c < "$out") bytes)"
}
SNAP="file://$PWD/dist/orioles-2026-snapshot.html"
U="http://127.0.0.1:$PORT"
shot "$SNAP" screenshots/00-best-home.png 1440,1200
shot "$SNAP" screenshots/overview.png 1440,1600
shot "$SNAP" screenshots/full.png 1440,6200
shot "$SNAP" screenshots/mobile.png 430,10000
if curl -sf "$U/healthz" >/dev/null 2>&1; then
  shot "$U/" screenshots/live.png 1440,1400
fi
# keep a copy of the classic hero shot name for back-compat
cp -f screenshots/00-best-home.png screenshots/00-best-hero-and-season-chart.png 2>/dev/null || true
