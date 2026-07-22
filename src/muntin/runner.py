"""Load a display module and normalize what render() gave back.

A display is a Python module exposing render(). Its return type selects
the level of control:

    scene.Node            -> laid out by the scene engine
    PIL.Image             -> one static frame
    iterable of PIL.Image -> an animation, frame by frame

There is no mode flag: the escape hatch is returning something
lower-level.
"""
import collections.abc
import hashlib
import importlib.util
import pathlib
import sys

from PIL import Image

from . import encode as _encode
from . import scene as _scene
from .canvas import check_frame_sizes
from .errors import MuntinError


class DisplayError(MuntinError):
    pass


def load_display(path):
    """Import the module at path and return its render callable."""
    path = pathlib.Path(path)
    if not path.exists():
        raise DisplayError(
            f"No such display: {path}. Check the path — it must point to "
            f"an existing .py file that defines render()."
        )

    # Unique module name per path, so two displays that share a basename
    # cannot overwrite each other in sys.modules.
    digest = hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:8]
    name = f"muntin_display_{digest}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        found = "a directory" if path.is_dir() else (path.suffix or "no extension")
        raise DisplayError(
            f"Cannot import {path} as a Python module (found {found}). "
            f"Displays must be a .py file — point to a Python source file."
        )
    module = importlib.util.module_from_spec(spec)
    # Register before exec, matching the standard importlib recipe: a
    # dataclass (or anything else pickle-by-reference) defined in the
    # display module needs `sys.modules[name]` to resolve back to it.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Don't leave a half-initialized module behind for a later
        # load_display(same path) to trip over.
        del sys.modules[name]
        raise

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
    """Turn a render() result into (list of 64x32 frames, encode.Budget).

    The Budget is what lets the CLI say how many frames were dropped and
    why. It is built by encode.take() from the count render() actually
    produced, never from the already-shortened list.
    """
    if isinstance(value, _scene.Node):
        return _scene.render_scene(value, frame_ms=frame_ms)

    # A dict has __iter__ and isn't str/bytes, so without this guard it
    # falls into the iterable branch and silently becomes list(dict) --
    # its *keys*. Returning a config/state dict by mistake is plausible,
    # so it needs to land on the same three-accepted-forms message as
    # any other wrong return type, instead of a misleading per-item
    # error that names the type of the first key and never says "dict".
    #
    # A set or frozenset must be rejected because animation frames are
    # inherently ordered, and an unordered container cannot represent a
    # valid frame sequence. This also prevents the same bug as above:
    # if a user returns set(['a', 'b']), the error would incorrectly
    # name 'str' (the first element's type) instead of 'set'. While
    # PIL.Image is unhashable (so a set of actual Images cannot be
    # constructed), that's not the only reason for rejection -- the
    # ordering requirement applies to any set, even if it contained
    # ordered content.
    not_a_sequence = (str, bytes, collections.abc.Mapping, set, frozenset)
    if isinstance(value, Image.Image):
        frames = [value]
    elif hasattr(value, "__iter__") and not isinstance(value, not_a_sequence):
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
    check_frame_sizes(frames, DisplayError)
    return _encode.take(lambda n: frames[:n], len(frames), frame_ms)


def frames_from(path, frame_ms=_encode.FRAME_MS_DEFAULT):
    """Load path's render() and normalize it. Returns (frames, Budget)."""
    return normalize(load_display(path)(), frame_ms=frame_ms)
