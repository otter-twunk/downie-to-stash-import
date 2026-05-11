#!/usr/bin/env python3
"""CLI entrypoint for Downie → Stash conversion.

Example:

  python cli.py \
    --json-root /path/to/downie-json \
    --media-root /media/stash/library \
    --output /tmp/stash-import
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core import ConversionConfig, run_conversion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Downie JSON into a Stash import bundle.",
    )
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
    args = parser.parse_args()

    config = ConversionConfig(
        json_root=Path(args.json_root),
        media_roots=[Path(p) for p in args.media_root],
        output_root=Path(args.output),
        details_text=args.details,
        min_score=args.min_score,
        ambiguity_gap=args.ambiguity_gap,
        allow_stream_url=args.allow_stream_url,
        include_date=not args.no_date,
        dry_run=args.dry_run,
    )

    def log(msg: str) -> None:
        print(msg, flush=True)

    run_conversion(config, log=log)


if __name__ == "__main__":
    main()
