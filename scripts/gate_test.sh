#!/usr/bin/env bash
# gate_test.sh — verify the admin gate on `research_and_ingest_topic` over the
# live SSE transport, without triggering any web scrape or database write.
#
# Usage:   ./scripts/gate_test.sh <BASE_URL> [EMAIL] [SECRET]
#
#   A. DENY  (everyday-user path, no headers):
#        ./scripts/gate_test.sh https://YOUR-APP.up.railway.app
#        → expect: restricted to system administrators
#
#   B. DENY  (wrong credentials):
#        ./scripts/gate_test.sh https://YOUR-APP.up.railway.app attacker@evil.com wrong-secret
#        → expect: restricted to system administrators
#
#   C. ALLOW (correct creds — SAFE: empty args, so it never scrapes or writes):
#        ./scripts/gate_test.sh https://YOUR-APP.up.railway.app ofer.neumann123@gmail.com "$RESEARCH_INGEST_SECRET"
#        → expect: provide either a `query`...   (gate passed)
#
# Why empty args are safe: the tool runs _authorize_admin() FIRST. Only after the
# gate passes does it hit the "provide either a query or url" check — so a passed
# gate returns that harmless error with zero side effects.
#
# Notes:
#   - If ALL three cases return the denial (including C), the Railway env vars
#     ADMIN_EMAIL / RESEARCH_INGEST_SECRET are probably unset → the tool fails closed.
#   - If you get no `data:` result, the proxy may be buffering SSE; the curl below
#     already requests `Accept: text/event-stream`.
set -eo pipefail

BASE="${1:?pass the Railway base URL, no trailing slash}"
EMAIL="${2:-}"
SECRET="${3:-}"

CAP="$(mktemp)"
curl -sN -H 'Accept: text/event-stream' "$BASE/sse" > "$CAP" &   # open SSE stream
SSE_PID=$!
trap 'kill $SSE_PID 2>/dev/null; rm -f "$CAP"' EXIT

# Wait for the `endpoint` event and extract the per-session POST URL.
EP=""
for _ in $(seq 1 20); do
  EP=$(grep -m1 -oE '/messages/\?session_id=[a-f0-9]+' "$CAP" || true)
  [ -n "$EP" ] && break
  sleep 0.3
done
[ -z "$EP" ] && { echo "ERROR: no SSE endpoint event from $BASE/sse"; exit 1; }
MSG="$BASE$EP"
echo "session: $MSG"

# Auth headers ride on the POST that carries the tool call (what the server reads).
HDRS=()
[ -n "$EMAIL" ]  && HDRS+=(-H "x-user-email: $EMAIL")
[ -n "$SECRET" ] && HDRS+=(-H "x-research-secret: $SECRET")
post() {
  curl -s -o /dev/null -X POST "$MSG" -H 'Content-Type: application/json' \
    ${HDRS[@]+"${HDRS[@]}"} -d "$1"
}

# MCP handshake, then call the tool with empty arguments.
post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl-gate-test","version":"0"}}}'
sleep 1
post '{"jsonrpc":"2.0","method":"notifications/initialized"}'
sleep 0.5
post '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"research_and_ingest_topic","arguments":{}}}'
sleep 2

echo "----- tool result -----"
grep '^data: ' "$CAP" \
  | grep -Eo 'restricted to system administrators|provide either a `query`' \
  | tail -1 \
  || { echo "(no recognizable result — raw tail:)"; tail -3 "$CAP"; }
