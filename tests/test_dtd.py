from pathlib import Path

from PIL import Image

from scripts.dtd import DtdError
from scripts.dtd import load_content
from scripts.dtd import render_post


def sample() -> dict:
    return {
        "date": "2026-07-27",
        "slug": "test",
        "book": {"title": "테스트 책", "author": "테스트 저자", "source_pdf": ""},
        "quotes": [
            {"text": "첫 번째 문장입니다.", "page": "1"},
            {"text": "두 번째 문장입니다.", "page": "2"},
            {"text": "세 번째 문장입니다.", "page": "3"},
        ],
        "approved": False,
    }


def test_render_creates_instagram_portrait_slides(tmp_path: Path) -> None:
    destination, manifest = render_post(sample(), tmp_path)
    assert len(manifest["slides"]) == 4
    for slide in manifest["slides"]:
        with Image.open(destination / slide["file"]) as image:
            assert image.size == (1080, 1350)


def test_requires_three_to_five_quotes(tmp_path: Path) -> None:
    path = tmp_path / "post.json"
    data = sample()
    data["quotes"] = data["quotes"][:2]
    import json

    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        load_content(path)
    except DtdError as exc:
        assert "3-5개" in str(exc)
    else:
        raise AssertionError("2개 문구가 검증을 통과했습니다.")
