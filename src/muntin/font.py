"""BDF bitmap font loading.

Fixed-width faces only in v1 — both shipped fonts have a uniform advance.
Adding a face is dropping a .bdf into the fonts/ directory.

GLYPH CELLS: glyphs[ch] is a list of char_h rows, each a list of char_w
ints, 1 = ink. Every glyph is normalized into the same cell so all
characters share one baseline and grid.
"""
import os

from .errors import MuntinError

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DEFAULT = "tom-thumb"


class FontError(MuntinError):
    pass


class Font:
    def __init__(self, name, char_w, char_h, glyphs):
        self.name = name
        self.char_w = char_w
        self.char_h = char_h
        self.glyphs = glyphs
        self._blank = [[0] * char_w for _ in range(char_h)]

    def text_width(self, s: str) -> int:
        return len(s) * self.char_w

    def draw(self, draw, xy, s, fill) -> int:
        """Paint s at xy via a PIL ImageDraw. Returns the width advanced."""
        x0, y0 = xy
        for i, ch in enumerate(s):
            cell = self.glyphs.get(ch, self._blank)
            for ry, row in enumerate(cell):
                for rx, on in enumerate(row):
                    if on:
                        draw.point((x0 + i * self.char_w + rx, y0 + ry), fill=fill)
        return self.text_width(s)

    def __repr__(self):
        return f"<Font {self.name} {self.char_w}x{self.char_h}>"


def available() -> list[str]:
    return sorted(f[:-4] for f in os.listdir(FONT_DIR) if f.endswith(".bdf"))


_CACHE: dict[str, Font] = {}


def load(name: str = DEFAULT) -> Font:
    if name in _CACHE:
        return _CACHE[name]
    path = os.path.join(FONT_DIR, name + ".bdf")
    if not os.path.exists(path):
        raise FontError(
            f"No font named {name!r}. Available: {', '.join(available())}. "
            f"To add one, drop a fixed-width .bdf into {FONT_DIR}."
        )
    _CACHE[name] = _parse(name, path)
    return _CACHE[name]


def _parse(name, path) -> Font:
    with open(path, encoding="latin-1") as f:
        lines = f.readlines()

    char_h, descent = None, 0
    raw = {}                       # codepoint -> (bbx, [hex rows])
    code = dwidth = bbx = None
    rows, reading = [], False

    for line in lines:
        p = line.split()
        if not p:
            continue
        key = p[0]
        if key == "FONTBOUNDINGBOX":
            char_h = int(p[2])
            descent = -int(p[4])
        elif key == "ENCODING":
            code = int(p[1])
        elif key == "DWIDTH":
            dwidth = int(p[1])
        elif key == "BBX":
            bbx = tuple(int(x) for x in p[1:5])
        elif key == "BITMAP":
            reading, rows = True, []
        elif key == "ENDCHAR":
            reading = False
            if code is not None and 32 <= code < 127:
                raw[code] = (dwidth, bbx, rows)
            code = dwidth = bbx = None
        elif reading:
            rows.append(int(p[0], 16))

    if char_h is None:
        raise FontError(
            f"{path} has no FONTBOUNDINGBOX; not a usable BDF. "
            f"Add a FONTBOUNDINGBOX line with format: FONTBOUNDINGBOX width height xoff yoff."
        )
    if not raw:
        raise FontError(
            f"{path} defines no ASCII glyphs (codepoints 32-126). "
            f"Add glyphs for printable ASCII characters (space through tilde) to this BDF file."
        )

    # Cell width is the ASCII advance width. FONTBOUNDINGBOX lies for
    # tom-thumb (says 3, is 4), and non-ASCII glyphs may advance further.
    widths = {w for w, _, _ in raw.values() if w}
    if not widths:
        raise FontError(
            f"{path} has no DWIDTH on its ASCII glyphs. "
            f"Add a DWIDTH line to each glyph with format: DWIDTH width 0."
        )
    char_w = max(widths)

    glyphs = {chr(c): _cell(b, r, char_w, char_h, descent)
              for c, (_, b, r) in raw.items()}
    return Font(name, char_w, char_h, glyphs)


def _cell(bbx, rows, char_w, char_h, descent):
    """Place a glyph's ink box into the shared char_w x char_h cell."""
    w, h, xoff, yoff = bbx
    cell = [[0] * char_w for _ in range(char_h)]
    top = char_h - h - (descent + yoff)
    stride = 8 * ((w + 7) // 8)          # hex rows are byte-padded
    for r, val in enumerate(rows):
        y = top + r
        if not 0 <= y < char_h:
            continue
        for c in range(w):
            x = xoff + c
            if 0 <= x < char_w and (val >> (stride - 1 - c)) & 1:
                cell[y][x] = 1
    return cell
