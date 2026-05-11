#!/usr/bin/env python3
"""CLI entrypoint for Downie → Stash conversion."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from downie_to_stash.core import ConversionConfig, run_conversion

VERSION = "0.1.0"


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Downie JSON into a Stash import bundle.",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--json-root", required=True, help="Folder with Downie JSON.")
    parser.add_argument(
        "--media-root",
        action="append",
        required=True,
        help="Media library root (repeat for multiple).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="stash-import",
        help="Output folder for Stash import bundle.",
    )
    parser.add_argument(
        "--details",
        default="Imported from Downie metadata",
        help="Details text to include on scenes.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=60.0,
        help="Minimum score to accept a match.",
    )
    parser.add_argument(
        "--ambiguity-gap",
        type=float,
        default=7.5,
        help="Minimum score difference between top candidates.",
    )
    parser.add_argument(
        "--allow-stream-url",
        action="store_true",
        help="Use Downie media URL if no referer/source page URL exists.",
    )
    parser.add_argument(
        "--no-date",
        action="store_true",
        help="Do not map Downie timestamps to Stash scene date.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only; do not write scene JSON files.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print all log lines.",
    )
    return parser


def _render_summary_table(summary: dict[str, object]) -> str:
    rows = [
        ("Media indexed", _as_int(summary.get("media_indexed", 0))),
        ("Downie JSON parsed", _as_int(summary.get("downie_json_parsed", 0))),
        ("Matched", _as_int(summary.get("matched_count", 0))),
        ("Unmatched", _as_int(summary.get("unmatched_count", 0))),
        ("Ambiguous", _as_int(summary.get("ambiguous_count", 0))),
    ]

    metric_width = max(len("Metric"), *(len(name) for name, _ in rows))
    count_width = max(len("Count"), *(len(str(count)) for _, count in rows))

    top = f"┌{'─' * (metric_width + 2)}┬{'─' * (count_width + 2)}┐"
    header = f"│ {'Metric'.ljust(metric_width)} │ {'Count'.ljust(count_width)} │"
    sep = f"├{'─' * (metric_width + 2)}┼{'─' * (count_width + 2)}┤"
    lines = [
        f"│ {name.ljust(metric_width)} │ {str(count).rjust(count_width)} │"
        for name, count in rows
    ]
    bottom = f"└{'─' * (metric_width + 2)}┴{'─' * (count_width + 2)}┘"
    return "\n".join([top, header, sep, *lines, bottom])


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    config = ConversionConfig(
        json_root=Path(args.json_root),
        media_roots=[Path(path) for path in args.media_root],
        output_root=Path(args.output),
        details_text=args.details,
        min_score=args.min_score,
        ambiguity_gap=args.ambiguity_gap,
        allow_stream_url=args.allow_stream_url,
        include_date=not args.no_date,
        dry_run=args.dry_run,
    )

    def log(message: str) -> None:
        if args.verbose or any(token in message for token in ("MATCH", "SKIP", "Done", "Error")):
            print(message, flush=True)

    summary = run_conversion(config, log=log)
    print(_render_summary_table(summary), flush=True)

    has_issues = _as_int(summary.get("unmatched_count", 0)) > 0 or _as_int(summary.get("ambiguous_count", 0)) > 0
    return 1 if has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
