"""Compressed product images (Problem 9).

The catalogue photos (data/products/*.jpg, 450-900 px, ~35 KB each) are made
into three smaller versions, stored in data/products_optimized/<variant>/:

    card    360 px WebP    product grids, chat cards, closet, wish list
    large   800 px WebP    the single-item page
    model   512 px JPEG    any image sent to an AI model (fits one 512 px vision tile)

They're built when the server starts (only missing or out-of-date files, so
later starts take milliseconds) and served at /media/<variant>/<name> with a
one-week browser cache. The originals stay untouched at /media/products/.

    cd backend && python images.py     # build and print the size / token report
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

from db import DATA_DIR

SOURCE_DIR = DATA_DIR / "products"
OUT_DIR = DATA_DIR / "products_optimized"

# name -> (longest side in px, format, quality, file extension)
VARIANTS = {
    "card": (360, "WEBP", 72, "webp"),
    "large": (800, "WEBP", 80, "webp"),
    "model": (512, "JPEG", 70, "jpg"),
}


def variant_name(image_file_path: str, variant: str) -> str:
    """'products/basic-hoodie.jpg' -> 'basic-hoodie.webp' for the card variant."""
    return f"{Path(image_file_path).stem}.{VARIANTS[variant][3]}"


def variant_url(image_file_path: str, variant: str) -> str:
    return f"/media/{variant}/{variant_name(image_file_path, variant)}"


def _make(src: Path, dst: Path, max_side: int, fmt: str, quality: int) -> None:
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side), Image.LANCZOS)  # never upscales
        dst.parent.mkdir(parents=True, exist_ok=True)
        opts = {"quality": quality, "method": 6} if fmt == "WEBP" else {"quality": quality, "optimize": True, "progressive": True}
        im.save(dst, fmt, **opts)


def ensure_images() -> int:
    """Build any missing or stale compressed images. Returns how many files were written."""
    written = 0
    for src in SOURCE_DIR.glob("*.jpg"):
        for variant, (side, fmt, quality, ext) in VARIANTS.items():
            dst = OUT_DIR / variant / f"{src.stem}.{ext}"
            if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                _make(src, dst, side, fmt, quality)
                written += 1
    return written


def image_for_model(image_file_path: str) -> bytes:
    """The small JPEG to send whenever a product photo goes to a vision model."""
    return (OUT_DIR / "model" / variant_name(image_file_path, "model")).read_bytes()


# ---- Report -----------------------------------------------------------------

def vision_tokens(width: int, height: int) -> int:
    """Image input tokens for a high-detail image under the published OpenAI GPT-4o-style formula:
    fit in 2048x2048, scale the short side to 768, then 170 tokens per 512 px tile + 85 base."""
    scale = min(1.0, 2048 / max(width, height))
    w, h = width * scale, height * scale
    scale = min(1.0, 768 / min(w, h))
    w, h = w * scale, h * scale
    return 85 + 170 * math.ceil(w / 512) * math.ceil(h / 512)


def report() -> dict:
    srcs = sorted(SOURCE_DIR.glob("*.jpg"))
    out = {"images": len(srcs), "original_kb": round(sum(f.stat().st_size for f in srcs) / 1024)}
    for variant, (_, _, _, ext) in VARIANTS.items():
        files = [OUT_DIR / variant / f"{s.stem}.{ext}" for s in srcs]
        out[f"{variant}_kb"] = round(sum(f.stat().st_size for f in files) / 1024)
    tokens_orig = tokens_model = 0
    for s in srcs:
        with Image.open(s) as a, Image.open(OUT_DIR / "model" / f"{s.stem}.jpg") as b:
            tokens_orig += vision_tokens(*a.size)
            tokens_model += vision_tokens(*b.size)
    out["vision_tokens_original"] = tokens_orig
    out["vision_tokens_model_variant"] = tokens_model
    return out


if __name__ == "__main__":
    print(f"wrote {ensure_images()} files")
    r = report()
    for k, v in r.items():
        print(f"  {k:28} {v}")
    print(f"  page weight, 102-card grid:  {r['original_kb']} KB -> {r['card_kb']} KB "
          f"({100 - 100 * r['card_kb'] // r['original_kb']}% smaller)")
    print(f"  vision tokens, all photos:   {r['vision_tokens_original']} -> {r['vision_tokens_model_variant']} "
          f"({100 - 100 * r['vision_tokens_model_variant'] // r['vision_tokens_original']}% fewer)")
