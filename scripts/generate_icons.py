#!/usr/bin/env python3
"""Generate PWA icons from existing favicon. Run once from project root."""
from pathlib import Path
from PIL import Image

STATIC = Path(__file__).parent.parent / 'static'
src = STATIC / 'favicon-32x32.png'

for size in (192, 512):
    img = Image.open(src).resize((size, size), Image.LANCZOS)
    dest = STATIC / f'android-chrome-{size}x{size}.png'
    img.save(dest)
    print(f'Generated {dest}')
