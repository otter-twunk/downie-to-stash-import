#!/usr/bin/env python3
"""Core batch engine for converting Downie JSON into Stash scene import bundles.

This module is used by both the CLI and GUI frontends. It:
- parses Downie metadata JSON files from a root folder
- scans one or more media roots for video files
- matches JSON records to media files using filename + title heuristics
- emits Stash-compatible scene JSON files into an output bundle

Stash import docs: https://docs.stashapp.cc/in-app-manual/tasks/jsonspec/
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Optional

VIDEO_EXTS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
}

SITE_NOISE = {
    "justthegays",
    "justthegays.tv",
    "porn",
    "video",
    "official",
    "tv",
    "www",
}


def normalize_text(value: str) -> str:
    """Lowercase, strip punctuation/URLs, remove common noise tokens."""
    value = value or ""
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"https?://", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = [t for t in value.split() if t and t not in SITE_NOISE]
    return " ".join(tokens).strip()


def tokenize(value: str) -> set[str]:
    return set(normalize_text(value).split())


def clean_title(title: str) -> str:
    """Clean noisy Downie titles into something usable as a scene title."""
    if not title:
        return "Untitled"
    t = re.sub(r"\s+", " ", title).strip()
    # Strip repeated JustTheGays boilerplate
    t = re.sub(
        r"\s+-\s+\|\s+JustTheGays(?:\s+-\s+justthegays\.tv)+$",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(r"(?:\s*-\s*justthegays\.tv)+$", "", t, flags=re.I)
    t = re.sub(r"\s+-\s+\|\s*$", "", t)
    return t.strip(" -|") or "Untitled"


def sanitize_filename(name: str) -> str:
    """Make a safe filename based on the title."""
    name = re.sub(r'[\\/:*?"<>|]+', "-", name)
    name = re.sub(r"\s+", " ", name).strip()
    return (name[:180] or "scene").rstrip(". ")


def extract_date(meta: dict) -> Optional[str]:
    """Pull a date string from Downie metadata, normalized to YYYY-MM-DD."""
    for key in ("creationDate", "prepareDate"):
        value = meta.get(key)
        if not value:
            continue
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).date().isoformat()
        except Exception:
            continue
    return None


@dataclass
class DownieRecord:
    json_path: str
    stem: str
    title_raw: str
    title_clean: str
    title_norm: str
    stem_norm: str
    referer: Optional[str]
    media_url: Optional[str]
    preview_image: Optional[str]
    date: Optional[str]


@dataclass
class MediaRecord:
    path: str
    stem: str
    stem_norm: str
    parent_name: str
    parent_norm: str
    grandparent_name: str
    grandparent_norm: str
    ext: str
    size: int


@dataclass
class MatchResult:
    json_path: str
    matched: bool
    reason: str
    score: float
    title: str
    scene_url: Optional[str]
    video_path: Optional[str]
    output_json: Optional[str]
    candidate_count: int


@dataclass
class ConversionConfig:
    json_root: Path
    media_roots: list[Path]
    output_root: Path
    details_text: str
    min_score: float
    ambiguity_gap: float
    allow_stream_url: bool
    include_date: bool
    dry_run: bool


class MediaIndex:
    """Index of media files under one or more library roots."""

    def __init__(self) -> None:
        self.records: list[MediaRecord] = []
        self.by_stem: dict[str, list[MediaRecord]] = defaultdict(list)
        self.by_parent: dict[str, list[MediaRecord]] = defaultdict(list)
        self.by_tokens: dict[str, list[MediaRecord]] = defaultdict(list)

    def add(self, record: MediaRecord) -> None:
        self.records.append(record)
        self.by_stem[record.stem_norm].append(record)
        if record.parent_norm:
            self.by_parent[record.parent_norm].append(record)
        for token in set(record.stem_norm.split()):
            if len(token) >= 3:
                self.by_tokens[token].append(record)

    def build_from_roots(
        self,
        roots: list[Path],
        log: Callable[[str], None],
    ) -> None:
        for root in roots:
            log(f"Scanning media root: {root}")
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in VIDEO_EXTS:
                    continue
                parent = path.parent.name
                grandparent = (
                    path.parent.parent.name
                    if path.parent.parent != path.parent
                    else ""
                )
                record = MediaRecord(
                    path=str(path.resolve()),
                    stem=path.stem,
                    stem_norm=normalize_text(path.stem),
                    parent_name=parent,
                    parent_norm=normalize_text(parent),
                    grandparent_name=grandparent,
                    grandparent_norm=normalize_text(grandparent),
                    ext=path.suffix.lower(),
                    size=path.stat().st_size,
                )
                self.add(record)
        log(f"Indexed {len(self.records)} media files")


def parse_downie_json(path: Path) -> Optional[DownieRecord]:
    """Parse a Downie metadata JSON file into an internal record."""
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    dtype = str(meta.get("__type", ""))
    if dtype and "Downie" not in dtype:
        return None
    title_raw = meta.get("title") or path.stem
    title_clean = clean_title(title_raw)
    return DownieRecord(
        json_path=str(path.resolve()),
        stem=path.stem,
        title_raw=title_raw,
        title_clean=title_clean,
        title_norm=normalize_text(title_clean),
        stem_norm=normalize_text(path.stem),
        referer=meta.get("referer")
        or meta.get("webpage_url")
        or meta.get("sourceURL"),
        media_url=meta.get("url"),
        preview_image=meta.get("previewImageURL"),
        date=extract_date(meta),
    )


def score_candidate(
    downie: DownieRecord,
    media: MediaRecord,
) -> tuple[float, list[str]]:
    """Compute a heuristic match score between a Downie record and a media file."""
    score = 0.0
    reasons: list[str] = []

    if media.stem_norm == downie.stem_norm and media.stem_norm:
        score += 70
        reasons.append("exact normalized stem match")

    if media.stem_norm == downie.title_norm and media.stem_norm:
        score += 55
        reasons.append("exact normalized title match")

    title_ratio = SequenceMatcher(
        None, downie.title_norm, media.stem_norm
    ).ratio()
    stem_ratio = SequenceMatcher(
        None, downie.stem_norm, media.stem_norm
    ).ratio()
    best_ratio = max(title_ratio, stem_ratio)
    score += best_ratio * 30
    if best_ratio >= 0.75:
        reasons.append(f"strong similarity {best_ratio:.2f}")

    dtokens = tokenize(downie.title_clean) | tokenize(downie.stem)
    mtokens = tokenize(media.stem)
    if dtokens and mtokens:
        overlap = len(dtokens & mtokens)
        union = len(dtokens | mtokens)
        jaccard = overlap / union if union else 0
        score += jaccard * 20
        if overlap:
            reasons.append(f"token overlap {overlap}")

    hint_tokens = set()
    if downie.referer:
        hint_tokens |= tokenize(downie.referer)
    if hint_tokens & tokenize(media.parent_name):
        score += 8
        reasons.append("parent folder hint")
    if hint_tokens & tokenize(media.grandparent_name):
        score += 4
        reasons.append("grandparent folder hint")

    if media.size > 50 * 1024 * 1024:
        score += 2  # prefer non-tiny files

    return score, reasons


def choose_best_match(
    downie: DownieRecord,
    candidates: list[MediaRecord],
    min_score: float,
    ambiguity_gap: float,
) -> tuple[
    Optional[tuple[float, MediaRecord, list[str]]],
    Optional[str],
    list[tuple[float, MediaRecord, list[str]]],
]:
    """Choose the best candidate, enforcing thresholds for quality and ambiguity."""
    if not candidates:
        return None, "no candidates", []

    scored: list[tuple[float, MediaRecord, list[str]]] = []
    for cand in candidates:
        score, reasons = score_candidate(downie, cand)
        scored.append((score, cand, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0]
    second = scored[1] if len(scored) > 1 else None

    if top[0] < min_score:
        return None, f"best score {top[0]:.1f} < threshold {min_score}", scored[:10]

    if second and (top[0] - second[0]) < ambiguity_gap:
        return None, f"ambiguous ({top[0]:.1f} vs {second[0]:.1f})", scored[:10]

    return top, None, scored[:10]


def build_scene_payload(
    downie: DownieRecord,
    matched_media: MediaRecord,
    include_date: bool,
    details_text: str,
    allow_stream_url: bool,
) -> dict:
    """Build a Stash scene JSON payload from a Downie record + matched media."""
    scene_url = downie.referer or (downie.media_url if allow_stream_url else None)
    payload: dict = {
        "title": downie.title_clean,
        "url": scene_url,
        "files": [matched_media.path],
        "details": details_text,
    }
    if include_date and downie.date:
        payload["date"] = downie.date
    return payload


def find_candidates(index: MediaIndex, downie: DownieRecord) -> list[MediaRecord]:
    """Collect a candidate set of media files for a given Downie record."""
    candidates: list[MediaRecord] = []
    seen: set[str] = set()

    def push(items: list[MediaRecord]) -> None:
        for item in items:
            key = item.path
            if key not in seen:
                seen.add(key)
                candidates.append(item)

    if downie.stem_norm in index.by_stem:
        push(index.by_stem[downie.stem_norm])

    title_tokens = tokenize(downie.title_clean)
    stem_tokens = tokenize(downie.stem)
    combined_tokens = {t for t in (title_tokens | stem_tokens) if len(t) >= 4}
    for token in combined_tokens:
        push(index.by_tokens.get(token, []))

    if len(candidates) < 10:
        for rec in index.records:
            if rec.stem_norm and (
                rec.stem_norm in downie.title_norm
                or downie.title_norm in rec.stem_norm
            ):
                push([rec])
                if len(candidates) >= 50:
                    break

    return candidates[:200]


def run_conversion(config: ConversionConfig, log: Callable[[str], None]) -> dict:
    """Main entrypoint: perform the full conversion based on config.

    - Validates paths
    - Parses Downie JSON
    - Indexes media
    - Matches & writes Stash scene JSON files (unless dry_run=True)
    - Writes report.json, unmatched.json, ambiguous.json
    """
    json_root = config.json_root
    media_roots = config.media_roots
    out_root = config.output_root
    scenes_dir = out_root / "scenes"

    log(f"JSON root: {json_root}")
    for mr in media_roots:
        log(f"Media root: {mr}")
    log(f"Output: {out_root}")

    if not json_root.exists() or not json_root.is_dir():
        raise ValueError("JSON root does not exist or is not a directory")

    for mr in media_roots:
        if not mr.exists() or not mr.is_dir():
            raise ValueError(f"Media root does not exist or is not a directory: {mr}")

    out_root.mkdir(parents=True, exist_ok=True)
    if not config.dry_run:
        scenes_dir.mkdir(parents=True, exist_ok=True)

    downie_files = sorted(json_root.rglob("*.json"))
    downie_records: list[DownieRecord] = []
    invalid_json: list[str] = []

    log(f"Found {len(downie_files)} JSON files under {json_root}")

    for path in downie_files:
        record = parse_downie_json(path)
        if record:
            downie_records.append(record)
        else:
            invalid_json.append(str(path.resolve()))

    log(
        f"Parsed {len(downie_records)} Downie metadata files; "
        f"{len(invalid_json)} invalid/non-Downie",
    )

    index = MediaIndex()
    index.build_from_roots(media_roots, log=log)

    matched: list[dict] = []
    unmatched: list[dict] = []
    ambiguous: list[dict] = []

    for i, record in enumerate(downie_records, start=1):
        log(f"[{i}/{len(downie_records)}] Matching: {record.title_clean}")
        candidates = find_candidates(index, record)
        best, issue, top_scored = choose_best_match(
            record,
            candidates,
            config.min_score,
            config.ambiguity_gap,
        )

        if not best:
            entry = {
                "json_path": record.json_path,
                "title": record.title_clean,
                "reason": issue or "no candidates",
                "candidate_count": len(candidates),
                "top_candidates": [
                    {
                        "score": round(score, 2),
                        "path": candidate.path,
                        "reasons": reasons,
                    }
                    for score, candidate, reasons in top_scored
                ],
            }
            if issue and issue.startswith("ambiguous"):
                ambiguous.append(entry)
            else:
                unmatched.append(entry)
            log(f"  -> SKIP: {entry['reason']} ({len(candidates)} candidates)")
            continue

        score, media, reasons = best
        payload = build_scene_payload(
            record,
            media,
            include_date=config.include_date,
            details_text=config.details_text,
            allow_stream_url=config.allow_stream_url,
        )
        output_json = None
        if not config.dry_run:
            fname = f"{sanitize_filename(record.title_clean)}.{i:05d}.json"
            output_path = scenes_dir / fname
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            output_json = str(output_path.resolve())

        matched_entry = asdict(
            MatchResult(
                json_path=record.json_path,
                matched=True,
                reason="; ".join(reasons),
                score=round(score, 2),
                title=record.title_clean,
                scene_url=payload.get("url"),
                video_path=media.path,
                output_json=output_json,
                candidate_count=len(candidates),
            )
        )
        matched.append(matched_entry)
        log(
            f"  -> MATCH: score={matched_entry['score']} "
            f"file={media.path}"
        )

    summary = {
        "json_root": str(json_root.resolve()),
        "media_roots": [str(p.resolve()) for p in media_roots],
        "media_indexed": len(index.records),
        "downie_json_found": len(downie_files),
        "downie_json_parsed": len(downie_records),
        "invalid_or_skipped_json": invalid_json,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "ambiguous_count": len(ambiguous),
        "dry_run": config.dry_run,
        "matched": matched,
    }

    (out_root / "report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_root / "unmatched.json").write_text(
        json.dumps(unmatched, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_root / "ambiguous.json").write_text(
        json.dumps(ambiguous, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    log(
        f"Done. Matched={len(matched)}, "
        f"Unmatched={len(unmatched)}, Ambiguous={len(ambiguous)}",
    )
    log(f"Report: {(out_root / 'report.json').resolve()}")

    return summary
