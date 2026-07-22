"""Load a display module and normalize what render() gave back.

A display is a Python module exposing render(). Its return type selects
the level of control:

    scene.Node            -> laid out by the scene engine
    PIL.Image             -> one static frame
    iterable of PIL.Image -> an animation, frame by frame

There is no mode flag: the escape hatch is returning something
lower-level.
"""
import hashlib
import importlib.util
import pathlib

from PIL import Image

from . import encode as _encode
from . import scene as _scene
from .canvas import H, W
from .errors import LlmbytError


class DisplayError(LlmbytError):
    pass


def load_display(path):
    """Import the module at path and return its render callable."""
    path = pathlib.Path(path)
    if not path.exists():
        raise DisplayError(f"No such display: {path}")

    # Unique module name per path, so two displays that share a basename
    # cannot overwrite each other in sys.modules.
    digest = hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:8]
    spec = importlib.util.spec_from_file_location(
        f"llmbyt_display_{digest}", path)
    if spec is None or spec.loader is None:
        raise DisplayError(f"Cannot import {path} as a Python module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    render = getattr(module, "render", None)
    if render is None:
        raise DisplayError(
            f"{path} defines no render(). A display must expose a function "
            f"named render() returning a Scene node, a PIL Image, or an "
            f"iterable of PIL Images."
        )
    if not callable(render):
        raise DisplayError(f"{path}: render is {type(render).__name__}, "
                           f"not callable. It must be a function.")
    return render


def normalize(value, frame_ms=_encode.FRAME_MS_DEFAULT):
    """Turn a render() result into a list of 64x32 frames."""
    if isinstance(value, _scene.Node):
        return _scene.render_scene(value, frame_ms=frame_ms)

    if isinstance(value, Image.Image):
        frames = [value]
    elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        frames = list(value)
    else:
        raise DisplayError(
            f"render() returned {type(value).__name__}. It must return one "
            f"of: a Scene node (scene.Text, scene.Column, ...), a PIL Image, "
            f"or an iterable of PIL Images."
        )

    if not frames:
        raise DisplayError(
            "render() returned no frames. Return at least one PIL Image."
        )
    for i, f in enumerate(frames):
        if not isinstance(f, Image.Image):
            raise DisplayError(
                f"render() returned {type(f).__name__} at position {i}. "
                f"Every item must be a PIL Image."
            )
        if (f.width, f.height) != (W, H):
            raise DisplayError(
                f"Frame {i} is {f.width}x{f.height}, but the display is "
                f"{W}x{H}. Build frames on a llmbyt.canvas.Canvas, or resize "
                f"to exactly {W}x{H}."
            )
    return frames[:_encode.max_frames(frame_ms)]


def frames_from(path, frame_ms=_encode.FRAME_MS_DEFAULT):
    return normalize(load_display(path)(), frame_ms=frame_ms)
