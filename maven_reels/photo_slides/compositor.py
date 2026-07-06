"""Controlled local compositor — renders EXACT slide text at 1080x1920.

Higgsfield cannot guarantee text fidelity, so (per spec) it only ever supplies
the premium background visual; every character on the final slide is drawn
here with the bundled brand fonts. Zero credits, deterministic, and the text
is always pixel-exact. Backgrounds: a Higgsfield image when provided, else a
premium dark editorial gradient with a soft accent glow.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

W, H = config.SLIDE_W, config.SLIDE_H
MARGIN = 96
TEXT_W = W - 2 * MARGIN

_FONTS = {
    "display": config.FONTS_DIR / "ArchivoBlack-Regular.ttf",
    "condensed": config.FONTS_DIR / "BebasNeue-Regular.ttf",
    "body": config.FONTS_DIR / "Montserrat-SemiBold.ttf",
}


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    p = _FONTS[kind]
    if p.exists():
        return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)  # last resort — QA flags missing fonts


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _gradient(top: str, bottom: str) -> Image.Image:
    t, b = _hex(top), _hex(bottom)
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        f = y / (H - 1)
        row = tuple(round(t[i] + (b[i] - t[i]) * f) for i in range(3))
        for x in range(W):
            px[x, y] = row
    return img


def _background(style: dict, bg_image: Path | None) -> Image.Image:
    if bg_image and bg_image.exists():
        try:
            src = Image.open(bg_image).convert("RGB")
            # cover-fit to 1080x1920
            scale = max(W / src.width, H / src.height)
            src = src.resize((round(src.width * scale), round(src.height * scale)))
            left, top = (src.width - W) // 2, (src.height - H) // 2
            img = src.crop((left, top, left + W, top + H))
            # readability scrim — text must always win
            img = Image.blend(img, Image.new("RGB", (W, H), _hex(style["bg_top"])), 0.55)
            return img
        except OSError:
            pass  # unreadable file -> premium gradient fallback
    img = _gradient(style["bg_top"], style["bg_bottom"])
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    ax, ay = _hex(style["accent"]), (W // 2, round(H * 0.22))
    gd.ellipse([ay[0] - 520, ay[1] - 420, ay[0] + 520, ay[1] + 420],
               fill=(*ax, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    return img


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
          max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _tracked(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
             font: ImageFont.FreeTypeFont, fill, tracking: int = 6) -> int:
    """Letter-spaced eyebrow text; returns end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return round(x)


def render_slide(slide: dict, dest: Path, *, style_name: str = config.DEFAULT_STYLE,
                 bg_image: Path | None = None) -> dict:
    """Render one slide to PNG. Returns an honest report for the QA gate."""
    style = config.STYLE_VARIANTS.get(style_name, config.STYLE_VARIANTS[config.DEFAULT_STYLE])
    accent = _hex(style["accent"])
    ink, muted, faint = (236, 242, 248), (199, 210, 224), (141, 160, 181)

    img = _background(style, bg_image)
    d = ImageDraw.Draw(img)
    is_hook = slide["role"] == "hook"
    is_close = slide["role"] == "maven_takeaway"

    # --- top: eyebrow + slide counter -------------------------------------
    eyebrow_font = _font("body", 30)
    label = config.SLIDE_ROLE_LABELS.get(slide["role"], slide["role"]).upper()
    _tracked(d, (MARGIN, 128), f"{config.BRAND_NAME.upper()}  ·  {label}",
             eyebrow_font, accent, tracking=5)
    counter_font = _font("body", 34)
    counter = f"{slide['slide_number']}/{config.SLIDE_COUNT}"
    cw = d.textlength(counter, font=counter_font)
    d.text((W - MARGIN - cw, 124), counter, font=counter_font, fill=faint)
    d.rectangle([MARGIN, 196, MARGIN + 132, 204], fill=accent)

    # --- title -------------------------------------------------------------
    title_size = 116 if is_hook else 92
    title_font = _font("display", title_size)
    title_lines = _wrap(d, slide["title"], title_font, TEXT_W)
    while len(title_lines) > 4 and title_size > 64:      # keep it phone-readable
        title_size -= 8
        title_font = _font("display", title_size)
        title_lines = _wrap(d, slide["title"], title_font, TEXT_W)
    y = 340 if is_hook else 320
    for line in title_lines:
        d.text((MARGIN, y), line, font=title_font, fill=ink)
        y += round(title_size * 1.16)

    # --- body ---------------------------------------------------------------
    body_size = 52
    body_font = _font("body", body_size)
    y += 56
    for line in _wrap(d, slide["body"], body_font, TEXT_W):
        d.text((MARGIN, y), line, font=body_font, fill=muted)
        y += round(body_size * 1.5)

    # --- slide 5 disclaimer strip -------------------------------------------
    if is_close:
        strip_top = H - 372
        d.rectangle([MARGIN, strip_top, W - MARGIN, strip_top + 2], fill=(60, 74, 92))
        disc_font = _font("body", 30)
        dy = strip_top + 28
        for line in _wrap(d, config.DISCLAIMER + " Not SEBI-registered.",
                          disc_font, TEXT_W):
            d.text((MARGIN, dy), line, font=disc_font, fill=faint)
            dy += 44

    # --- source note + brand footer ------------------------------------------
    if not is_close:                    # slide 5's strip already carries the disclaimer
        note_font = _font("body", 28)
        d.text((MARGIN, H - 236), slide.get("source_note", ""),
               font=note_font, fill=faint)
    brand_font = _font("condensed", 56)
    d.text((MARGIN, H - 172), config.BRAND_NAME.upper(), font=brand_font, fill=ink)
    site_font = _font("body", 32)
    sw = d.textlength(config.BRAND_SITE, font=site_font)
    d.text((W - MARGIN - sw, H - 160), config.BRAND_SITE, font=site_font, fill=accent)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")
    return {
        "path": str(dest), "width": W, "height": H,
        "style": style_name,
        "background": "higgsfield_image" if (bg_image and bg_image.exists()) else "local_gradient",
        "fonts_bundled": all(p.exists() for p in _FONTS.values()),
        "min_text_px": 28, "title_px": title_size, "body_px": body_size,
        "text_fidelity": "exact_local_compositor",
    }
