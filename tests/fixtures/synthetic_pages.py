#!/usr/bin/env python3
"""Render synthetic register pages with invented words at known pixel boxes.

Test fixtures only. Every name is invented; no real record, scan or surname is used.
Rendering is deterministic (seeded speckle, fixed layout). Word boxes are measured from
the rendered ink, so tests do not depend on font metrics. Requires Pillow.

    python tests/fixtures/synthetic_pages.py OUT_DIR
"""
import json
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont

PAGE_SIZE = (2400, 3200)
PAPER = (236, 226, 200)
INK = (58, 40, 26)
SLANT = 0.28
# Two pages share word positions on purpose: same coordinates, different pages, different words.
PAGES = {
    1: [('Ulvadine', (260, 420)), ('Moonquill', (980, 420)), ('Orlamund', (260, 1180)),
        ('Fizzcourt', (1040, 1180)), ('Zephrine', (260, 1940)), ('Glimmerholt', (1000, 1940))],
    2: [('Tarskelo', (260, 420)), ('Pebblewhit', (980, 420)), ('Quorvina', (260, 1180)),
        ('Brindlemoss', (1040, 1180)), ('Ysolde', (260, 1940)), ('Thistlewick', (1000, 1940))],
}


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def word_tile(text, size=96):
    """Draw one word with a forward slant on a transparent tile; return the tile cropped to its ink."""
    face = font(size)
    probe = ImageDraw.Draw(Image.new('L', (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=face)
    width, height = right - left + 40, bottom - top + 40
    mask = Image.new('L', (width + int(height * SLANT) + 20, height), 0)
    ImageDraw.Draw(mask).text((20 - left + int(height * SLANT), 20 - top), text, font=face, fill=255, stroke_width=2, stroke_fill=255)
    mask = mask.transform(mask.size, Image.AFFINE, (1, SLANT, 0, 0, 1, 0), resample=Image.BICUBIC)
    return mask.crop(mask.getbbox())


def render(page, path=None):
    """Render page 1 or 2. Returns the layout: page number, size and each word's ink box [x0, y0, x1, y1]."""
    image = Image.new('RGB', PAGE_SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    noise = random.Random(page)
    for _ in range(4000):
        x, y = noise.randrange(PAGE_SIZE[0]), noise.randrange(PAGE_SIZE[1])
        shade = noise.randrange(200, 230)
        draw.point((x, y), fill=(shade, shade - 8, shade - 30))
    for y in range(300, PAGE_SIZE[1] - 200, 190):
        draw.line([(160, y + 150), (PAGE_SIZE[0] - 160, y + 150)], fill=(205, 196, 172), width=2)
    words = []
    for text, (x, y) in PAGES[page]:
        tile = word_tile(text)
        image.paste(Image.new('RGB', tile.size, INK), (x, y), tile)
        words.append({'text': text, 'bbox': [x, y, x + tile.size[0], y + tile.size[1]]})
    if path is not None:
        image.save(path)
    return {'page': page, 'size': list(PAGE_SIZE), 'words': words}


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    layout = [render(page, out / ('page-%d.png' % page)) for page in sorted(PAGES)]
    (out / 'layout.json').write_text(json.dumps(layout, indent=2) + '\n', encoding='utf-8')
    return layout


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
