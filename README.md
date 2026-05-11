# Downie → Stash Import Helper

[![CI](https://github.com/otter-twunk/downie-to-stash-import/actions/workflows/ci.yml/badge.svg)](https://github.com/otter-twunk/downie-to-stash-import/actions/workflows/ci.yml)

Convert a folder of Downie metadata JSON files into a Stash-compatible scene import bundle.

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/otter-twunk/downie-to-stash-import.git
cd downie-to-stash-import
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Development tooling:

```bash
pip install -e ".[dev]"
```

## Usage – GUI

```bash
python -m downie_to_stash.gui_app
# or
 downie-stash-gui
```

## Usage – CLI

```bash
downie-stash-cli \
  --json-root /path/to/downie-json \
  --media-root /path/to/media-1 \
  --media-root /path/to/media-2 \
  --output /path/to/stash-import
```

Important flags:

- `--dry-run` analyze only (no `scenes/` files written)
- `--min-score` and `--ambiguity-gap` tune matching strictness
- `--no-date` skip mapping Downie timestamps to scene date
- `--verbose` / `-v` print all logs
- `--version` print version and exit

## Building the macOS app

```bash
./packaging/build_mac.sh
```

This runs PyInstaller with `packaging/downie_stash.spec` and outputs:

- `dist/DownieToStash.app`

## Importing into Stash

1. Ensure Stash has already scanned your media files.
2. Run this tool to generate `scenes/` plus reports.
3. Use Stash JSON import task with the generated bundle.

Reference docs:

- https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
- https://docs.stashapp.cc/in-app-manual/tasks/

## Troubleshooting

- **Low match rates**
  - Check filename/title naming consistency.
  - Lower `--min-score` carefully if matches are too strict.
- **Ambiguous matches**
  - Inspect `ambiguous.json`.
  - Rename media files or remove duplicate names to improve confidence.
- **No media indexed**
  - Confirm files use supported extensions in `VIDEO_EXTS` (`src/downie_to_stash/core.py`).
- **Import not working in Stash**
  - Ensure Stash has scanned files before running JSON import.
