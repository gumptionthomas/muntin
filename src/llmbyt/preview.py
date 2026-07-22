"""Frames -> an image a human or an agent can actually look at.

This is the core of the tool, not a convenience. Without it, a display is
authored blind and 'it looks great' is an unverifiable claim. Upscaling
makes individual pixels legible; the bezel makes the display edges visible
so overflow is obvious.
"""
import pathlib

from PIL import Image, ImageDraw

from .canvas import H, W
from .errors import LlmbytError

DEFAULT_SCALE = 8
GRID = (40, 40, 40)
BEZEL = (70, 70, 70)


class PreviewError(LlmbytError):
    pass


def _check_frame_ms(frame_ms: int) -> None:
    """Mirrors encode._check_frame_ms: every public entry point funnels
    through here so the frame_ms contract (positive, non-zero) can't be
    bypassed."""
    if frame_ms <= 0:
        raise PreviewError(
            f"frame_ms must be positive, got {frame_ms}. Pass a frame_ms "
            f"greater than 0 (milliseconds per frame)."
        )


def write(frames, path, scale=DEFAULT_SCALE, grid=True, frame_ms=100):
    """Write frames to path. Returns the pathlib.Path actually written."""
    _check_frame_ms(frame_ms)
    frames = list(frames)
    if not frames:
        raise PreviewError(
            "Cannot preview: no frames. render() must return a Scene, an "
            "Image, or a non-empty iterable of Images."
        )
    for i, f in enumerate(frames):
        if (f.width, f.height) != (W, H):
            raise PreviewError(
                f"frame {i} is {f.width}x{f.height}, but the display is "
                f"{W}x{H}. Every frame must be exactly {W}x{H}. Resize or "
                f"crop the frame to {W}x{H} before passing it to preview.write()."
            )
    if not isinstance(scale, int):
        raise PreviewError(
            f"scale must be an integer, got {scale!r} "
            f"({type(scale).__name__}). Pass a whole number of "
            f"pixels-per-cell."
        )
    if scale < 1:
        raise PreviewError(
            f"scale must be >= 1, got {scale}. Pass an integer scale of 1 "
            f"or greater."
        )

    path = pathlib.Path(path)
    if not path.suffix:
        path = path.with_suffix(".png" if len(frames) == 1 else ".gif")
    path.parent.mkdir(parents=True, exist_ok=True)

    shots = [_decorate(f, scale, grid) for f in frames]
    if len(shots) == 1:
        shots[0].save(path)
    else:
        shots[0].save(path, save_all=True, append_images=shots[1:],
                      duration=frame_ms, loop=0)
    return path


def _decorate(frame, scale, grid):
    big = frame.convert("RGB").resize(
        (frame.width * scale, frame.height * scale), Image.NEAREST)
    out = Image.new("RGB", (big.width + 2, big.height + 2), BEZEL)
    out.paste(big, (1, 1))
    if grid and scale >= 4:
        d = ImageDraw.Draw(out)
        for x in range(scale, big.width, scale):
            d.line([(x, 1), (x, big.height)], fill=GRID)
        for y in range(scale, big.height, scale):
            d.line([(1, y), (big.width, y)], fill=GRID)
    return out
