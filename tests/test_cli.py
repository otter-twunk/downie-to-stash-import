from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from downie_to_stash import cli


def test_cli_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "downie_to_stash.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Convert Downie JSON" in proc.stdout


def test_cli_dry_run(tmp_json_root: Path, tmp_media_root: Path, tmp_output_root: Path) -> None:
    code = cli.main(
        [
            "--json-root",
            str(tmp_json_root),
            "--media-root",
            str(tmp_media_root),
            "--output",
            str(tmp_output_root),
            "--dry-run",
        ]
    )

    report_path = tmp_output_root / "report.json"
    assert code == 1
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dry_run"] is True
