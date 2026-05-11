# Workflow and Design Justification

This document explains how the tool works end-to-end and why it is designed
this way.

## Goals

- Take **one folder of Downie JSON** as input.
- Search across **one or more media roots**.
- Automatically match metadata to media files.
- Produce a **Stash-compatible scene import bundle** that can be ingested
  via Stash’s JSON import task.

The design explicitly avoids writing directly to the Stash database and
instead targets the documented JSON import format.
https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/

## High-Level Workflow

1. **Parse Downie JSON**
   - Recursively walk `json_root` for `*.json`.
   - For each file:
     - parse JSON
     - confirm it looks like Downie metadata (`__type` contains "Downie")
     - extract:
       - `title`
       - `referer` (source page URL)
       - `url` (media URL, usually `m3u8`)
       - `creationDate` / `prepareDate`
       - `previewImageURL`
   - Clean up the title into `title_clean` using heuristics (strip
     repeated site boilerplate etc.).

2. **Index media**
   - Recursively walk each `media_root`.
   - Include only files with known video extensions.
   - For each, compute:
     - absolute path
     - raw stem
     - normalized stem
     - parent and grandparent names (and normalized variants)
     - file size
   - Store records in `MediaIndex`, indexed by:
     - normalized stem
     - normalized parent
     - individual tokens from the normalized stem.

3. **Candidate generation**
   - For each Downie record:
     - start with any media record whose **normalized stem matches** the
       Downie JSON stem
     - expand by shared tokens between normalized title and normalized
       stem
     - finally, if the candidate list is still small, add any media whose
       normalized stem contains the normalized title or vice versa.

4. **Scoring and selection**
   - For each candidate, compute a heuristic score:
     - +70 for exact normalized stem match
     - +55 for exact normalized title match
     - + up to 30 based on string similarity between normalized title and
       filename
     - + up to 20 for token overlap
     - + small bonuses for parent/grandparent folder hints
     - + tiny bonus for larger file size (avoid tiny clips)
   - Sort candidates by score.
   - Apply two safety checks:
     - **min_score**: reject all matches if the top score is below the
       threshold.
     - **ambiguity_gap**: reject matches if the top two scores are too
       close, to avoid ambiguous assignments.
   - If there is no acceptable match:
     - record in `unmatched` or `ambiguous` with a summary of candidates.
   - If there is a clear match:
     - build a scene payload.

5. **Scene payloads**
   - For each accepted match, build a minimal Stash scene JSON:

     ```json
     {
       "title": "Cleaned title",
       "url": "https://source-site/video/...",
       "files": ["/absolute/path/to/media/file.mp4"],
       "details": "Imported from Downie metadata",
       "date": "YYYY-MM-DD"  // optional
     }
     ```

   - Date is only included if explicitly enabled and if Downie metadata
     contained a parseable timestamp.

6. **Output bundle**
   - All scene JSON files go into `output_root/scenes/`.
   - `report.json` contains:
     - summary counts
     - which JSON files matched which media
   - `unmatched.json` includes all Downie records where no candidate met
     the thresholds.
   - `ambiguous.json` includes Downie records where several candidates
     scored similarly.

7. **Import into Stash**
   - Stash’s import task reads the scene JSON files and attaches
     metadata to the files referenced in `files[]`, following the JSON
     spec and tasks behavior described in the Stash docs.
   - See:
     - https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
     - https://docs.stashapp.cc/in-app-manual/tasks/

## Why JSON Import Instead of Direct DB Writes

- Stash’s database schema for scenes, files, and link tables can change
  between versions.
- Using the documented JSON import format and tasks keeps this tool
  aligned with Stash’s supported interfaces, reducing breakage risk.
- Stash already expects scene metadata to be imported from JSON files, so
  this workflow integrates cleanly with existing tasks.

## Why a Separate Engine (`core.py`)

- The same engine can be driven by:
  - a GUI (Tkinter)
  - a CLI
  - future UIs (web, Tauri, etc.)
- Tests can be written against `core.run_conversion()` without needing
  any UI layer.
- GitHub Copilot can safely refactor internal functions without touching
  the GUI wiring.

## Matching Strategy Justification

- **Default strictness**:
  - The tool prefers to mark items as `unmatched` or `ambiguous` rather
    than risk binding metadata to the wrong file.
- **Heuristic scoring**:
  - Filename and title are usually similar for media downloaded via
    Downie and then organized for Stash.
  - Token overlap plus folder names give a robust signal while still
    being cheap to compute.
- **Configurable thresholds**:
  - Different libraries can have different naming conventions.
  - Exposing `min_score` and `ambiguity_gap` lets the user tune false
    positive vs. false negative tolerance without modifying code.

## Future Extensions

These are recommended next steps for improvement:

- Add a small UI on top of `unmatched.json` and `ambiguous.json` to allow
  manual resolution (pick media for a given Downie record).
- Add additional parsers for other metadata formats.
- Add Stash API integration to trigger import jobs directly from the app.
- Add automated tests for `core.py` (normalization, matching, end-to-end
  dry runs).
- Add packaging via PyInstaller to ship a macOS `.app`.
