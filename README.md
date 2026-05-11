# Downie → Stash Import Helper

Convert a folder of Downie metadata JSON files into a Stash-compatible scene
import bundle, with optional GUI.

The tool:

- parses Downie JSON files (one folder in)
- searches one or more media library roots for video files
- matches each Downie JSON to a media file using filename + title heuristics
- writes Stash scene JSON into `scenes/`, plus `report.json`,
  `unmatched.json`, and `ambiguous.json`

You can then import the generated bundle into Stash using its JSON import
task. See the Stash docs for the scene JSON format and import behavior.
https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/

## Features

- Supports **one JSON root folder** and **multiple media roots**
- Heuristic matching based on:
  - normalized filename
  - normalized title
  - token overlap
  - folder name hints
- Safety controls:
  - minimum match score threshold
  - ambiguity gap between top candidates
  - dry-run mode
- GUI front-end with Tkinter
- Optional CLI entrypoint for automation

## Installation

Requires Python 3.10+.

On macOS, use a Python from python.org or Homebrew so you get a modern
Tk installation for the GUI.

```bash
git clone https://github.com/otter-twunk/downie-to-stash-import.git
cd downie-to-stash-import
python3 -m venv .venv
source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
```

## Usage – GUI

```bash
python3 gui_app.py
```

Then:

1. Select your **Downie JSON folder**.
2. Add one or more **media roots** (Stash library folders).
3. Select an **output folder** (where the Stash import bundle will be written).
4. Optionally adjust:
   - min score
   - ambiguity gap
   - whether to include date
   - whether to use the Downie media URL as a fallback
5. Click **Run**.

The app will:

- index media
- match each JSON to a media file
- write scene JSON into `output/scenes/`
- write `report.json`, `unmatched.json`, and `ambiguous.json` at the
  output root

## Usage – CLI

```bash
python3 cli.py \
  --json-root /path/to/downie-json \
  --media-root /path/to/media-1 \
  --media-root /path/to/media-2 \
  --output /path/to/stash-import
```

Important flags:

- `--dry-run` to analyze only (populate report/unmatched/ambiguous without
  writing scene JSON).
- `--min-score` and `--ambiguity-gap` to tune match strictness.
- `--no-date` to skip mapping Downie timestamps to Stash `date`.

## Importing into Stash

After running the tool:

1. Go to Stash.
2. Use the JSON import task and point it at the output
   folder or copy the `scenes/` JSON into your configured metadata
   directory.
3. Run the import; Stash will read the scene JSON and attach metadata to
   the files matching the paths in `files[]`.

Refer to Stash’s JSON specification and tasks docs for current details:
- https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
- https://docs.stashapp.cc/in-app-manual/tasks/
