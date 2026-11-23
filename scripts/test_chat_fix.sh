#!/usr/bin/env bash
# Verifies the chat-onboarding fix live against production, end-to-end.
set -euo pipefail
BASE="https://stitchbase.duckdns.org"

echo "==> Uploading sample design..."
SESSION_ID=$(curl -sf -F "svg_file=@BE/test-fixtures/sample.svg" "$BASE/api/v1/sessions" \
  | python -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "session_id=$SESSION_ID"

echo "==> Asking a fabric-specific question as the FIRST chat message (the reported bug case)..."
curl -sf -X POST "$BASE/api/v1/sessions/$SESSION_ID/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "How should I fix this for cotton?"}' \
  | python -c "
import sys, json
reply = json.load(sys.stdin)['content']
print('--- reply ---')
print(reply)
print('--- checks ---')
bad = ['what are you trying to achieve', 'what garment is this', 'run a preflight check']
lowered = reply.lower()
hits = [p for p in bad if p in lowered]
print('FAIL: onboarding phrases found:', hits) if hits else print('PASS: no onboarding phrases')
"
