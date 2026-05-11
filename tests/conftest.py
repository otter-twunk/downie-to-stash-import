from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_json_root(tmp_path: Path) -> Path:
    json_root = tmp_path / "downie-json"
    json_root.mkdir()

    payloads = [
        {
            "file": "alpha-scene.json",
            "data": {
                "__type": "DownieMetadata",
                "title": "Alpha Scene - | JustTheGays - justthegays.tv",
                "referer": "https://example.com/alpha-scene",
                "creationDate": "2024-01-02T12:00:00Z",
            },
        },
        {
            "file": "bravo-scene.json",
            "data": {
                "__type": "DownieMetadata",
                "title": "Bravo Scene",
                "referer": "https://example.com/bravo-scene",
                "creationDate": "2024-02-03T12:00:00Z",
            },
        },
        {
            "file": "missing-scene.json",
            "data": {
                "__type": "DownieMetadata",
                "title": "Missing Scene",
                "referer": "https://example.com/missing-scene",
                "creationDate": "2024-03-04T12:00:00Z",
            },
        },
    ]

    for item in payloads:
        (json_root / item["file"]).write_text(json.dumps(item["data"]), encoding="utf-8")

    return json_root


@pytest.fixture
def tmp_media_root(tmp_path: Path) -> Path:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "alpha scene.mp4").write_bytes(b"")
    (media_root / "bravo-scene.mp4").write_bytes(b"")
    return media_root


@pytest.fixture
def tmp_output_root(tmp_path: Path) -> Path:
    output_root = tmp_path / "output"
    output_root.mkdir()
    return output_root
