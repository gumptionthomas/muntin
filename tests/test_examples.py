import pathlib

import pytest

from llmbyt import canvas as cv
from llmbyt import runner

EXAMPLES = sorted((pathlib.Path(__file__).parent.parent / "examples")
                  .glob("*.py"))


def test_there_are_examples():
    assert len(EXAMPLES) >= 4


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_renders_to_valid_frames(path):
    frames, _ = runner.frames_from(path)
    assert frames
    assert all(f.size == (cv.W, cv.H) for f in frames)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_draws_something_visible(path):
    first = runner.frames_from(path)[0][0]
    assert first.convert("RGB").getbbox() is not None, (
        f"{path.name} renders an entirely black first frame")


def test_the_raw_escape_hatch_example_actually_animates():
    frames, _ = runner.frames_from(
        pathlib.Path(__file__).parent.parent / "examples" / "bounce.py")
    assert len(frames) > 1
    assert frames[0].tobytes() != frames[1].tobytes()
