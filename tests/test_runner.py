import sys

import pytest
from PIL import Image

from llmbyt import canvas as cv
from llmbyt import runner


def display(tmp_path, body, name="d.py"):
    p = tmp_path / name
    p.write_text(body)
    return p


def test_loads_and_calls_render(tmp_path):
    p = display(tmp_path, """
from llmbyt import scene as sc
def render():
    return sc.Text("hi")
""")
    frames = runner.frames_from(p)
    assert len(frames) == 1
    assert frames[0].size == (cv.W, cv.H)


def test_a_scene_node_is_rendered_through_the_scene_engine(tmp_path):
    p = display(tmp_path, """
from llmbyt import scene as sc
def render():
    return sc.Marquee(sc.Column([sc.Text("x") for _ in range(8)]), hold=2)
""")
    assert len(runner.frames_from(p)) > 1


def test_a_single_image_becomes_one_frame(tmp_path):
    p = display(tmp_path, """
from PIL import Image
def render():
    return Image.new("RGB", (64, 32), (255, 0, 0))
""")
    assert len(runner.frames_from(p)) == 1


def test_a_list_of_images_becomes_an_animation(tmp_path):
    p = display(tmp_path, """
from PIL import Image
def render():
    return [Image.new("RGB", (64, 32)) for _ in range(4)]
""")
    assert len(runner.frames_from(p)) == 4


def test_a_generator_of_images_is_accepted(tmp_path):
    p = display(tmp_path, """
from PIL import Image
def render():
    for i in range(3):
        yield Image.new("RGB", (64, 32), (i * 10, 0, 0))
""")
    assert len(runner.frames_from(p)) == 3


def test_raw_frames_are_clamped_to_the_device_budget(tmp_path):
    p = display(tmp_path, """
from PIL import Image
def render():
    return [Image.new("RGB", (64, 32)) for _ in range(500)]
""")
    assert len(runner.frames_from(p, frame_ms=100)) == 145


def test_a_wrong_sized_raw_frame_names_the_size(tmp_path):
    p = display(tmp_path, """
from PIL import Image
def render():
    return Image.new("RGB", (10, 10))
""")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    assert "10x10" in str(e.value) and "64x32" in str(e.value)


def test_a_bad_return_type_lists_the_three_accepted_forms(tmp_path):
    p = display(tmp_path, "def render():\n    return 42\n")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    msg = str(e.value)
    assert "int" in msg and "Scene" in msg and "Image" in msg


def test_returning_none_is_a_loud_error(tmp_path):
    p = display(tmp_path, "def render():\n    pass\n")
    with pytest.raises(runner.DisplayError, match="NoneType"):
        runner.frames_from(p)


def test_an_empty_list_is_a_loud_error(tmp_path):
    p = display(tmp_path, "def render():\n    return []\n")
    with pytest.raises(runner.DisplayError, match="no frames"):
        runner.frames_from(p)


def test_a_module_without_render_says_what_is_required(tmp_path):
    p = display(tmp_path, "def draw():\n    pass\n")
    with pytest.raises(runner.DisplayError) as e:
        runner.load_display(p)
    assert "render()" in str(e.value)


def test_a_non_callable_render_is_rejected(tmp_path):
    p = display(tmp_path, "render = 5\n")
    with pytest.raises(runner.DisplayError, match="not callable"):
        runner.load_display(p)


def test_a_missing_file_names_the_path(tmp_path):
    with pytest.raises(runner.DisplayError, match="missing.py"):
        runner.load_display(tmp_path / "missing.py")


def test_an_import_error_in_the_display_propagates(tmp_path):
    p = display(tmp_path, "import nonexistent_module_xyz\n")
    with pytest.raises(ModuleNotFoundError):
        runner.load_display(p)


def test_a_dict_names_dict_and_the_three_accepted_forms(tmp_path):
    p = display(tmp_path, "def render():\n    return {'a': 1}\n")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    msg = str(e.value)
    assert "dict" in msg and "Scene" in msg and "Image" in msg
    # Must not be misdispatched into the per-item iterable message.
    assert "position 0" not in msg


def test_other_mapping_types_are_also_rejected_like_dict(tmp_path):
    p = display(tmp_path, """
from collections import OrderedDict
def render():
    return OrderedDict(a=1)
""")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    msg = str(e.value)
    assert "Scene" in msg and "Image" in msg
    assert "position 0" not in msg


def test_a_set_of_images_cannot_even_be_constructed(tmp_path):
    # Not a runner concern: PIL.Image is unhashable, so a set literally
    # containing frame Images can't exist. Python raises its own clear
    # error at the user's return statement before normalize() runs.
    p = display(tmp_path, """
from PIL import Image
def render():
    return {Image.new("RGB", (64, 32))}
""")
    with pytest.raises(TypeError, match="unhashable"):
        runner.frames_from(p)


def test_a_set_of_non_images_names_set_and_the_three_accepted_forms(tmp_path):
    p = display(tmp_path, "def render():\n    return {'a', 'b'}\n")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    msg = str(e.value)
    assert "set" in msg and "Scene" in msg and "Image" in msg
    # Must not be misdispatched into the per-item iterable message.
    assert "position 0" not in msg


def test_a_frozenset_of_non_images_names_frozenset_and_the_three_accepted_forms(tmp_path):
    p = display(tmp_path, "def render():\n    return frozenset(['a', 'b'])\n")
    with pytest.raises(runner.DisplayError) as e:
        runner.frames_from(p)
    msg = str(e.value)
    assert "frozenset" in msg and "Scene" in msg and "Image" in msg
    # Must not be misdispatched into the per-item iterable message.
    assert "position 0" not in msg


def test_a_class_defined_in_a_display_module_can_be_pickled(tmp_path):
    p = display(tmp_path, """
import pickle
from dataclasses import dataclass
from PIL import Image

@dataclass
class State:
    value: int

def render():
    pickle.dumps(State(1))
    return Image.new("RGB", (64, 32))
""")
    # Must not raise PicklingError: the module needs to be registered in
    # sys.modules before exec_module runs, or dataclasses/pickle can't
    # find it by name.
    runner.frames_from(p)


def test_sys_modules_does_not_retain_a_module_that_failed_to_exec(tmp_path):
    p = display(tmp_path, "raise ValueError('boom')\n")
    before = set(sys.modules)
    with pytest.raises(ValueError):
        runner.load_display(p)
    after = set(sys.modules)
    assert after - before == set()


def test_a_missing_display_says_what_to_check(tmp_path):
    with pytest.raises(runner.DisplayError) as e:
        runner.load_display(tmp_path / "missing.py")
    msg = str(e.value)
    assert "missing.py" in msg
    assert "check" in msg.lower() or "point" in msg.lower()


def test_a_directory_path_names_the_fix(tmp_path):
    d = tmp_path / "somedir"
    d.mkdir()
    with pytest.raises(runner.DisplayError) as e:
        runner.load_display(d)
    msg = str(e.value)
    assert ".py" in msg


def test_a_wrong_extension_names_the_fix(tmp_path):
    p = display(tmp_path, "def render():\n    pass\n", name="d.txt")
    with pytest.raises(runner.DisplayError) as e:
        runner.load_display(p)
    msg = str(e.value)
    assert ".py" in msg


def test_two_displays_with_the_same_basename_do_not_collide(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "d.py").write_text(
        'from PIL import Image\n'
        'def render():\n    return Image.new("RGB", (64, 32), (255, 0, 0))\n')
    (tmp_path / "b" / "d.py").write_text(
        'from PIL import Image\n'
        'def render():\n    return Image.new("RGB", (64, 32), (0, 255, 0))\n')
    fa = runner.frames_from(tmp_path / "a" / "d.py")
    fb = runner.frames_from(tmp_path / "b" / "d.py")
    assert fa[0].getpixel((0, 0)) != fb[0].getpixel((0, 0))
