#!/usr/bin/env python3
"""Proof sheets for the Greek: PNGs rendered with FreeType.

    python tools/greek/proof.py                      # from fonts/variable/AlloVariable.ttf
    python tools/greek/proof.py --ufo sources/masters/Allo-opsz14-wght400-ROND50.ufo   # one source, quickly

Writes documentation/greek-*.png.
"""
import argparse
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]

CAPS = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
LOWER = 'αβγδεζηθικλμνξοπρσςτυφχψω'
ACCENTS = 'ΆΈΉΊΌΎΏΪΫ άέήίόύώϊϋΐΰ ΄΅·;'
PANGRAM = 'Ξεσκεπάζω την ψυχοφθόρα βδελυγμία.'
WORDS = 'Καλημέρα κόσμε! Hamburgefonstiv ΑΘΗΝΑ Θεσσαλονίκη'
MIXED = 'HΗ AΑ OΟ nη oο vν uυ xχ pρ'

BG, FG, DIM = (250, 250, 248), (20, 20, 24), (150, 150, 160)


def font(path, size, **axes):
    f = ImageFont.truetype(str(path), size)
    if axes:
        names = [a['name'] if isinstance(a['name'], str) else a['name'].decode() for a in f.get_variation_axes()]
        tags = {'Optical size': 'opsz', 'Weight': 'wght', 'Roundness': 'ROND'}
        cur = {tags.get(n, n): a['default'] for n, a in zip(names, f.get_variation_axes())}
        cur.update(axes)
        f.set_variation_by_axes([cur[tags.get(n, n)] for n in names])
    return f


def sheet(path, rows, out, width=2400):
    """rows: [(label, text, size, axes)]."""
    label_font = ImageFont.load_default(size=22)
    heights = [int(size * 1.45) + 34 for _, _, size, _ in rows]
    img = Image.new('RGB', (width, sum(heights) + 60), BG)
    d = ImageDraw.Draw(img)
    y = 30
    for (label, text, size, axes), h in zip(rows, heights):
        d.text((40, y), label, font=label_font, fill=DIM)
        d.text((40, y + 28), text, font=font(path, size, **axes), fill=FG)
        y += h
    img.save(out)
    print(out)


def from_ufo(ufo):
    import ufoLib2
    from ufo2ft import compileTTF
    tt = compileTTF(ufoLib2.Font.open(ufo), useProductionNames=False)
    out = Path(tempfile.gettempdir()) / (Path(ufo).stem + '.ttf')
    tt.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ufo')
    ap.add_argument('--font', default=str(ROOT / 'fonts/variable/AlloVariable.ttf'))
    ap.add_argument('--out', default=str(ROOT / 'documentation'))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    if args.ufo:
        path = from_ufo(args.ufo)
        name = Path(args.ufo).stem
        sheet(path, [('caps', CAPS, 110, {}), ('lower', LOWER, 110, {}), ('accents', ACCENTS, 110, {}),
                     ('with Latin', MIXED, 110, {}), ('pangram', PANGRAM, 80, {}), ('words', WORDS, 80, {})],
              out / f'proof-{name}.png')
        return
    path = Path(args.font)
    rows = []
    for w in (100, 300, 400, 600, 700, 900):
        rows.append((f'wght {w}', CAPS + ' ' + LOWER[:12], 64, {'wght': w}))
    sheet(path, rows, out / 'greek-weights.png')
    rows = []
    for r in (0, 50, 100):
        for w in (400, 900):
            rows.append((f'ROND {r}  wght {w}', 'ΓΔΘΛΞΠΣΦΨΩ αβγδεζηθλξπσςφψω', 84, {'ROND': r, 'wght': w}))
    sheet(path, rows, out / 'greek-roundness.png')
    rows = []
    for o in (9, 14, 20, 32):
        rows.append((f'opsz {o}', PANGRAM, 84, {'opsz': o}))
    rows.append(('opsz 32  wght 900  ROND 100', 'ΚΑΛΗΜΕΡΑ Ωραία', 140, {'opsz': 32, 'wght': 900, 'ROND': 100}))
    rows.append(('opsz 32  wght 100  ROND 0', 'ΚΑΛΗΜΕΡΑ Ωραία', 140, {'opsz': 32, 'wght': 100, 'ROND': 0}))
    sheet(path, rows, out / 'greek-optical.png')
    rows = [('caps', CAPS, 120, {}), ('lowercase', LOWER, 120, {}), ('accents & punctuation', ACCENTS, 120, {}),
            ('beside Latin', MIXED, 120, {}), ('text', PANGRAM, 72, {}), ('text', WORDS, 72, {})]
    sheet(path, rows, out / 'greek-charset.png')
    # body text at a reading size
    text = ('Η Allo είναι μια φιλική γραμματοσειρά για οθόνες και διεπαφές. Έχει τρεις άξονες: μέγεθος, '
            'βάρος και στρογγυλότητα. Ξεσκεπάζω την ψυχοφθόρα βδελυγμία. ΑΒΓΔ 0123456789 €42,50 «εισαγωγικά»')
    img = Image.new('RGB', (1800, 520), BG)
    d = ImageDraw.Draw(img)
    y = 30
    for size, w in ((18, 400), (24, 400), (32, 400), (32, 700)):
        f = font(path, size, wght=w, opsz=min(max(size * 0.75, 9), 32))
        words, line = text.split(), ''
        for wd in words:
            if d.textlength(line + ' ' + wd, font=f) > 1720:
                d.text((40, y), line, font=f, fill=FG)
                y += int(size * 1.4)
                line = wd
            else:
                line = (line + ' ' + wd).strip()
        d.text((40, y), line, font=f, fill=FG)
        y += int(size * 2.2)
    img.save(out / 'greek-text.png')
    print(out / 'greek-text.png')


if __name__ == '__main__':
    main()
