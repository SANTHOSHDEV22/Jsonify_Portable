#!/usr/bin/env bash
# ============================================================
#  Jsonify - development launcher (macOS / Linux / Git Bash)
#
#    ./run_dev.sh            create venv + install (first run), then start the app
#    ./run_dev.sh file.json  start the app and open a file
#    ./run_dev.sh test       run the test suite (extra pytest args allowed)
#    ./run_dev.sh check      ruff + format check + mypy + tests
#    ./run_dev.sh cli ...    run the command-line interface
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x venv/bin/python ] && [ ! -x venv/Scripts/python.exe ]; then
    echo "Creating virtual environment in ./venv ..."
    python3 -m venv venv 2>/dev/null || python -m venv venv
fi

if [ -x venv/bin/python ]; then PY=venv/bin/python; else PY=venv/Scripts/python.exe; fi

"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -e ".[dev]"

case "${1:-}" in
    test)  shift; exec "$PY" -m pytest "$@" ;;
    check)
        "$PY" -m ruff check .
        "$PY" -m ruff format --check .
        "$PY" -m mypy
        exec "$PY" -m pytest -q
        ;;
    cli)   shift; exec "$PY" -m jsonify "$@" ;;
    *)     exec "$PY" -m jsonify "$@" ;;
esac
