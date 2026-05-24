#!/usr/bin/env bash
# run_dev.sh
# Unified launcher: boots the FastAPI server (server.py) and the
# Vite dev server (frontend/) side-by-side. Ctrl-C cleanly stops both.
#
# Usage:
#   ./run_dev.sh                 # mock telemetry, default ports
#   PIA_USE_MOCK=0 ./run_dev.sh  # real serial hardware
#   PORT_API=9000 ./run_dev.sh   # override backend port

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PORT_API="${PORT_API:-8000}"
PORT_WEB="${PORT_WEB:-5173}"

# ── venv activation (best-effort) ────────────────────────────────────────────
if [[ -d "$ROOT/venv" && -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  echo "[run_dev] activated venv: $ROOT/venv"
fi

# ── Prerequisite checks ──────────────────────────────────────────────────────
command -v uvicorn >/dev/null 2>&1 || {
  echo "[run_dev] uvicorn not installed — run: pip install -r requirements.txt" >&2
  exit 1
}
if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "[run_dev] frontend deps not installed — running npm install"
  (cd "$ROOT/frontend" && npm install)
fi

# ── Process bookkeeping ──────────────────────────────────────────────────────
API_PID=""
WEB_PID=""

cleanup() {
  echo ""
  echo "[run_dev] stopping…"
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$WEB_PID" ]] && kill "$WEB_PID" 2>/dev/null || true
  # Give them a beat, then SIGKILL anything still hanging on.
  sleep 0.3
  [[ -n "$API_PID" ]] && kill -9 "$API_PID" 2>/dev/null || true
  [[ -n "$WEB_PID" ]] && kill -9 "$WEB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "[run_dev] done."
}
trap cleanup EXIT INT TERM

# ── Launch backend ───────────────────────────────────────────────────────────
echo "[run_dev] starting FastAPI server on :$PORT_API …"
uvicorn backend.server:app --host 0.0.0.0 --port "$PORT_API" --reload \
  --reload-dir backend --reload-dir sensors --reload-dir perception --reload-dir agents \
  2>&1 | sed -u 's/^/[api] /' &
API_PID=$!

# ── Launch frontend ──────────────────────────────────────────────────────────
echo "[run_dev] starting Vite dev server on :$PORT_WEB …"
(cd "$ROOT/frontend" && npm run dev -- --port "$PORT_WEB") \
  2>&1 | sed -u 's/^/[web] /' &
WEB_PID=$!

cat <<EOF

──────────────────────────────────────────────────────────────────────
  PIA dev stack
  API : http://localhost:$PORT_API   (docs: /docs, ws: /ws/telemetry)
  WEB : http://localhost:$PORT_WEB
  Ctrl-C to stop both.
──────────────────────────────────────────────────────────────────────

EOF

# Wait on either child; if one dies, cleanup() tears the other down.
wait -n "$API_PID" "$WEB_PID"
