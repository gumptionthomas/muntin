"""Frames -> animated WebP, with the device's duration ceiling enforced.

The Tidbyt silently stops rendering past ~15s, which is invisible from
looking at the device. So we clamp at 14500ms and hand the caller a
Budget describing exactly what was dropped. Silent truncation is the bug
class that costs an hour of confused iteration.
"""
import io
from dataclasses import dataclass

from .canvas import H, W
from .errors import LlmbytError

MAX_MS = 14500
FRAME_MS_DEFAULT = 100


class EncodeError(LlmbytError):
    pass


def _check_frame_ms(frame_ms: int) -> None:
    """Every public entry point funnels through here so the frame_ms
    contract (positive, non-zero) can't be bypassed by calling budget()
    or max_frames() directly instead of to_webp()."""
    if frame_ms <= 0:
        raise EncodeError(
            f"frame_ms must be positive, got {frame_ms}. Pass a frame_ms "
            f"greater than 0 (milliseconds per frame)."
        )


@dataclass(frozen=True)
class Budget:
    requested: int
    kept: int
    frame_ms: int

    @property
    def dropped(self) -> int:
        return self.requested - self.kept

    @property
    def fits(self) -> bool:
        return self.dropped == 0 and self.duration_ms <= MAX_MS

    @property
    def duration_ms(self) -> int:
        return self.kept * self.frame_ms

    def message(self) -> str | None:
        if self.fits:
            return None
        if self.dropped > 0:
            return (
                f"Animation is {self.requested} frames x {self.frame_ms}ms = "
                f"{self.requested * self.frame_ms}ms, over the {MAX_MS}ms device "
                f"ceiling. Kept the first {self.kept} frames and dropped "
                f"{self.dropped}. Shorten the animation or lower frame_ms."
            )
        return (
            f"Animation is {self.kept} frame(s) x {self.frame_ms}ms = "
            f"{self.duration_ms}ms, over the {MAX_MS}ms device ceiling. No "
            f"frames were dropped, but frame_ms alone exceeds the ceiling. "
            f"Lower frame_ms below {MAX_MS}ms."
        )


def max_frames(frame_ms: int = FRAME_MS_DEFAULT) -> int:
    _check_frame_ms(frame_ms)
    return max(1, MAX_MS // frame_ms)


def budget(n_frames: int, frame_ms: int = FRAME_MS_DEFAULT) -> Budget:
    _check_frame_ms(frame_ms)
    return Budget(n_frames, min(n_frames, max_frames(frame_ms)), frame_ms)


def to_webp(frames, frame_ms: int = FRAME_MS_DEFAULT) -> tuple[bytes, Budget]:
    """Encode frames. Returns (webp_bytes, Budget)."""
    _check_frame_ms(frame_ms)
    frames = list(frames)
    if not frames:
        raise EncodeError(
            "Cannot encode: no frames. render() must return a Scene, an "
            "Image, or a non-empty iterable of Images."
        )
    for i, f in enumerate(frames):
        if (f.width, f.height) != (W, H):
            raise EncodeError(
                f"frame {i} is {f.width}x{f.height}, but the display is "
                f"{W}x{H}. Every frame must be exactly {W}x{H}."
            )

    b = budget(len(frames), frame_ms)
    kept = [f.convert("RGB") for f in frames[:b.kept]]
    buf = io.BytesIO()
    kept[0].save(buf, format="WEBP", save_all=True, append_images=kept[1:],
                 duration=frame_ms, loop=0, lossless=True)
    return buf.getvalue(), b
