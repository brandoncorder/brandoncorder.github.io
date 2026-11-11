#!/usr/bin/env python3
"""Create browser-sized favicon assets from images/favicon.png.

Run: python scripts/build_favicons.py
Requires: Pillow (pip install pillow)

The source image is kept unchanged; all output files are derived assets.
Preserve the entire artwork with transparent padding instead of cropping it.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "images" / "favicon.png"


def square_icon(image: Image.Image, size: int) -> Image.Image:
    """Downsample the full image onto a transparent, square canvas."""
    rgba = image.convert("RGBA")
    fitted = ImageOps.contain(rgba, (size, size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    return canvas


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source favicon: {SOURCE}")
    with Image.open(SOURCE) as image:
        image.load()
        if image.format != "PNG":
            raise SystemExit("The source favicon must be a PNG.")
        print(f"Source favicon: {image.width}×{image.height}, {SOURCE.stat().st_size:,} bytes")
        for size, path in [
            (32, ROOT / "images" / "favicon-32.png"),
            (180, ROOT / "images" / "apple-touch-icon.png"),
        ]:
            icon = square_icon(image, size)
            icon.save(path, format="PNG", optimize=True)
            print(f"Created {path.relative_to(ROOT)}: {size}×{size}, {path.stat().st_size:,} bytes")

        # The conventional root favicon.ico supports browsers and bots that
        # request /favicon.ico without inspecting the HTML <head>.
        icon = square_icon(image, 64)
        output = ROOT / "favicon.ico"
        icon.save(output, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
        print(f"Created favicon.ico: 16, 32, 48, 64 px; {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
