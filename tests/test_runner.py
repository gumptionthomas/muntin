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
