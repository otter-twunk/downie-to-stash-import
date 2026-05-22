# Downie to Stash Import Helper

[![CI](https://github.com/otter-twunk/downie-to-stash-import/actions/workflows/ci.yml/badge.svg)](https://github.com/otter-twunk/downie-to-stash-import/actions/workflows/ci.yml)

Convert a folder of [Downie](https://software.charliemonroe.net/downie/) metadata JSON files into a [Stash](https://stashapp.cc)-compatible scene import bundle.

## How it works

Downie saves a `.json` sidecar alongside each downloaded video. This tool reads those JSON files, matches each one to the corresponding media file on disk, and writes Stash scene JSON files that Stash can import via its built-in **JSON import** task.

Nothing is written directly to the Stash database — only plain JSON files are produced.

## Requirements

- Python 3.10 or later
- Stash must have already **scanned** your media library before you run the import

## Installation

```bash
git clone https://github.com/otter-twunk/downie-to-stash-import.git
cd downie-to-stash-import
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Development tooling (linters, type checker, tests):

```bash
pip install -e ".[dev]"
```

## Usage — CLI

```bash
downie-stash-cli \
  --json-root /path/to/downie-json \
  --media-root /path/to/media \
  --output /path/to/stash-import
```

Repeat `--media-root` for multiple library roots:

```bash
downie-stash-cli \
  --json-root ~/Downloads/Downie \
  --media-root /Volumes/Media/site1 \
  --media-root /Volumes/Media/site2 \
  --output ~/Desktop/stash-import
```

### All CLI flags

| Flag | Default | Description |
|---|---|---|
| `--json-root` | *(required)* | Folder containing Downie JSON sidecars (searched recursively) |
| `--media-root` | *(required, repeatable)* | Media library root(s) to search for matching video files |
| `--output` / `-o` | `stash-import` | Output folder for the generated Stash import bundle |
| `--details` | `Imported from Downie metadata` | Text added to the `details` field of each scene |
| `--min-score` | `60.0` | Minimum match score to accept (lower = more permissive) |
| `--ambiguity-gap` | `7.5` | Minimum score gap between top two candidates (lower = more permissive) |
| `--allow-stream-url` | off | Fall back to Downie's direct media URL when no page URL is present |
| `--no-date` | off | Skip mapping Downie timestamps to the scene `date` field |
| `--dry-run` | off | Score and report without writing any `scenes/` JSON files |
| `--path-map SOURCE=TARGET` | *(repeatable)* | Rewrite media paths in exported JSON (see Docker note below) |
| `--verbose` / `-v` | off | Print every log line (default shows only matches, skips, and errors) |
| `--version` | | Print version and exit |

### Output files

The tool writes four files into the output folder:

| File | Contents |
|---|---|
| `scenes/*.json` | One Stash scene JSON file per matched Downie item |
| `report.json` | Full run summary with all matched items and their scores |
| `unmatched.json` | Items with no candidate above `--min-score` |
| `ambiguous.json` | Items where two or more candidates scored too close together |

## Usage — GUI

```bash
downie-stash-gui
# or: python -m downie_to_stash.gui_app
```

The GUI exposes the same options as the CLI in a Tkinter window. Conversion runs in a background thread so the UI stays responsive. A progress indicator is shown during the run and the log can be cleared between runs.

## Importing into Stash

1. **Scan first.** Run Stash's library scan so it has indexed your media files.
2. **Run this tool** to generate the import bundle.
3. In Stash, go to **Settings → Tasks → Import** and point it at the `scenes/` folder inside the output directory.

Stash matches the imported scene to an existing file by the `files` path. The path in the exported JSON must exactly match what Stash indexed.

Reference:
- [Stash JSON import spec](https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/)
- [Stash tasks](https://docs.stashapp.cc/in-app-manual/tasks/)

### Docker / path remapping

If Stash runs in Docker (or sees your media at a different mount point), the paths this tool records must match the paths inside the container, not on the host.

Use `--path-map HOST_PATH=CONTAINER_PATH`:

```bash
downie-stash-cli \
  --json-root ~/Downloads/Downie \
  --media-root /Volumes/Media \
  --output ~/Desktop/stash-import \
  --path-map /Volumes/Media=/data/media
```

Multiple `--path-map` entries are resolved longest-prefix-first.

## Building the macOS app

```bash
./packaging/build_mac.sh
```

This creates a fresh `.venv-build`, installs the package, runs PyInstaller with `packaging/downie_stash.spec`, and outputs:

- `dist/Downie to Stash Import Helper.app`

## Troubleshooting

**Low match rate**
- Check that Downie JSON filenames and video filenames share recognisable words.
- Lower `--min-score` (e.g. `--min-score 45`) to allow weaker matches.
- Use `--verbose` to see per-item scoring.

**Many ambiguous items**
- Inspect `ambiguous.json` for the two competing candidates.
- Rename duplicate video files or remove lower-quality copies to eliminate ambiguity.
- Raise `--ambiguity-gap` to require a larger score gap.

**No media indexed**
- Confirm your video files use extensions in `VIDEO_EXTS` (defined in `src/downie_to_stash/core.py`).

**Import not working in Stash**
- Stash must have scanned the files *before* the import runs.
- The `files` path in each exported JSON must exactly match the path Stash stored. Use `--path-map` if the paths differ.
- Check `unmatched.json` and `ambiguous.json` for items that were not exported.
