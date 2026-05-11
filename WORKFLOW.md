# Workflow and Design Justification

## Package structure

- `src/downie_to_stash/core.py` — conversion engine
- `src/downie_to_stash/cli.py` — CLI entrypoint
- `src/downie_to_stash/gui_app.py` — Tkinter GUI entrypoint
- `tests/` — unit/integration/CLI tests
- `.github/workflows/ci.yml` — Ruff, Mypy, Pytest matrix CI

## Goals

- Parse one Downie JSON root recursively.
- Index one or more media roots.
- Match JSON records to local media using heuristic scoring.
- Emit Stash-compatible scene JSON files for Stash JSON import.
- Never write directly to Stash SQLite.

## High-level workflow

1. Parse Downie JSON files (`*.json`) and extract title, URLs, and date fields.
2. Index media files by extension (`VIDEO_EXTS`) and normalized naming tokens.
3. Generate candidates per Downie item and score each candidate.
4. Accept only high-confidence matches (`min_score`, `ambiguity_gap`).
5. Write:
   - `output/scenes/*.json`
   - `output/report.json`
   - `output/unmatched.json`
   - `output/ambiguous.json`

## Why JSON import instead of DB writes

Stash's JSON import format is documented and stable compared with direct schema coupling. Using the documented task format keeps this project aligned with supported Stash behavior.

- https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
- https://docs.stashapp.cc/in-app-manual/tasks/

## Matching strategy

The matcher combines:

- exact normalized stem/title matches
- similarity scoring
- token overlap scoring
- parent/grandparent folder hints

Ambiguous or low-confidence results are recorded rather than force-matched.

## GUI/CLI behavior

- GUI always runs conversion in a worker thread.
- GUI includes progress indicator, clearable log, and summary panel.
- CLI supports `--version`, `--verbose`, final summary table, and non-zero exit when unmatched/ambiguous items remain.
