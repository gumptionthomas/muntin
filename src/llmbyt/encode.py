"""Frames -> animated WebP, with the device's duration ceiling enforced.

The Tidbyt silently stops rendering past ~15s, which is invisible from
looking at the device. So we clamp at 14500ms and hand the caller a
Budget describing exactly what was dropped. Silent truncation is the bug
class that costs an hour of confused iteration.
"""
import io
from dataclasses import dataclass

from .canvas import check_frame_sizes
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


def take(produce, requested: int, frame_ms: int = FRAME_MS_DEFAULT
         ) -> tuple[list, Budget]:
    """THE ONLY PLACE IN llmbyt THAT CLAMPS A FRAME COUNT.

    Three layers used to clamp independently -- scene.render_scene,
    runner.normalize, and to_webp below -- and only the last one built a
    Budget. By the time it ran the list had already been shortened twice,
    so requested == kept, fits was always True, message() always None,
    and the CLI's warning branch was unreachable. Over-budget animations
    were silently truncated on every path.

    Now every clamp routes through here, and here alone:

        requested   what the display actually asked for. This, not the
                    post-clamp length, is what lands in the Budget.
        produce(n)  called once with the number of frames to actually
                    materialize, so a scene that wants 10,000 frames
                    renders the budget rather than the 10,000 and then
                    throwing 9,855 of them away.

    The Budget travels back up to the CLI, which reports it on `preview`
    as well as `show`.
    """
    b = budget(requested, frame_ms)
    frames = list(produce(b.kept))
    if len(frames) != b.kept:
        raise EncodeError(
            f"produce(n) must return exactly n frames: called with "
            f"n={b.kept} (the Budget's kept count) but it returned "
            f"{len(frames)}. Fix the producer passed to take() so it "
            f"returns exactly the requested count."
        )
    return frames, b


def to_webp(frames, frame_ms: int = FRAME_MS_DEFAULT) -> tuple[bytes, Budget]:
    """Encode frames. Returns (webp_bytes, Budget).

    The pipeline hands this already-budgeted frames, but to_webp is also
    a public entry point, so it still enforces the ceiling -- through
    take(), not with a clamp of its own.
    """
    _check_frame_ms(frame_ms)
    frames = list(frames)
    if not frames:
        raise EncodeError(
            "Cannot encode: no frames. render() must return a Scene, an "
            "Image, or a non-empty iterable of Images."
        )
    check_frame_sizes(frames, EncodeError)

    kept, b = take(lambda n: frames[:n], len(frames), frame_ms)
    kept = [f.convert("RGB") for f in kept]
    buf = io.BytesIO()
    kept[0].save(buf, format="WEBP", save_all=True, append_images=kept[1:],
                 duration=frame_ms, loop=0, lossless=True)
    return buf.getvalue(), b
