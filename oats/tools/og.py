#!/usr/bin/env python3
"""og.py - render the share image and the favicons from the brand type.

The wordmark is set in the real Archivo variable font (converted from the shipped woff2 on
the fly with fontTools), so the social card matches the site instead of approximating it.

    python -m oats.tools.og
"""
import io
import os

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
CREAM, INK, TOAST = "#F9F2E8", "#0B0B0B", "#C98A3F"


def archivo(size, wdth=118, wght=900):
    """Pillow wants a TTF; the woff2 becomes one in memory."""
    f = TTFont(os.path.join(STATIC, "fonts", "archivo-var.woff2"))
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    font = ImageFont.truetype(buf, size)
    font.set_variation_by_axes([wght, wdth])   # axis order in the file: wght, wdth
    return font


def marker(size):
    f = TTFont(os.path.join(STATIC, "fonts", "permanent-marker.woff2"))
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def og_image():
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    # Right: the hero bowl, bleeding off the edge.
    bowl = Image.open(os.path.join(STATIC, "img", "hero-bowl-960.jpg")).convert("RGB")
    bh = H
    bw = round(bowl.width * bh / bowl.height)
    bowl = bowl.resize((bw, bh), Image.LANCZOS)
    x0 = W - bw - 8                       # flush right, so the handwriting in the shot stays whole
    im.paste(bowl, (x0, 0))
    # Fade the photo into the cream on its left edge so the type sits on a clean field.
    fade = Image.new("L", (300, H), 0)
    fd = ImageDraw.Draw(fade)
    for x in range(300):
        fd.line([(x, 0), (x, H)], fill=int(255 * (1 - x / 300)))
    cream = Image.new("RGB", (300, H), CREAM)
    im.paste(cream, (x0, 0), fade)
    if x0 > 0:
        im.paste(Image.new("RGB", (x0, H), CREAM), (0, 0))

    big = archivo(132)
    d.text((64, 70), "TOASTED", font=big, fill=INK)
    d.text((64, 190), "OATS", font=big, fill=INK)
    d.text((64 + d.textlength("OATS", font=big) + 8, 196), "TM", font=archivo(22, 100, 700), fill=INK)
    d.text((66, 340), "BLENDED OAT PUDDING", font=archivo(30, 100, 600), fill=INK)
    d.text((64, 430), "Same base.", font=marker(54), fill=INK)
    d.text((64, 500), "Different vibes.", font=marker(54), fill=INK)
    d.rounded_rectangle((64, 580, 420, 592), radius=6, fill=TOAST)
    im.save(os.path.join(STATIC, "img", "og.jpg"), quality=86, optimize=True, progressive=True)
    return im


def favicons():
    # The TO monogram: black rounded square, cream letters, drawn large then downsampled.
    S = 512
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=96, fill=INK)
    f = archivo(300, 100, 900)
    d.text((S / 2, S / 2 + 6), "TO", font=f, fill=CREAM, anchor="mm")
    im.save(os.path.join(STATIC, "apple-touch-icon.png"))
    im.resize((32, 32), Image.LANCZOS).save(os.path.join(STATIC, "favicon.ico"), sizes=[(32, 32), (16, 16)])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           f'<rect width="64" height="64" rx="12" fill="{INK}"/>'
           f'<text x="32" y="44" text-anchor="middle" font-family="Archivo,Arial Black,Arial,sans-serif" '
           f'font-weight="900" font-size="34" fill="{CREAM}">TO</text></svg>\n')
    with open(os.path.join(STATIC, "favicon.svg"), "w") as fh:
        fh.write(svg)


if __name__ == "__main__":
    og_image()
    favicons()
    print("wrote og.jpg, favicon.svg, favicon.ico, apple-touch-icon.png", flush=True)
