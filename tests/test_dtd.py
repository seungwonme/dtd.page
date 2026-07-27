from pathlib import Path

from PIL import Image

from scripts.dtd import DtdError
from scripts.dtd import GRAPH_VERSION
from scripts.dtd import graph_post
from scripts.dtd import load_content
from scripts.dtd import render_post
from scripts.dtd import wait_for_container


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


def test_render_creates_instagram_portrait_slides(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("scripts.design_compare.extract_cover", lambda data: Image.new("RGB", (600, 900), "#E6B438"))
    destination, manifest = render_post(sample(), tmp_path)
    assert len(manifest["slides"]) == 4
    assert manifest["style"] == "minimalist-ui"
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


def test_graph_post_uses_instagram_login_host(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return b'{"id":"1"}'

    def urlopen(request, timeout):
        assert request.full_url == f"https://graph.instagram.com/{GRAPH_VERSION}/123/media"
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assert graph_post("123/media", {"key": "value"}, "token") == {"id": "1"}


def test_waits_until_container_is_finished(monkeypatch) -> None:
    statuses = iter(({"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}))
    monkeypatch.setattr("scripts.dtd.graph_get", lambda *args: next(statuses))
    monkeypatch.setattr("scripts.dtd.time.sleep", lambda seconds: None)
    wait_for_container("123", "token")
