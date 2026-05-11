# Workflow and Design Justification

## Package structure

- `src/downie_to_stash/core.py` - conversion engine
- `src/downie_to_stash/cli.py` - CLI entrypoint
- `src/downie_to_stash/gui_app.py` - Tkinter GUI entrypoint
- `tests/` - unit, integration, and CLI tests
- `.github/workflows/ci.yml` - Ruff, Mypy, and Pytest matrix CI

## Goals

- Parse one Downie JSON root recursively.
- Index one or more media roots.
- Match JSON records to local media using heuristic scoring.
- Emit Stash-compatible scene JSON files for the Stash JSON import task.
- Never write directly to the Stash SQLite database.

## High-level workflow

1. Parse Downie JSON files and extract title, URLs, and date fields.
2. Index media files by extension (`VIDEO_EXTS`) and normalized naming tokens.
3. Generate candidate media matches for each Downie item.
4. Score each candidate and keep only high-confidence matches.
5. Write:
   - `output/scenes/*.json`
   - `output/report.json`
   - `output/unmatched.json`
   - `output/ambiguous.json`

The generated scene payloads include `files`, `created_at`, and `updated_at`, which aligns with the current Stash scene JSON schema.

## Why JSON import instead of DB writes

Stash's JSON import format is documented and more stable than writing directly against the database schema. Using the supported import task keeps this tool aligned with Stash's intended workflow.

- https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
- https://docs.stashapp.cc/in-app-manual/tasks/

## Matching strategy

The matcher combines:

- exact normalized stem or title matches
- similarity scoring
- token overlap scoring
- parent and grandparent folder hints

Ambiguous or low-confidence results are recorded instead of force-matched.

## GUI and CLI behavior

- GUI always runs conversion in a worker thread.
- GUI includes a progress indicator, clearable log, results summary, and output-folder opener.
- CLI supports `--version`, `--verbose`, a final summary table, and a non-zero exit when unmatched or ambiguous items remain.
