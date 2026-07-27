#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image
from PIL import ImageChops
from PIL import ImageDraw
from PIL import ImageFilter
from PIL import ImageFont
from PIL import ImageOps
from pypdf import PdfReader

from scripts.dtd import DtdError
from scripts.dtd import HEIGHT
from scripts.dtd import ROOT
from scripts.dtd import WIDTH
from scripts.dtd import load_content
from scripts.dtd import post_id
from scripts.dtd import resolve_source
from scripts.dtd import wrap_text


STYLE_NAMES = (
    "gpt-taste",
    "high-end-visual-design",
    "minimalist-ui",
)

FONT_DIR = Path.home() / "Library/Fonts"
FONT_FILES = {
    "regular": FONT_DIR / "Pretendard-Regular.otf",
    "bold": FONT_DIR / "Pretendard-Bold.otf",
    "extra": FONT_DIR / "Pretendard-ExtraBold.otf",
}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    configured = os.environ.get("DTD_FONT_PATH")
    path = Path(configured).expanduser() if configured else FONT_FILES.get(weight, FONT_FILES["regular"])
    if not path.is_file():
        path = FONT_FILES["regular"]
    if not path.is_file():
        raise DtdError("Pretendard가 필요합니다. DTD_FONT_PATH 또는 ~/Library/Fonts/Pretendard-Regular.otf를 확인하세요.")
    return ImageFont.truetype(str(path), size=size)


def largest_run(values: list[int], threshold: int) -> tuple[int, int]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values + [0]):
        if value >= threshold and start is None:
            start = index
        elif value < threshold and start is not None:
            runs.append((start, index))
            start = None
    if not runs:
        raise DtdError("PDF 첫 페이지에서 표지 경계를 찾지 못했습니다.")
    return max(runs, key=lambda run: run[1] - run[0])


def crop_cover_screenshot(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    white = Image.new("RGB", image.size, "white")
    mask = ImageChops.difference(image, white).convert("L").point(lambda value: 255 if value > 18 else 0)
    row_density = list(mask.resize((1, image.height), Image.Resampling.BOX).get_flattened_data())
    top, bottom = largest_run(row_density, 70)
    column_density = list(mask.crop((0, top, image.width, bottom)).resize((image.width, 1), Image.Resampling.BOX).get_flattened_data())
    left, right = largest_run(column_density, 70)
    return image.crop((left, top, right, bottom))


def extract_cover(data: dict[str, Any]) -> Image.Image:
    raw = str(data["book"].get("cover_source_pdf") or data["book"].get("source_pdf") or "").strip()
    source = resolve_source({"book": {"source_pdf": raw}}, required=True)
    assert source is not None
    images = PdfReader(source).pages[0].images
    if not images:
        raise DtdError("PDF 첫 페이지에 추출 가능한 표지 이미지가 없습니다.")
    return crop_cover_screenshot(images[0].image)


def dominant_accent(image: Image.Image) -> tuple[int, int, int]:
    sample = image.convert("RGB").resize((120, 120), Image.Resampling.LANCZOS)
    colors = sample.quantize(colors=12).convert("RGB").getcolors(120 * 120) or []
    candidates: list[tuple[float, tuple[int, int, int]]] = []
    for count, color in colors:
        red, green, blue = color
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        del hue
        if saturation >= 0.18 and 0.22 <= value <= 0.98:
            candidates.append((count * (0.5 + saturation), color))
    return max(candidates, default=(0, (222, 180, 52)), key=lambda item: item[0])[1]


def blend(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(a * (1 - amount) + b * amount) for a, b in zip(first, second, strict=True))


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
    weight: str,
    spacing: int,
) -> tuple[str, ImageFont.FreeTypeFont]:
    for size in range(max_size, min_size - 1, -2):
        selected_font = font(weight, size)
        wrapped = wrap_text(draw, text, selected_font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=selected_font, spacing=spacing)
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, selected_font
    raise DtdError("비교 카드에 넣기에는 문구가 너무 깁니다.")


def text_height(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, spacing: int) -> int:
    box = draw.multiline_textbbox((0, 0), text, font=selected_font, spacing=spacing)
    return box[3] - box[1]


def paste_cover(canvas: Image.Image, cover: Image.Image, box: tuple[int, int, int, int], *, shadow: int = 0) -> None:
    left, top, right, bottom = box
    fitted = ImageOps.contain(cover, (right - left, bottom - top), Image.Resampling.LANCZOS)
    x = left + (right - left - fitted.width) // 2
    y = top + (bottom - top - fitted.height) // 2
    if shadow:
        layer = Image.new("RGBA", canvas.size)
        shadow_draw = ImageDraw.Draw(layer)
        shadow_draw.rectangle((x + 12, y + 18, x + fitted.width + 12, y + fitted.height + 18), fill=(0, 0, 0, shadow))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(22)))
    canvas.alpha_composite(fitted.convert("RGBA"), (x, y))


def palette(style: str, accent: tuple[int, int, int]) -> dict[str, tuple[int, int, int]]:
    if style in {"design-taste-frontend-v1", "gpt-taste"}:
        return {"bg": (20, 21, 22), "surface": (34, 35, 36), "ink": (244, 244, 240), "muted": (169, 171, 168), "accent": accent}
    if style == "high-end-visual-design":
        return {"bg": (231, 233, 234), "surface": (249, 249, 247), "ink": (30, 32, 31), "muted": (105, 109, 106), "accent": blend(accent, (255, 255, 255), 0.28)}
    if style == "minimalist-ui":
        return {"bg": (248, 247, 244), "surface": (255, 255, 253), "ink": (28, 28, 27), "muted": (116, 114, 108), "accent": blend(accent, (255, 255, 255), 0.48)}
    if style == "industrial-brutalist-ui":
        return {"bg": (242, 242, 236), "surface": accent, "ink": (15, 15, 15), "muted": (67, 67, 63), "accent": accent}
    return {"bg": (242, 243, 239), "surface": (255, 255, 252), "ink": (27, 28, 27), "muted": (103, 106, 101), "accent": accent}


def draw_footer(draw: ImageDraw.ImageDraw, colors: dict[str, tuple[int, int, int]], index: int, total: int, *, dark: bool = False) -> None:
    footer_font = font("bold", 25)
    fill = colors["muted"] if not dark else colors["ink"]
    draw.text((74, 1284), "dtd.page", font=footer_font, fill=fill)
    marker = f"{index:02d}/{total:02d}"
    marker_width = draw.textlength(marker, font=footer_font)
    draw.text((WIDTH - 74 - marker_width, 1284), marker, font=footer_font, fill=fill)


def render_cover(style: str, data: dict[str, Any], cover: Image.Image, colors: dict[str, tuple[int, int, int]]) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), colors["bg"] + (255,))
    cover_boxes = {
        "gpt-taste": (225, 165, 855, 1185),
        "high-end-visual-design": (250, 175, 830, 1175),
        "minimalist-ui": (270, 195, 810, 1155),
    }
    paste_cover(image, cover, cover_boxes[style])
    return image.convert("RGB")


def render_quote(style: str, data: dict[str, Any], quote: dict[str, Any], number: int, colors: dict[str, tuple[int, int, int]]) -> Image.Image:
    title = data["book"]["title"].strip()
    total = len(data["quotes"]) + 1
    page = str(quote.get("page", "")).strip()
    image = Image.new("RGB", (WIDTH, HEIGHT), colors["bg"])
    draw = ImageDraw.Draw(image)
    text = quote["text"].strip()

    if style == "design-taste-frontend":
        draw.rectangle((70, 112, 82, 1010), fill=colors["accent"])
        draw.text((112, 112), f"문장 {number - 1}", font=font("bold", 25), fill=colors["muted"])
        wrapped, quote_font = fit_text(draw, text, max_width=835, max_height=700, max_size=70, min_size=40, weight="bold", spacing=22)
        height = text_height(draw, wrapped, quote_font, 22)
        draw.multiline_text((112, 500 - height // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=22)
        draw.text((112, 1065), f"{title}  /  PDF p.{page}", font=font("regular", 28), fill=colors["muted"])
    elif style == "design-taste-frontend-v1":
        draw.rectangle((0, 0, WIDTH, 30), fill=colors["accent"])
        draw.rectangle((760, 80, 1005, 325), fill=colors["accent"])
        draw.text((804, 112), f"{number - 1:02d}", font=font("extra", 112), fill=colors["bg"])
        wrapped, quote_font = fit_text(draw, text, max_width=860, max_height=720, max_size=72, min_size=40, weight="bold", spacing=24)
        height = text_height(draw, wrapped, quote_font, 24)
        draw.multiline_text((76, 600 - height // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=24)
        draw.line((76, 1085, 1005, 1085), fill=colors["muted"], width=2)
        draw.text((76, 1125), f"{title} / PDF p.{page}", font=font("regular", 28), fill=colors["muted"])
    elif style == "gpt-taste":
        draw.rectangle((0, 0, 34, HEIGHT), fill=colors["accent"])
        draw.text((74, 84), f"QUOTE {number - 1:02d}", font=font("bold", 26), fill=colors["accent"])
        wrapped, quote_font = fit_text(draw, text, max_width=880, max_height=720, max_size=76, min_size=40, weight="extra", spacing=20)
        box = draw.multiline_textbbox((0, 0), wrapped, font=quote_font, spacing=20)
        draw.multiline_text(((WIDTH - (box[2] - box[0])) // 2, 620 - (box[3] - box[1]) // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=20, align="center")
        meta = f"{title} / PDF p.{page}"
        meta_width = draw.textlength(meta, font=font("regular", 28))
        draw.text(((WIDTH - meta_width) // 2, 1085), meta, font=font("regular", 28), fill=colors["muted"])
    elif style == "high-end-visual-design":
        draw.rounded_rectangle((66, 66, 1014, 1235), radius=54, fill=blend(colors["bg"], (0, 0, 0), 0.05))
        draw.rounded_rectangle((80, 80, 1000, 1221), radius=46, fill=colors["surface"])
        draw.rounded_rectangle((120, 125, 290, 168), radius=20, fill=blend(colors["accent"], colors["surface"], 0.62))
        draw.text((144, 132), f"문장 {number - 1}", font=font("bold", 23), fill=colors["ink"])
        wrapped, quote_font = fit_text(draw, text, max_width=760, max_height=650, max_size=66, min_size=38, weight="bold", spacing=23)
        box = draw.multiline_textbbox((0, 0), wrapped, font=quote_font, spacing=23)
        draw.multiline_text(((WIDTH - (box[2] - box[0])) // 2, 620 - (box[3] - box[1]) // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=23, align="center")
        meta = f"{title} / PDF p.{page}"
        meta_width = draw.textlength(meta, font=font("regular", 27))
        draw.text(((WIDTH - meta_width) // 2, 1065), meta, font=font("regular", 27), fill=colors["muted"])
    elif style == "minimalist-ui":
        draw.text((70, 72), title, font=font("bold", 27), fill=colors["ink"])
        draw.text((880, 72), f"{number - 1:02d}", font=font("bold", 27), fill=colors["muted"])
        draw.line((70, 125, 1010, 125), fill=(224, 223, 218), width=2)
        wrapped, quote_font = fit_text(draw, text, max_width=830, max_height=720, max_size=68, min_size=39, weight="regular", spacing=25)
        height = text_height(draw, wrapped, quote_font, 25)
        draw.multiline_text((105, 570 - height // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=25)
        draw.rectangle((105, 1015, 290, 1022), fill=colors["accent"])
        draw.text((105, 1060), f"PDF p.{page}", font=font("regular", 27), fill=colors["muted"])
    else:
        draw.rectangle((0, 0, WIDTH, 110), fill=colors["ink"])
        draw.text((54, 30), f"QUOTE / {number - 1:02d}", font=font("extra", 31), fill=colors["bg"])
        draw.text((850, 30), f"P.{page}", font=font("extra", 31), fill=colors["accent"])
        draw.rectangle((54, 160, 1018, 1060), outline=colors["ink"], width=5)
        draw.rectangle((54, 160, 215, 1060), fill=colors["accent"])
        draw.text((82, 202), f"{number - 1:02d}", font=font("extra", 105), fill=colors["ink"])
        wrapped, quote_font = fit_text(draw, text, max_width=710, max_height=700, max_size=68, min_size=38, weight="extra", spacing=18)
        height = text_height(draw, wrapped, quote_font, 18)
        draw.multiline_text((255, 610 - height // 2), wrapped, font=quote_font, fill=colors["ink"], spacing=18)
        draw.rectangle((54, 1080, 1018, 1165), fill=colors["ink"])
        draw.text((74, 1102), title, font=font("bold", 27), fill=colors["bg"])

    draw_footer(draw, colors, number, total, dark=style == "industrial-brutalist-ui")
    return image


def render_style(style: str, data: dict[str, Any], cover: Image.Image, accent: tuple[int, int, int], output_root: Path) -> Path:
    if style not in STYLE_NAMES:
        raise DtdError(f"지원하지 않는 디자인 스킬입니다: {style}")
    destination = output_root / style
    destination.mkdir(parents=True, exist_ok=True)
    colors = palette(style, accent)
    render_cover(style, data, cover, colors).save(destination / "01-cover.png", optimize=True)
    for index, quote in enumerate(data["quotes"], start=2):
        render_quote(style, data, quote, index, colors).save(destination / f"{index:02d}-quote.png", optimize=True)
    return destination


def build_comparison_board(data: dict[str, Any], output_root: Path) -> Path:
    cell_width, cell_height = 720, 600
    rows = (len(STYLE_NAMES) + 2) // 3
    board = Image.new("RGB", (cell_width * 3, cell_height * rows), (238, 238, 234))
    board_draw = ImageDraw.Draw(board)
    longest_index = max(range(len(data["quotes"])), key=lambda index: len(data["quotes"][index]["text"])) + 2
    for index, style in enumerate(STYLE_NAMES):
        column, row = index % 3, index // 3
        x, y = column * cell_width, row * cell_height
        board_draw.rectangle((x + 1, y + 1, x + cell_width - 1, y + cell_height - 1), fill=(252, 252, 249))
        board_draw.text((x + 28, y + 24), style, font=font("bold", 28), fill=(26, 26, 25))
        cover = Image.open(output_root / style / "01-cover.png").convert("RGB")
        quote = Image.open(output_root / style / f"{longest_index:02d}-quote.png").convert("RGB")
        board.paste(ImageOps.fit(cover, (310, 388), method=Image.Resampling.LANCZOS), (x + 28, y + 88))
        board.paste(ImageOps.fit(quote, (310, 388), method=Image.Resampling.LANCZOS), (x + 382, y + 88))
        board_draw.text((x + 28, y + 500), "표지", font=font("regular", 23), fill=(105, 105, 100))
        board_draw.text((x + 382, y + 500), "최장 문구", font=font("regular", 23), fill=(105, 105, 100))
    path = output_root / "comparison-board.png"
    board.save(path, optimize=True)
    return path


def render_comparison(data: dict[str, Any], output_root: Path) -> dict[str, Any]:
    cover = extract_cover(data)
    accent = dominant_accent(cover)
    output_root.mkdir(parents=True, exist_ok=True)
    cover.save(output_root / "cover-cropped.png", optimize=True)
    for style in STYLE_NAMES:
        render_style(style, data, cover, accent, output_root)
    board = build_comparison_board(data, output_root)
    summary = {
        "id": post_id(data),
        "styles": list(STYLE_NAMES),
        "slides_per_style": len(data["quotes"]) + 1,
        "accent_rgb": accent,
        "cover_size": cover.size,
        "comparison_board": board.name,
        "approved": data.get("approved") is True,
    }
    (output_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="dtd.page 디자인 스킬 비교 렌더러")
    parser.add_argument("content", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = load_content(args.content)
        output = args.output or ROOT / ".work/design-tests" / post_id(data)
        print(json.dumps({"output": str(output), **render_comparison(data, output)}, ensure_ascii=False, indent=2))
    except DtdError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
