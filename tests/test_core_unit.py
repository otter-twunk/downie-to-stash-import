from __future__ import annotations

from downie_to_stash.core import (
    DownieRecord,
    MediaRecord,
    clean_title,
    extract_date,
    normalize_text,
    sanitize_filename,
    score_candidate,
    tokenize,
)


def _downie(stem: str = "alpha scene", title: str = "Alpha Scene") -> DownieRecord:
    return DownieRecord(
        json_path="/tmp/alpha.json",
        stem=stem,
        title_raw=title,
        title_clean=title,
        title_norm=normalize_text(title),
        stem_norm=normalize_text(stem),
        referer=None,
        media_url=None,
        preview_image=None,
        date=None,
    )


def _media(stem: str = "alpha scene") -> MediaRecord:
    return MediaRecord(
        path="/tmp/alpha scene.mp4",
        stem=stem,
        stem_norm=normalize_text(stem),
        parent_name="lib",
        parent_norm=normalize_text("lib"),
        grandparent_name="",
        grandparent_norm="",
        ext=".mp4",
        size=10,
    )


def test_normalize_text_strips_noise() -> None:
    assert normalize_text("JustTheGays Official Video") == ""


def test_normalize_text_handles_empty() -> None:
    assert normalize_text("") == ""


def test_normalize_text_handles_url() -> None:
    assert (
        normalize_text("https://example.com/Alpha Scene") == "example com alpha scene"
    )


def test_clean_title_strips_boilerplate() -> None:
    assert clean_title("My Video - | JustTheGays - justthegays.tv") == "My Video"


def test_clean_title_passthrough() -> None:
    assert clean_title("A Real Title") == "A Real Title"


def test_clean_title_empty_input() -> None:
    assert clean_title("") == "Untitled"


def test_extract_date_iso_format() -> None:
    assert extract_date({"creationDate": "2024-03-08T12:00:00Z"}) == "2024-03-08"


def test_extract_date_missing() -> None:
    assert extract_date({}) is None


def test_extract_date_falls_back_to_prepare_date() -> None:
    assert extract_date({"prepareDate": "2024-03-09T12:00:00Z"}) == "2024-03-09"


def test_tokenize_result_type() -> None:
    result = tokenize("Alpha Scene")
    assert isinstance(result, set)
    assert all(isinstance(token, str) for token in result)


def test_sanitize_filename_no_forbidden_chars() -> None:
    assert sanitize_filename('bad:/\\*?"<>|name') == "bad-name"


def test_score_candidate_exact_stem() -> None:
    score, _ = score_candidate(_downie(), _media())
    assert score > 60


def test_score_candidate_zero_for_mismatch() -> None:
    score, _ = score_candidate(
        _downie(stem="zzzz", title="zzzz"), _media(stem="alpha scene")
    )
    assert score < 20
