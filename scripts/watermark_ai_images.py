"""Burn a visible "made by AI" mark into every AI-generated illustration listed in the media library.

The 2026 Space Apps submission guide says AI-generated images "must include a visible watermark". The mark sits
in the lower centre, above the app's own image label: the app crops images with object-fit cover around a focal
point, which mostly trims the sides. A marked file carries an XMP packet (IPTC digital source type "trainedAlgorithmicMedia"); files that already have it
are skipped, so running the script again never draws a second mark.

Usage: python scripts/watermark_ai_images.py   (needs Pillow from requirements-dev.lock and `npm ci` in frontend/)
"""

import json
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "frontend" / "public"
MEDIA_JSON = REPO / "frontend" / "src" / "data" / "generated" / "media.json"
FONT_DIR = REPO / "frontend" / "node_modules" / "@fontsource" / "be-vietnam-pro" / "files"
# fontsource splits the font by script: Vietnamese letters in one file, plain Latin and punctuation in another
FONT_FILES = ("be-vietnam-pro-vietnamese-600-normal.woff2", "be-vietnam-pro-latin-600-normal.woff2")

MARK_TEXT = "Ảnh tạo bằng AI · AI-generated"
TEXT_SIZE_SHARE = 0.032  # font size as a share of image width: about 12 CSS px when a 640 px file fills a phone
# the app's own label covers the bottom 42 of 246 CSS px of a home step card (Media.module.css .tag): keep above it
LABEL_SHARE = 0.2
# the app's image label colours (frontend/src/design-system/Media.module.css .tag)
BOX_RGBA = (8, 20, 11, 168)
TEXT_RGB = (244, 240, 229)
# chosen so re-encoded files come out about as large as the originals (measured on the 64 files, 2026-11-15)
QUALITY = {"WEBP": 82, "AVIF": 58}
# IPTC NewsCodes digital source type for media made by a trained model (https://cv.iptc.org/newscodes/digitalsourcetype/)
AI_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
XMP = (
    '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
    f'Iptc4xmpExt:DigitalSourceType="{AI_SOURCE_TYPE}"/></rdf:RDF></x:xmpmeta>'
).encode()

FontsForSize = Callable[[int], list[ImageFont.FreeTypeFont]]


def load_fonts(size: int) -> list[ImageFont.FreeTypeFont]:
    return [ImageFont.truetype(FONT_DIR / name, size) for name in FONT_FILES]


def glyph(font: ImageFont.FreeTypeFont, char: str) -> tuple[bytes, float]:
    canvas = Image.new("L", (round(font.size) * 2, round(font.size) * 2))
    ImageDraw.Draw(canvas).text((0, 0), char, font=font, fill=255)
    return canvas.tobytes(), font.getlength(char)


def has_glyph(font: ImageFont.FreeTypeFont, char: str) -> bool:
    # a missing letter gets the font's "not defined" glyph (same pixels and width) like a private-use code point
    return glyph(font, char) != glyph(font, "\U0010fffd")


def text_runs(text: str, fonts: list[ImageFont.FreeTypeFont]) -> list[tuple[str, ImageFont.FreeTypeFont]]:
    """Split text into runs, each drawn with the first font that has its letters."""
    runs: list[tuple[str, ImageFont.FreeTypeFont]] = []
    for char in text:
        font = next((f for f in fonts if has_glyph(f, char)), None)
        if font is None:
            raise ValueError(f"no font in {FONT_FILES} has the letter {char!r} of {text!r}")
        if runs and runs[-1][1] is font:
            runs[-1] = (runs[-1][0] + char, font)
        else:
            runs.append((char, font))
    return runs


def draw_mark(image: Image.Image, fonts_for_size: FontsForSize) -> Image.Image:
    width, height = image.size
    size = round(width * TEXT_SIZE_SHARE)
    runs = text_runs(MARK_TEXT, fonts_for_size(size))
    text_width = sum(font.getlength(text) for text, font in runs)
    ascent, descent = runs[0][1].getmetrics()
    pad_x, pad_y = round(size * 0.7), round(size * 0.3)
    box_w, box_h = round(text_width) + 2 * pad_x, ascent + descent + 2 * pad_y
    left, top = (width - box_w) // 2, height - box_h - round(height * LABEL_SHARE)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((left, top, left + box_w, top + box_h), radius=box_h // 2, fill=BOX_RGBA)
    x = left + pad_x
    for text, font in runs:
        # baseline anchor keeps runs from different subset files on one line
        draw.text((x, top + pad_y + ascent), text, font=font, fill=TEXT_RGB, anchor="ls")
        x += font.getlength(text)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert(image.mode)


def watermark_file(path: Path, fonts_for_size: FontsForSize = load_fonts) -> bool:
    """Mark one AVIF or WebP file in place, keeping its size and format. False when it was already marked."""
    with Image.open(path) as image:
        if AI_SOURCE_TYPE.encode() in (image.info.get("xmp") or b""):
            return False
        fmt = image.format
        if fmt not in QUALITY:
            raise ValueError(f"{path} is {fmt}, expected one of {sorted(QUALITY)}")
        marked = draw_mark(image.convert("RGB"), fonts_for_size)
    marked.save(path, fmt, quality=QUALITY[fmt], xmp=XMP)
    return True


def illustration_paths(media: dict, public: Path) -> list[Path]:
    """Every AVIF and WebP file of every illustration in media.json."""
    return [
        public / source[fmt]
        for asset in media.values()
        if asset["kind"] == "illustration"
        for source in asset["sources"]
        for fmt in ("avif", "webp")
    ]


if __name__ == "__main__":
    paths = illustration_paths(json.loads(MEDIA_JSON.read_text(encoding="utf-8")), PUBLIC)
    changed = [path for path in paths if watermark_file(path)]
    print(f"marked {len(changed)} of {len(paths)} illustration files")
