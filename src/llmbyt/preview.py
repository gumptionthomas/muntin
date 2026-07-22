"""Frames -> an image a human or an agent can actually look at.

This is the core of the tool, not a convenience. Without it, a display is
authored blind and 'it looks great' is an unverifiable claim. Upscaling
makes individual pixels legible; the bezel makes the display edges visible
so overflow is obvious.
"""
import pathlib

from PIL import Image, ImageDraw

from .canvas import check_frame_sizes
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


def candidates(path):
    """Every file a preview run could leave at this output stem.

    write() picks .png or .gif from the frame count, so one stem owns two
    possible artifacts.
    """
    path = pathlib.Path(path)
    try:
        return [path, path.with_suffix(".png"), path.with_suffix(".gif")]
    except ValueError:                      # no name to hang a suffix on
        return [path]


def clear(path):
    """Delete any artifact a previous run left at this output stem.

    Call this BEFORE rendering, not after. A render that raises used to
    leave the last successful preview sitting on disk, and an agent
    iterating against a stale PNG cannot tell that it is stale -- it
    reads the error, looks at the image, and sees the bug it just fixed.
    Both extensions go, so an animated run does not leave its .gif
    beside the .png a later static run writes.
    """
    failed = None
    for c in candidates(path):
        try:
            c.unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            failed = (c, e.strerror or type(e).__name__)
            break
    if failed is not None:
        target, reason = failed
        raise PreviewError(
            f"Cannot remove the previous preview at {target} ({reason}). "
            f"llmbyt clears the old artifact before rendering so a failed "
            f"render can never leave a stale image behind. Delete it by "
            f"hand, or pass a different -o path."
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
    check_frame_sizes(frames, PreviewError)
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
