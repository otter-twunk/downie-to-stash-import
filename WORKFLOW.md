# Workflow and Design

## Package layout

```
src/downie_to_stash/
  __init__.py      version constant
  core.py          conversion engine (parsing, indexing, matching, output)
  cli.py           argparse CLI entrypoint
  gui_app.py       Tkinter GUI entrypoint

tests/
  conftest.py      shared fixtures (tmp JSON root, media root, output root)
  test_core_unit.py      unit tests for pure functions
  test_core_integration.py  end-to-end run_conversion tests
  test_cli.py      CLI invocation tests

packaging/
  build_mac.sh     macOS .app build script (PyInstaller)
  downie_stash.spec  PyInstaller spec for the GUI bundle

.github/workflows/ci.yml  Ruff + Mypy + Pytest matrix (3.10–3.13)
```

## Goals

- Parse one Downie JSON root recursively.
- Index one or more media roots.
- Match each Downie JSON record to a local media file using heuristic scoring.
- Write Stash-compatible scene JSON files for import via Stash's JSON import task.
- Never write directly to the Stash SQLite database.

## Step-by-step workflow

1. **Parse JSON.** Walk `json_root` recursively and call `parse_downie_json` on each `.json` file. Records with no `__type` field or with `__type` containing "Downie" are kept; anything else is skipped (these are typically unrelated JSON files in the same folder).

2. **Index media.** Walk each `media_root` recursively and build a `MediaIndex` — three lookup tables keyed by normalised stem, parent folder name, and individual tokens. The index stores the `stash_path` (post-mapping path) separately from `path` (absolute host path), so symlinks are preserved and Docker path remaps are applied once at index time.

3. **Candidate selection.** For each Downie record, `find_candidates` assembles a candidate set by:
   - Exact normalised-stem lookup
   - Token-bucket lookup (tokens ≥ 4 chars)
   - Substring fallback scan (capped at 50 results) when fewer than 10 candidates exist

4. **Scoring.** `score_candidate` assigns points for:
   - Exact normalised stem or title match (70 / 55 pts)
   - Sequence similarity against stem and title (up to 30 pts)
   - Jaccard token overlap (up to 20 pts)
   - Referer URL hints matching parent/grandparent folder names (8 / 4 pts)
   - File size > 50 MB (2 pts — minor tiebreaker)

5. **Threshold checks.** `choose_best_match` rejects any top candidate whose score is below `min_score`, and rejects the top candidate as ambiguous when the gap between first and second place is below `ambiguity_gap`.

6. **Output.** For each matched record, `build_scene_payload` assembles a Stash scene JSON payload and writes it to `scenes/{title}.{n:05d}.json`. Three summary files are always written regardless of `--dry-run`: `report.json`, `unmatched.json`, `ambiguous.json`.

## Why JSON import instead of direct DB writes

Stash's JSON import format is documented and versioned. Writing directly to the SQLite schema is fragile across Stash upgrades. Using the supported import task keeps this tool decoupled from Stash internals.

- https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
- https://docs.stashapp.cc/in-app-manual/tasks/

## Scene JSON format

Each file in `scenes/` matches the Stash scene import schema:

```json
{
  "title": "Scene Title",
  "files": ["/absolute/path/to/file.mp4"],
  "details": "Imported from Downie metadata",
  "created_at": "2024-01-02T12:00:00+00:00",
  "updated_at": "2024-01-02T12:00:00+00:00",
  "url": "https://source.example.com/scene",
  "date": "2024-01-02"
}
```

`url` and `date` are omitted when not available or when `--no-date` / no referer is set.

## Normalisation

`normalize_text` lowercases, strips punctuation, removes embedded URLs, and drops tokens in `SITE_NOISE`. This is applied to both Downie titles/stems and media filenames before any comparison, so differences in punctuation, capitalisation, and site-branding suffixes do not affect matching.

`clean_title` additionally strips common Downie title suffixes (site watermark patterns) before the cleaned title is stored in the scene JSON.

## Path handling

- Media files are indexed using `os.path.abspath` (symlinks not resolved) so the exported path reflects the path Stash would have indexed.
- `apply_path_mappings` remaps host paths to container paths at index time. Mappings are sorted longest-prefix-first to avoid partial-prefix collisions.
- On Windows-style target roots (backslash separator, no forward slash), `ntpath.join` is used; otherwise `posixpath.join` is used. This allows correct path construction when running on macOS/Linux but producing Docker-Linux paths.

## GUI and CLI behaviour

- The GUI runs `run_conversion` in a daemon thread, posting log lines and the final summary back to the main thread via `widget.after(0, ...)`.
- The CLI filters log output to MATCH/SKIP/Done/Error lines unless `--verbose` is set, then prints a Unicode summary table.
- The CLI exits with code 0 on a clean run, 1 when there are unmatched or ambiguous items, and 2 on a configuration error (invalid paths, bad `--path-map`).
