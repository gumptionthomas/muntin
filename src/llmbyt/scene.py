"""The declarative layer: a small widget vocabulary over the canvas.

CONTRACT -- every node implements exactly:

    measure() -> (w, h)            intrinsic size in pixels
    draw(canvas, box, t) -> None   paint into box at frame index t
    frame_count() -> int           how many frames this node wants (default 1)

box is (x, y, w, h) in absolute canvas coordinates. draw() must be a pure
function of (box, t) -- no state between frames. That is what makes golden
tests meaningful and animation restartable from any frame.
"""
import pathlib

from PIL import Image

from . import encode as _encode
from . import font as _font
from .canvas import GREEN, H, W, Canvas, WHITE
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
        if gap < 0:
            raise SceneError(
                f"gap={gap!r} is not valid. gap must be >= 0 -- a negative "
                f"gap would drive the main-axis measure() negative. Pass "
                f"gap=0 or a positive integer."
            )
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
            child.draw(canvas, box, t)


# --- animation, images, data ----------------------------------------

AXES = ("x", "y")
FITS = ("none", "contain", "cover")


class SceneOverflowError(SceneError):
    pass


class Marquee(Node):
    """A viewport that scrolls an oversized child past the display.

    measure() reports the clamped viewport size, not the child's size --
    that is what makes a Marquee root exempt from the overflow check.
    """

    def __init__(self, child, axis="y", hold=14, speed=1):
        if axis not in AXES:
            raise SceneError(
                f"axis={axis!r} is not valid. Use one of: "
                f"{', '.join(AXES)} ('x' scrolls horizontally, 'y' "
                f"scrolls vertically)."
            )
        if speed < 1:
            raise SceneError(
                f"speed={speed!r} is not valid. speed must be >= 1 -- it "
                f"is the pixels advanced per frame, and 0 or negative "
                f"would mean the marquee never reaches the far edge. "
                f"Pass an integer speed of 1 or greater."
            )
        if hold < 0:
            raise SceneError(
                f"hold={hold!r} is not valid. hold must be >= 0 -- it is "
                f"the number of static frames before scrolling starts, "
                f"and a negative count is meaningless. Pass hold=0 or a "
                f"positive integer."
            )
        self.child = child
        self.axis = axis
        self.hold = hold
        self.speed = speed

    def _travel(self):
        cw, ch = self.child.measure()
        return max(0, (cw - W) if self.axis == "x" else (ch - H))

    def measure(self):
        cw, ch = self.child.measure()
        return (min(cw, W), min(ch, H))

    def frame_count(self):
        travel = self._travel()
        if not travel:
            return max(1, self.hold)
        return self.hold + -(-travel // self.speed)

    def draw(self, canvas, box, t):
        x, y, _, _ = box
        step = t - self.hold
        moved = (step + 1) * self.speed if step >= 0 else 0
        off = min(moved, self._travel())
        cw, ch = self.child.measure()
        if self.axis == "x":
            self.child.draw(canvas, (x - off, y, cw, ch), t)
        else:
            self.child.draw(canvas, (x, y - off, cw, ch), t)


class Sprite(Node):
    """A bitmap. fit=none|contain|cover; never upscales past the display."""

    def __init__(self, image_or_path, fit="none"):
        if fit not in FITS:
            raise SceneError(
                f"fit={fit!r} is not valid. Use one of: {', '.join(FITS)}."
            )
        if isinstance(image_or_path, (str, pathlib.Path)):
            path = pathlib.Path(image_or_path)
            if not path.exists():
                raise SceneError(
                    f"No such image: {path}. Sprite(...) needs a path to "
                    f"an existing image file, or a PIL.Image passed in "
                    f"directly. Check the path, or pass an Image object."
                )
            try:
                img = Image.open(path)
                img.load()
            except Exception as e:
                # Covers every way Image.open()/load() can fail on a path
                # that exists but isn't a usable image: unidentifiable or
                # corrupt/truncated files (OSError subclasses), decompression
                # bombs (PIL.Image.DecompressionBombError, not an OSError),
                # memory issues, and permission errors. The try block
                # contains only pure PIL operations with no llmbyt logic,
                # so a broad catch is safe and future-proof.
                raise SceneError(
                    f"{path} exists but is not a readable image ({e}). "
                    f"Sprite(...) needs a valid image file (PNG, JPEG, "
                    f"GIF, etc) -- check that the path points at an "
                    f"actual image and not a directory, and that the "
                    f"file isn't corrupt, truncated, or permission-"
                    f"restricted. Or pass a PIL.Image object directly "
                    f"instead of a path."
                ) from e
        else:
            img = image_or_path
        self.img = _fit(img.convert("RGB"), fit)

    def measure(self):
        return (self.img.width, self.img.height)

    def draw(self, canvas, box, t):
        canvas.sprite(self.img, (box[0], box[1]))


def _fit(img, mode):
    if mode == "none" or (img.width <= W and img.height <= H
                          and mode == "contain"):
        return img
    if mode == "contain":
        scale = min(W / img.width, H / img.height)
        size = (max(1, round(img.width * scale)),
                max(1, round(img.height * scale)))
        return img.resize(size, Image.LANCZOS)
    # cover: fill the display, centre-crop the overflow
    scale = max(W / img.width, H / img.height)
    big = img.resize((max(W, round(img.width * scale)),
                      max(H, round(img.height * scale))), Image.LANCZOS)
    left, top = (big.width - W) // 2, (big.height - H) // 2
    return big.crop((left, top, left + W, top + H))


class Plot(Node):
    """A sparkline: one column per value, min at the bottom, max at the top."""

    DEFAULT_H = 8

    def __init__(self, values, color=GREEN):
        self.values = [float(v) for v in values]
        if not self.values:
            raise SceneError(
                "Plot has no values. A sparkline needs at least one "
                "point to measure or draw -- pass a non-empty sequence "
                "of numbers."
            )
        self.color = color

    def measure(self):
        return (len(self.values), self.DEFAULT_H)

    def draw(self, canvas, box, t):
        x, y, bw, bh = box
        lo, hi = min(self.values), max(self.values)
        span = (hi - lo) or 1.0
        rows = max(1, bh - 1)
        pts = [(x + i, y + rows - round((v - lo) / span * rows))
               for i, v in enumerate(self.values)]
        if len(pts) == 1:
            canvas.pixel(pts[0], self.color)
            return
        for a, b in zip(pts, pts[1:]):
            canvas.line(a, b, self.color)


def render_scene(node, frame_ms=_encode.FRAME_MS_DEFAULT):
    """Render a scene tree to a list of 64x32 frames."""
    w, h = node.measure()
    if w > W or h > H:
        raise SceneOverflowError(
            f"Scene measures {w}x{h}, larger than the {W}x{H} display. "
            f"Shorten the content, or wrap it in Marquee(...) to scroll it."
        )
    n = min(max(1, node.frame_count()), _encode.max_frames(frame_ms))
    frames = []
    for t in range(n):
        c = Canvas()
        node.draw(c, (0, 0, W, H), t)
        frames.append(c.snapshot())
    return frames
