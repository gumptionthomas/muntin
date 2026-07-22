"""The declarative layer: a small widget vocabulary over the canvas.

CONTRACT -- every node implements exactly:

    measure() -> (w, h)            intrinsic size in pixels
    draw(canvas, box, t) -> None   paint into box at frame index t
    frame_count() -> int           how many frames this node wants (default 1)

box is (x, y, w, h) in absolute canvas coordinates. draw() must be a pure
function of (box, t) -- no state between frames. That is what makes golden
tests meaningful and animation restartable from any frame.
"""
from . import font as _font
from .canvas import WHITE
from .errors import LlmbytError

ALIGNMENTS = ("start", "center", "end")


class SceneError(LlmbytError):
    pass


def _check_alignment(name, value):
    if value not in ALIGNMENTS:
        raise SceneError(
            f"{name}={value!r} is not valid. Use one of: "
            f"{', '.join(ALIGNMENTS)}."
        )
    return value


def _offset(mode, available, used):
    slack = max(0, available - used)
    return {"start": 0, "center": slack // 2, "end": slack}[mode]


class Node:
    def measure(self):
        raise NotImplementedError

    def draw(self, canvas, box, t):
        raise NotImplementedError

    def frame_count(self):
        return 1


class Text(Node):
    def __init__(self, s, font=None, color=WHITE):
        self.s = str(s)
        self.font = _font.load(font) if isinstance(font, str) else (
            font or _font.load())
        self.color = color

    def measure(self):
        return (self.font.text_width(self.s), self.font.char_h)

    def draw(self, canvas, box, t):
        canvas.text((box[0], box[1]), self.s, font=self.font, color=self.color)


class _Container(Node):
    def __init__(self, children, gap=0, align="start", justify="start"):
        self.children = list(children)
        self.gap = gap
        self.align = _check_alignment("align", align)
        self.justify = _check_alignment("justify", justify)

    def frame_count(self):
        return max((c.frame_count() for c in self.children), default=1)

    def _sizes(self):
        return [c.measure() for c in self.children]

    def _gaps(self):
        return self.gap * max(0, len(self.children) - 1)


class Column(_Container):
    """Children stacked top to bottom. align = horizontal, justify = vertical."""

    def measure(self):
        sizes = self._sizes()
        if not sizes:
            return (0, 0)
        return (max(w for w, _ in sizes),
                sum(h for _, h in sizes) + self._gaps())

    def draw(self, canvas, box, t):
        x, y, bw, bh = box
        _, used = self.measure()
        cy = y + _offset(self.justify, bh, used)
        for child, (cw, ch) in zip(self.children, self._sizes()):
            cx = x + _offset(self.align, bw, cw)
            child.draw(canvas, (cx, cy, cw, ch), t)
            cy += ch + self.gap


class Row(_Container):
    """Children laid left to right. align = vertical, justify = horizontal."""

    def measure(self):
        sizes = self._sizes()
        if not sizes:
            return (0, 0)
        return (sum(w for w, _ in sizes) + self._gaps(),
                max(h for _, h in sizes))

    def draw(self, canvas, box, t):
        x, y, bw, bh = box
        used, _ = self.measure()
        cx = x + _offset(self.justify, bw, used)
        for child, (cw, ch) in zip(self.children, self._sizes()):
            cy = y + _offset(self.align, bh, ch)
            child.draw(canvas, (cx, cy, cw, ch), t)
            cx += cw + self.gap


class Stack(Node):
    """Children overlaid at the same origin. Last child paints on top."""

    def __init__(self, children):
        self.children = list(children)

    def measure(self):
        sizes = [c.measure() for c in self.children]
        if not sizes:
            return (0, 0)
        return (max(w for w, _ in sizes), max(h for _, h in sizes))

    def frame_count(self):
        return max((c.frame_count() for c in self.children), default=1)

    def draw(self, canvas, box, t):
        for child in self.children:
            cw, ch = child.measure()
            child.draw(canvas, (box[0], box[1], cw, ch), t)
