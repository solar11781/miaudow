"""Visible "made by AI" mark on the home illustrations (Space Apps 2026 submission guide: AI-generated images "must
include a visible watermark"). Written before scripts/watermark_ai_images.py. Run: pytest tests/test_watermark_ai_images.py
"""

import importlib.util
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageFont, ImageStat

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("watermark_ai_images", REPO / "scripts" / "watermark_ai_images.py")
watermark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watermark)


def default_fonts(size: int) -> list[ImageFont.FreeTypeFont]:
    # Pillow's built-in font: enough to test placement and re-runs without the frontend's node_modules
    return [ImageFont.load_default(size)]


@pytest.fixture
def latin_text(monkeypatch: pytest.MonkeyPatch) -> None:
    # the built-in font has no Vietnamese letters; the real font is checked in the last test
    monkeypatch.setattr(watermark, "MARK_TEXT", "AI-generated")


def mean_change(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(a.crop(box), b.crop(box))).mean) / 3


@pytest.mark.parametrize("fmt", ["WEBP", "AVIF"])
@pytest.mark.usefixtures("latin_text")
def test_mark_is_drawn_bottom_centre_and_keeps_size_and_format(tmp_path: Path, fmt: str) -> None:
    path = tmp_path / f"art-640.{fmt.lower()}"
    Image.new("RGB", (640, 426), (150, 170, 90)).save(path, fmt)
    before = Image.open(path).convert("RGB")

    assert watermark.watermark_file(path, default_fonts) is True

    after = Image.open(path)
    assert (after.format, after.size) == (fmt, (640, 426))
    after = after.convert("RGB")
    # bottom centre (where object-fit cover keeps it) changes; the top corners stay as they were
    assert mean_change(before, after, (260, 380, 380, 415)) > 30
    assert mean_change(before, after, (0, 0, 100, 100)) < 3
    assert mean_change(before, after, (540, 0, 640, 100)) < 3


@pytest.mark.parametrize("fmt", ["WEBP", "AVIF"])
@pytest.mark.usefixtures("latin_text")
def test_second_run_changes_nothing(tmp_path: Path, fmt: str) -> None:
    path = tmp_path / f"art-640.{fmt.lower()}"
    Image.new("RGB", (640, 426), (150, 170, 90)).save(path, fmt)
    watermark.watermark_file(path, default_fonts)
    marked = path.read_bytes()

    assert watermark.watermark_file(path, default_fonts) is False
    assert path.read_bytes() == marked


def test_only_illustrations_are_listed_with_both_formats(tmp_path: Path) -> None:
    media = {
        "x1": {
            "kind": "illustration",
            "sources": [{"w": 640, "avif": "media/art/x1-640.avif", "webp": "media/art/x1-640.webp"}],
        },
        "p1": {
            "kind": "photo",
            "sources": [{"w": 640, "avif": "media/photo/p1-640.avif", "webp": "media/photo/p1-640.webp"}],
        },
    }
    assert watermark.illustration_paths(media, tmp_path) == [
        tmp_path / "media/art/x1-640.avif",
        tmp_path / "media/art/x1-640.webp",
    ]


@pytest.mark.skipif(not watermark.FONT_DIR.exists(), reason="needs frontend/node_modules (npm ci in frontend)")
def test_every_letter_of_the_mark_has_a_be_vietnam_pro_glyph() -> None:
    fonts = watermark.load_fonts(20)
    runs = watermark.text_runs(watermark.MARK_TEXT, fonts)
    assert "".join(text for text, _ in runs) == watermark.MARK_TEXT
    # the Vietnamese letters come from the vietnamese subset, plain Latin and the middle dot from the latin subset
    assert runs[0] == ("Ả", fonts[0])
    assert ("ạ", fonts[0]) in runs
    assert ("ằ", fonts[0]) in runs
