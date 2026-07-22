"""A 64x32 drawing surface and the palette that survives an LED panel.

Boxes are always (x, y, w, h). Drawing outside the surface clips rather
than raising -- Marquee depends on being able to paint a child that is
larger than its viewport.
"""
from PIL import Image, ImageDraw

from . import font as _font

W, H = 64, 32

# Saturated primaries read cleanly on the LEDs. Mid-grays and pastels
# turn to mush at any distance, and pure blue reads as near-black --
# hence BLUE is lifted off (0, 0, 255). See CRAFT.md.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DIM = (90, 90, 90)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 80, 255)
YELLOW = (255, 200, 0)
ORANGE = (255, 110, 0)
CYAN = (0, 220, 220)
MAGENTA = (255, 0, 180)

PALETTE = {
    "black": BLACK, "white": WHITE, "dim": DIM, "red": RED, "green": GREEN,
    "blue": BLUE, "yellow": YELLOW, "orange": ORANGE, "cyan": CYAN,
    "magenta": MAGENTA,
}


class Canvas:
    def __init__(self, w=W, h=H, bg=BLACK):
        self.img = Image.new("RGB", (w, h), bg)
        self._d = ImageDraw.Draw(self.img)

    @property
    def width(self):
        return self.img.width

    @property
    def height(self):
        return self.img.height

    def pixel(self, xy, color):
        x, y = xy
        if 0 <= x < self.width and 0 <= y < self.height:
            self._d.point((x, y), fill=color)

    def line(self, xy0, xy1, color):
        self._d.line([xy0, xy1], fill=color)

    def rect(self, box, color, fill=False):
        x, y, w, h = box
        if w <= 0 or h <= 0:
            return
        self._d.rectangle([x, y, x + w - 1, y + h - 1],
                          fill=color if fill else None,
                          outline=None if fill else color)

    def fill(self, color):
        self._d.rectangle([0, 0, self.width - 1, self.height - 1], fill=color)

    def text(self, xy, s, font=None, color=WHITE) -> int:
        f = _resolve_font(font)
        return f.draw(self._d, xy, s, color)

    def sprite(self, img, xy):
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            self.img.paste(img, tuple(xy), img)
        else:
            self.img.paste(img.convert("RGB"), tuple(xy))

    def snapshot(self):
        return self.img.copy()


def _resolve_font(font):
    if font is None:
        return _font.load()
    if isinstance(font, str):
        return _font.load(font)
    return font
