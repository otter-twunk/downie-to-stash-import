from __future__ import annotations

import json
from pathlib import Path

import pytest

from downie_to_stash.core import ConversionConfig, run_conversion


def _config(
    json_root: Path,
    media_root: Path,
    output_root: Path,
    dry_run: bool,
    path_mappings: list[tuple[str, str]] | None = None,
) -> ConversionConfig:
    return ConversionConfig(
        json_root=json_root,
        media_roots=[media_root],
        output_root=output_root,
        details_text="Imported from Downie metadata",
        min_score=60.0,
        ambiguity_gap=7.5,
        allow_stream_url=False,
        include_date=True,
        dry_run=dry_run,
        path_mappings=path_mappings or [],
    )


def test_run_conversion_basic_match(
    tmp_json_root: Path, tmp_media_root: Path, tmp_output_root: Path
) -> None:
    summary = run_conversion(
        _config(tmp_json_root, tmp_media_root, tmp_output_root, dry_run=False),
        log=lambda _: None,
    )

    scenes_dir = tmp_output_root / "scenes"
    assert scenes_dir.exists()

    scene_files = sorted(scenes_dir.glob("*.json"))
    assert len(scene_files) == 2
    for scene_file in scene_files:
        scene_json = json.loads(scene_file.read_text(encoding="utf-8"))
        assert "title" in scene_json
        assert "files" in scene_json

    assert (tmp_output_root / "report.json").exists()
    assert (tmp_output_root / "unmatched.json").exists()
    assert (tmp_output_root / "ambiguous.json").exists()
    assert summary["matched_count"] == 2


def test_run_conversion_dry_run(
    tmp_json_root: Path, tmp_media_root: Path, tmp_output_root: Path
) -> None:
    run_conversion(
        _config(tmp_json_root, tmp_media_root, tmp_output_root, dry_run=True),
        log=lambda _: None,
    )
    assert not (tmp_output_root / "scenes").exists()
    assert (tmp_output_root / "report.json").exists()


def test_run_conversion_invalid_json_root_raises(
    tmp_media_root: Path, tmp_output_root: Path, tmp_path: Path
) -> None:
    with pytest.raises(ValueError):
        run_conversion(
            _config(
                tmp_path / "missing", tmp_media_root, tmp_output_root, dry_run=False
            ),
            log=lambda _: None,
        )


def test_run_conversion_empty_json_root(
    tmp_media_root: Path, tmp_output_root: Path, tmp_path: Path
) -> None:
    empty_json_root = tmp_path / "empty-json"
    empty_json_root.mkdir()
    summary = run_conversion(
        _config(empty_json_root, tmp_media_root, tmp_output_root, dry_run=True),
        log=lambda _: None,
    )
    assert summary["matched_count"] == 0


def test_run_conversion_no_media(
    tmp_json_root: Path, tmp_output_root: Path, tmp_path: Path
) -> None:
    empty_media_root = tmp_path / "empty-media"
    empty_media_root.mkdir()
    summary = run_conversion(
        _config(tmp_json_root, empty_media_root, tmp_output_root, dry_run=True),
        log=lambda _: None,
    )
    assert summary["unmatched_count"] == 3


def test_run_conversion_preserves_non_resolved_media_path(
    tmp_json_root: Path, tmp_output_root: Path, tmp_path: Path
) -> None:
    actual_media_root = tmp_path / "actual-media"
    actual_media_root.mkdir()
    (actual_media_root / "alpha scene.mp4").write_bytes(b"")
    (actual_media_root / "bravo-scene.mp4").write_bytes(b"")

    linked_media_root = tmp_path / "linked-media"
    linked_media_root.symlink_to(actual_media_root, target_is_directory=True)

    run_conversion(
        _config(tmp_json_root, linked_media_root, tmp_output_root, dry_run=False),
        log=lambda _: None,
    )

    scene_files = sorted((tmp_output_root / "scenes").glob("*.json"))
    scene_json = json.loads(scene_files[0].read_text(encoding="utf-8"))
    exported_path = scene_json["files"][0]
    assert str(linked_media_root) in exported_path
    assert str(actual_media_root) not in exported_path


def test_run_conversion_applies_path_mapping(
    tmp_json_root: Path, tmp_media_root: Path, tmp_output_root: Path
) -> None:
    run_conversion(
        _config(
            tmp_json_root,
            tmp_media_root,
            tmp_output_root,
            dry_run=False,
            path_mappings=[(str(tmp_media_root), "/data")],
        ),
        log=lambda _: None,
    )

    scene_files = sorted((tmp_output_root / "scenes").glob("*.json"))
    scene_json = json.loads(scene_files[0].read_text(encoding="utf-8"))
    assert scene_json["files"][0].startswith("/data/")
