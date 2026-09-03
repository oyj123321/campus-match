"""
16 型岛图：公有领域铜版/木刻 → 主题色二创（1024² PNG）。

只收 CC0 / PDM / 博物馆开放获取。运行：
  python scripts/engrave_islands.py
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "personality_islands"
UA = "CampusMatch/1.9 (engrave remix; https://campusmatch.com.cn)"

# (ink, paper-tint) — ink 用型主题色，纸仍偏羊皮纸
THEMES = {
    "ESCP": "#4f46e5",
    "ESCA": "#6366f1",
    "EFCP": "#d97706",
    "EFCA": "#db2777",
    "ESOP": "#0369a1",
    "ESOA": "#0f766e",
    "EFOP": "#c2410c",
    "EFOA": "#15803d",
    "ISCP": "#475569",
    "ISCA": "#6d28d9",
    "IFCP": "#be123c",
    "IFCA": "#7e22ce",
    "ISOP": "#1e3a8a",
    "ISOA": "#115e59",
    "IFOP": "#3f6212",
    "IFOA": "#1e3a8a",
}

# 每型一张：url / 来源页 / 许可 / 作者或作品名
SOURCES = {
    "ESCP": {
        "title": "Coat of Arms with a Lion (1544), Sebald Beham",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/9992351/coat-arms-with-lion-1544-sebald-beham",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIzLTA0L25nYTQzNDYtaW1hZ2UuanBn.jpg",
    },
    "ESCA": {
        "title": "Javaans schip te Bantam, 1596",
        "license": "CC0",
        "source": "https://commons.wikimedia.org/wiki/File:Javaans_schip_te_Bantam,_1596,_RP-P-OB-80.259.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Javaans_schip_te_Bantam%2C_1596%2C_RP-P-OB-80.259.jpg",
        "crop": (0.0, 0.0, 1.0, 0.86),
    },
    "EFCP": {
        "title": "Bird nest plate (Biodiversity Heritage Library scan)",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/61021753@N02/8592743010",
        "url": "https://live.staticflickr.com/8525/8592743010_5fbc3d7261_b.jpg",
    },
    "EFCA": {
        "title": "Paysage avec Paris et Oenone (Claude Lorrain)",
        "license": "CC0",
        "source": "https://www.flickr.com/photos/125149010@N07/24607292165",
        "url": "https://live.staticflickr.com/1566/24607292165_5b985041e3_b.jpg",
        "invert": False,
    },
    "ESOP": {
        "title": "The Eddystone Lighthouse",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/9117587/the-eddystone-lighthouse",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIzLTAxL3ljYmF0bXMzMDk2My1pbWFnZS5qcGc.jpg",
    },
    "ESOA": {
        "title": "The Burgundian Standard Bearer, c. 1500",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/8782864/the-burgundian-standard-bearer",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIyLTExL3Nta2trc2diNjQzMS1pbWFnZS5qcGc.jpg",
    },
    "EFOP": {
        "title": "Cottages at Dents Hole, Byker (J.W. Carmichael / Lambert)",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/39821974@N06/4076581052",
        "url": "https://live.staticflickr.com/2724/4076581052_49e5a76aeb_b.jpg",
    },
    "EFOA": {
        "title": "Eastern comfrey and Indian sage (botanical plate)",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/97123293@N07/15167922018",
        "url": "https://live.staticflickr.com/2947/15167922018_0c03886566_b.jpg",
    },
    "ISCP": {
        "title": "Ramsgate, Kent: the beach and harbour by night (wood engraving, 1850)",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/14018138/ramsgate-kent-the-beach-and-harbour-night-wood-engraving-1850",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDI0LTAyL2xyL3djeTRzcDlnN2ctaW1hZ2UuanBn.jpg",
    },
    "ISCA": {
        "title": "Architecture: various masonry details. Engraving, Bénard after Lucotte",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/14020922/architecture-various-masonry-details-engraving-benard-after-lucotte",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDI0LTAyL2xyL3djejRka3B5c3otaW1hZ2UuanBn.jpg",
    },
    "IFCP": {
        "title": "Changeable Rose and Queen Swallowtail, Maria Sibylla Merian",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/97123293@N07/24347988201",
        "url": "https://live.staticflickr.com/65535/24347988201_0c853dcbf9_b.jpg",
    },
    "IFCA": {
        "title": "Liras o cítaras de los antiguos",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/37667416@N04/4031749408",
        "url": "https://live.staticflickr.com/3505/4031749408_54cc341a28_b.jpg",
    },
    "ISOP": {
        "title": "A scholar in his study, reading",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/13972543/image-person-book-art",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDI0LTAyL2xyL3djYWFmOXVha2ctaW1hZ2UuanBn.jpg",
    },
    "ISOA": {
        "title": "Diogenes, seated before his barrel (Met Open Access)",
        "license": "CC0",
        "source": "https://www.metmuseum.org/art/collection/search/354611",
        "url": "https://images.metmuseum.org/CRDImages/dp/original/DR89.jpg",
        "invert": False,
    },
    "IFOP": {
        "title": "Hospital of St Mary the Virgin, 1786",
        "license": "PDM 1.0",
        "source": "https://www.flickr.com/photos/39821974@N06/4090513911",
        "url": "https://live.staticflickr.com/2528/4090513911_4dc5c83df5_b.jpg",
        "crop": (0.02, 0.02, 0.98, 0.58),
        "invert": False,
    },
    "IFOA": {
        "title": "Saint Stephen (Cepheus), Constellation IV",
        "license": "CC0",
        "source": "https://www.rawpixel.com/image/7653514/image-vintage-art-public-domain",
        "url": "https://images.rawpixel.com/editor_1024/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIyLTA4L2xyL21pYTczOTA2LWltYWdlLmpwZw.jpg",
    },
}

PAPER = (244, 234, 214)  # #f4ead6


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def crop_content(im: Image.Image) -> Image.Image:
    """去掉四周近纸色的空白。"""
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    bw = g.point(lambda p: 255 if p < 232 else 0)
    bbox = bw.getbbox()
    if not bbox:
        return im
    w, h = im.size
    pad = int(min(w, h) * 0.04)
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(w, r + pad)
    b = min(h, b + pad)
    return im.crop((l, t, r, b))


def to_ink_on_paper(im: Image.Image, invert: bool | None) -> Image.Image:
    g = ImageOps.grayscale(im)
    g = ImageOps.autocontrast(g, cutoff=2)
    do_inv = invert if invert is not None else (ImageStat.Stat(g).median[0] < 90)
    if do_inv:
        g = ImageOps.invert(g)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.12)
    return g


def grain(im: Image.Image, amount: int = 12) -> Image.Image:
    noise = Image.effect_noise(im.size, amount).convert("L")
    noise = ImageEnhance.Contrast(noise).enhance(0.35)
    return Image.blend(im, Image.merge("RGB", (noise, noise, noise)), 0.07)


def compose(gray: Image.Image, ink: str, size: int = 1024) -> Image.Image:
    paper = PAPER
    colored = ImageOps.colorize(gray, black=hex_rgb(ink), white=paper)
    colored = grain(colored)
    # 主体约占画面 82%，四周留纸边（分享卡仍会略裁）
    box = int(size * 0.86)
    fitted = ImageOps.contain(colored, (box, box), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), paper)
    x = (size - fitted.width) // 2
    y = int((size - fitted.height) * 0.38)  # 略靠上，适配 object-position 40%
    canvas.paste(fitted, (x, y))
    # 极轻的纸纹
    canvas = canvas.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=2))
    return canvas


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = []
    for code, src in SOURCES.items():
        print("fetch", code, src["title"][:48])
        raw = fetch(src["url"])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        box = src.get("crop")
        if box:
            w, h = im.size
            im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
        im = crop_content(im)
        gray = to_ink_on_paper(im, src.get("invert"))
        out = compose(gray, THEMES[code])
        dest = OUT / f"{code}.png"
        out.save(dest, "PNG", optimize=True)
        rec = {
            "code": code,
            "title": src["title"],
            "license": src["license"],
            "source": src["source"],
            "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
        }
        meta.append(rec)
        print("  ->", dest, out.size)
    manifest = ROOT / "docs" / "personality-island-sources.json"
    manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", manifest)


if __name__ == "__main__":
    run()
