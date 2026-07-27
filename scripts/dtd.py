#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF_ROOT = Path(
    os.environ.get(
        "DTD_PDF_ROOT",
        Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/PDF",
    )
).expanduser()
PUBLIC_BASE_URL = os.environ.get("DTD_PUBLIC_BASE_URL", "https://seungwonme.github.io/dtd.page").rstrip("/")
GRAPH_VERSION = os.environ.get("INSTAGRAM_GRAPH_VERSION", "v23.0")
WIDTH, HEIGHT = 1080, 1350
BACKGROUND = "#F5F0E8"
INK = "#172238"
MUTED = "#68707D"
ACCENT = "#E46E42"
WHITE = "#FFFDFC"
FONT_CANDIDATES = (
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
)


class DtdError(RuntimeError):
    pass


def load_content(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DtdError(f"콘텐츠 JSON을 읽을 수 없습니다: {path}") from exc

    try:
        dt.date.fromisoformat(data["date"])
        slug = data["slug"]
        book = data["book"]
        quotes = data["quotes"]
    except (KeyError, TypeError, ValueError) as exc:
        raise DtdError("date, slug, book, quotes 필드를 확인하세요.") from exc

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise DtdError("slug는 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.")
    if not isinstance(book, dict) or not str(book.get("title", "")).strip() or not str(book.get("author", "")).strip():
        raise DtdError("book.title과 book.author가 필요합니다.")
    if not isinstance(quotes, list) or not 3 <= len(quotes) <= 5:
        raise DtdError("문구는 3-5개여야 합니다.")
    for index, quote in enumerate(quotes, start=1):
        text = str(quote.get("text", "")).strip() if isinstance(quote, dict) else ""
        if not text or len(text) > 360:
            raise DtdError(f"{index}번 문구는 1-360자여야 합니다.")
    return data


def post_id(data: dict[str, Any]) -> str:
    return f"{data['date']}-{data['slug']}"


def resolve_source(data: dict[str, Any], *, required: bool) -> Path | None:
    raw = str(data["book"].get("source_pdf", "")).strip()
    if not raw:
        if required:
            raise DtdError("공개 발행에는 book.source_pdf가 필요합니다.")
        return None
    root = PDF_ROOT.resolve()
    source = Path(raw).expanduser()
    source = source.resolve() if source.is_absolute() else (root / source).resolve()
    if source != root and root not in source.parents:
        raise DtdError("source_pdf는 DTD_PDF_ROOT 안에 있어야 합니다.")
    if not source.is_file():
        raise DtdError(f"PDF를 찾을 수 없습니다: {raw}")
    return source


def font_path() -> str:
    configured = os.environ.get("DTD_FONT_PATH")
    for candidate in (configured, *FONT_CANDIDATES):
        if candidate and Path(candidate).is_file():
            return candidate
    raise DtdError("한글 글꼴을 찾을 수 없습니다. DTD_FONT_PATH를 지정하세요.")


def split_long_token(draw: ImageDraw.ImageDraw, token: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in token:
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            parts.append(current)
            current = char
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            tokens = [word]
            if draw.textlength(word, font=font) > max_width:
                tokens = split_long_token(draw, word, font, max_width)
            for token in tokens:
                candidate = token if not current else f"{current} {token}"
                if current and draw.textlength(candidate, font=font) > max_width:
                    lines.append(current)
                    current = token
                else:
                    current = candidate
        if current:
            lines.append(current)
    return "\n".join(lines)


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
    spacing: int,
) -> tuple[str, ImageFont.FreeTypeFont]:
    path = font_path()
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(path, size=size)
        wrapped = wrap_text(draw, text, font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font
    raise DtdError("카드에 넣기에는 문구가 너무 깁니다.")


def centered_x(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, spacing: int = 4) -> int:
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return (WIDTH - (box[2] - box[0])) // 2


def render_post(data: dict[str, Any], output_root: Path | None = None) -> tuple[Path, dict[str, Any]]:
    output_root = output_root or ROOT / "docs/posts"
    destination = output_root / post_id(data)
    destination.mkdir(parents=True, exist_ok=True)
    regular = font_path()
    title = data["book"]["title"].strip()
    author = data["book"]["author"].strip()
    slides: list[dict[str, str]] = []
    total = len(data["quotes"]) + 1

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 75, 154, 89), radius=7, fill=ACCENT)
    label_font = ImageFont.truetype(regular, 34)
    brand_font = ImageFont.truetype(regular, 30)
    draw.text((80, 130), "오늘의 문장", font=label_font, fill=MUTED)
    wrapped, cover_font = fit_text(draw, title, max_width=820, max_height=520, max_size=108, min_size=56, spacing=22)
    draw.multiline_text((80, 330), wrapped, font=cover_font, fill=INK, spacing=22)
    draw.text((82, 930), author, font=ImageFont.truetype(regular, 42), fill=ACCENT)
    draw.line((80, 1160, 1000, 1160), fill="#D7D1C8", width=2)
    draw.text((80, 1205), "day to day, page by page", font=brand_font, fill=MUTED)
    draw.text((910, 1205), f"01/{total:02d}", font=brand_font, fill=MUTED)
    cover_path = destination / "01-cover.png"
    image.save(cover_path, optimize=True)
    slides.append({"file": cover_path.name, "alt_text": f"{title}, {author}. 오늘의 문장 표지"})

    for index, quote in enumerate(data["quotes"], start=2):
        image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((78, 78, 1002, 1272), radius=42, fill=WHITE)
        draw.ellipse((100, 108, 126, 134), fill=ACCENT)
        quote_text = f"“{quote['text'].strip()}”"
        wrapped, quote_font = fit_text(
            draw,
            quote_text,
            max_width=760,
            max_height=650,
            max_size=66,
            min_size=38,
            spacing=24,
        )
        box = draw.multiline_textbbox((0, 0), wrapped, font=quote_font, spacing=24)
        text_height = box[3] - box[1]
        draw.multiline_text((centered_x(draw, wrapped, quote_font, 24), (HEIGHT - text_height) // 2 - 70), wrapped, font=quote_font, fill=INK, spacing=24, align="center")
        meta = title
        page = str(quote.get("page", "")).strip()
        if page:
            meta = f"{meta} · p.{page}"
        meta_font = ImageFont.truetype(regular, 31)
        meta_wrapped = wrap_text(draw, meta, meta_font, 760)
        draw.multiline_text((centered_x(draw, meta_wrapped, meta_font), 1085), meta_wrapped, font=meta_font, fill=MUTED, spacing=10, align="center")
        draw.text((105, 1210), "dtd.page", font=brand_font, fill=MUTED)
        draw.text((870, 1210), f"{index:02d}/{total:02d}", font=brand_font, fill=MUTED)
        slide_path = destination / f"{index:02d}-quote.png"
        image.save(slide_path, optimize=True)
        slides.append({"file": slide_path.name, "alt_text": f"{title}에서 고른 문장 {index - 1}: {quote['text'].strip()}"})

    manifest = {
        "id": post_id(data),
        "book": data["book"],
        "caption": str(data.get("caption", "")).strip() or f"{title}에서 오늘 마음에 머문 문장들.",
        "slides": slides,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, manifest


def extract_pdf(source_arg: str, page_range: str | None) -> Path:
    data = {"book": {"source_pdf": source_arg}}
    source = resolve_source(data, required=True)
    assert source is not None
    reader = PdfReader(source)
    start, end = 1, len(reader.pages)
    if page_range:
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", page_range)
        if not match:
            raise DtdError("--pages는 12 또는 12-30 형식이어야 합니다.")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > len(reader.pages):
            raise DtdError(f"쪽수 범위는 1-{len(reader.pages)} 안이어야 합니다.")
    parts = []
    for page_number in range(start, end + 1):
        text = reader.pages[page_number - 1].extract_text() or ""
        parts.append(f"\n\n--- PDF page {page_number} ---\n\n{text}")
    destination = ROOT / ".work/extracts" / f"{source.stem}-p{start}-{end}.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(parts).lstrip(), encoding="utf-8")
    return destination


def public_urls(manifest: dict[str, Any]) -> list[str]:
    identifier = urllib.parse.quote(manifest["id"])
    return [f"{PUBLIC_BASE_URL}/posts/{identifier}/{urllib.parse.quote(slide['file'])}" for slide in manifest["slides"]]


def wait_for_urls(urls: list[str], timeout: int) -> None:
    deadline = time.monotonic() + timeout
    pending = set(urls)
    while pending and time.monotonic() < deadline:
        for url in list(pending):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10) as response:
                    if response.status == 200 and response.headers.get_content_type().startswith("image/"):
                        pending.remove(url)
            except (OSError, urllib.error.HTTPError):
                pass
        if pending:
            time.sleep(5)
    if pending:
        raise DtdError(f"공개 이미지 URL이 준비되지 않았습니다: {len(pending)}개")


def graph_post(path: str, payload: dict[str, str], token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}",
        data=urllib.parse.urlencode(payload).encode(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").replace(token, "[masked]")
        raise DtdError(f"Instagram API 오류 HTTP {exc.code}: {body[:600]}") from exc


def publish_carousel(manifest: dict[str, Any], urls: list[str]) -> dict[str, Any]:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    if not token or not user_id:
        raise DtdError("INSTAGRAM_ACCESS_TOKEN과 INSTAGRAM_USER_ID가 필요합니다.")
    child_ids = []
    for url, slide in zip(urls, manifest["slides"], strict=True):
        response = graph_post(
            f"{user_id}/media",
            {"image_url": url, "is_carousel_item": "true", "alt_text": slide["alt_text"], "access_token": token},
            token,
        )
        if not response.get("id"):
            raise DtdError("Instagram이 carousel child id를 반환하지 않았습니다.")
        child_ids.append(str(response["id"]))
    parent = graph_post(
        f"{user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": manifest["caption"],
            "access_token": token,
        },
        token,
    )
    creation_id = str(parent.get("id", ""))
    if not creation_id:
        raise DtdError("Instagram이 carousel container id를 반환하지 않았습니다.")
    result = graph_post(f"{user_id}/media_publish", {"creation_id": creation_id, "access_token": token}, token)
    if not result.get("id"):
        raise DtdError("Instagram이 게시물 id를 반환하지 않았습니다.")
    return {"media_id": str(result["id"]), "container_id": creation_id}


def run_git(args: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=False, text=True, capture_output=capture)
    if result.returncode:
        detail = result.stderr.strip() if capture else ""
        raise DtdError(f"git {' '.join(args)} 실패{': ' + detail if detail else ''}")
    return result.stdout.strip() if capture else ""


def commit_paths(paths: list[Path], message: str) -> None:
    staged = run_git(["diff", "--cached", "--name-only"], capture=True)
    if staged:
        raise DtdError("이미 staged 된 파일이 있어 자동 커밋을 중단했습니다.")
    relative = [str(path.resolve().relative_to(ROOT)) for path in paths]
    run_git(["add", "--", *relative])
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False)
    if diff.returncode == 1:
        run_git(["commit", "-m", message])
        run_git(["push", "origin", "HEAD"])
    elif diff.returncode != 0:
        raise DtdError("staged diff를 확인할 수 없습니다.")


def release(content_path: Path, *, publish: bool, wait_seconds: int) -> dict[str, Any]:
    data = load_content(content_path)
    destination, manifest = render_post(data)
    urls = public_urls(manifest)
    plan = {"mode": "publish" if publish else "dry-run", "id": manifest["id"], "slides": urls, "caption": manifest["caption"]}
    if not publish:
        return plan
    if data.get("approved") is not True:
        raise DtdError("approved가 true인 콘텐츠만 발행할 수 있습니다.")
    resolve_source(data, required=True)
    state_path = ROOT / "state" / f"{manifest['id']}.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        raise DtdError(f"중복 발행 방지: {state_path.name} 상태가 {state.get('status', 'unknown')}입니다.")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    pending = {
        "id": manifest["id"],
        "status": "pending",
        "caption_sha256": hashlib.sha256(manifest["caption"].encode()).hexdigest(),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    state_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    commit_paths([content_path, destination, state_path], f"content: host {manifest['id']}")
    wait_for_urls(urls, wait_seconds)
    result = publish_carousel(manifest, urls)
    pending.update(result)
    pending["status"] = "published"
    pending["published_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    commit_paths([state_path], f"content: record {manifest['id']} publication")
    return {**plan, **result, "status": "published"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="dtd.page 카드뉴스 렌더링과 발행")
    subparsers = result.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract", help="선택한 PDF 텍스트 추출")
    extract.add_argument("source_pdf")
    extract.add_argument("--pages", help="PDF 쪽수, 예: 12 또는 12-30")
    render = subparsers.add_parser("render", help="카드 PNG 생성")
    render.add_argument("content", type=Path)
    release_parser = subparsers.add_parser("release", help="dry-run 또는 승인된 게시물 발행")
    release_parser.add_argument("content", type=Path)
    release_parser.add_argument("--publish", action="store_true", help="GitHub Pages 호스팅 후 실제 Instagram 발행")
    release_parser.add_argument("--wait-seconds", type=int, default=180)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "extract":
            print(extract_pdf(args.source_pdf, args.pages))
        elif args.command == "render":
            data = load_content(args.content)
            destination, manifest = render_post(data)
            print(json.dumps({"output": str(destination), "slides": len(manifest["slides"])}, ensure_ascii=False))
        else:
            print(json.dumps(release(args.content, publish=args.publish, wait_seconds=args.wait_seconds), ensure_ascii=False, indent=2))
    except DtdError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
