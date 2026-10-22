"""Render the CampusMatch logo (static/brand/logo.svg) to PNG/ICO icons.

Run from the repo root: python scripts/gen_brand_icons.py
Keep the geometry here in sync with static/brand/logo.svg.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "brand"

INK = (20, 20, 19, 255)
PAPER = (244, 238, 227, 255)
ACCENT = (224, 122, 95, 255)
SS = 8  # supersampling factor


def disc(size, cx, cy, r, s):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), fill=255)
    return mask


def render(px, rounded=True):
    size = px * SS
    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=14 * s, fill=INK)
    else:
        d.rectangle((0, 0, size, size), fill=INK)

    lens = ImageChops.multiply(disc(size, 24, 32, 13, s), disc(size, 40, 32, 13, s))
    img.paste(Image.new("RGBA", (size, size), ACCENT), (0, 0), lens)

    for cx in (24, 40):
        ring = ImageChops.subtract(disc(size, cx, 32, 15, s), disc(size, cx, 32, 11, s))
        img.paste(Image.new("RGBA", (size, size), PAPER), (0, 0), ring)

    return img.resize((px, px), Image.LANCZOS)


def main():
    render(32).save(OUT / "favicon-32.png")
    render(180, rounded=False).save(OUT / "apple-touch-icon.png")
    render(192).save(OUT / "icon-192.png")
    render(512).save(OUT / "icon-512.png")
    render(48).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
