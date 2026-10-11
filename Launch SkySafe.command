#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
print "SkySafe dashboard: http://127.0.0.1:5050"
print "Keep this window open while using the dashboard. Press Control-C to stop."
exec .venv/bin/python -m dashboard.app "$@"
