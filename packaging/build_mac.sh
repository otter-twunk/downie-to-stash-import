#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf .venv-build
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pip install pyinstaller

pyinstaller packaging/downie_stash.spec

echo "Build complete: dist/Downie to Stash Import Helper.app"
