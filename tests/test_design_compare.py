from pathlib import Path

from PIL import Image
from PIL import ImageDraw

from scripts.design_compare import STYLE_NAMES
from scripts.design_compare import crop_cover_screenshot
from scripts.design_compare import render_style


def test_all_design_styles_render_complete_carousels(tmp_path: Path) -> None:
    screenshot = Image.new("RGB", (500, 700), "white")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((100, 50, 399, 549), fill="#F3D348")
    draw.text((5, 680), "1/238", fill="gray")
    cover = crop_cover_screenshot(screenshot)
    assert cover.size == (300, 500)

    data = {
        "date": "2026-07-27",
        "slug": "test",
        "book": {"title": "아주 작은 습관의 힘", "author": "제임스 클리어"},
        "quotes": [
            {"text": "짧은 문장입니다.", "page": "20"},
            {"text": "조금 더 긴 문장이 카드 안에서 안정적으로 줄바꿈되는지 확인합니다.", "page": "22"},
            {"text": "마지막 문장입니다.", "page": "36"},
        ],
    }
    for style in STYLE_NAMES:
        destination = render_style(style, data, cover, (243, 211, 72), tmp_path)
        slides = sorted(destination.glob("*.png"))
        assert len(slides) == 4
        with Image.open(slides[0]) as first_slide:
            assert first_slide.getpixel((20, 20)) == first_slide.getpixel((1060, 1330))
        for slide in slides:
            with Image.open(slide) as image:
                assert image.size == (1080, 1350)
