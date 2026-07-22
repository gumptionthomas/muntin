import pytest

from llmbyt import canvas as cv
from llmbyt import scene as sc


def test_a_static_scene_renders_exactly_one_frame():
    frames = sc.render_scene(sc.Text("hello"))
    assert len(frames) == 1
    assert frames[0].size == (cv.W, cv.H)


def test_an_animated_scene_renders_one_frame_per_tick():
    child = sc.Column([sc.Text("x") for _ in range(8)])   # 48px tall
    m = sc.Marquee(child, axis="y", hold=2, speed=1)
    assert len(sc.render_scene(m)) == m.frame_count()


def test_render_clamps_to_the_device_budget():
    child = sc.Column([sc.Text("x") for _ in range(400)])
    frames = sc.render_scene(sc.Marquee(child, hold=1), frame_ms=100)
    assert len(frames) == 145


def test_frames_are_independent_images_not_the_same_object():
    child = sc.Column([sc.Text("x") for _ in range(8)])
    frames = sc.render_scene(sc.Marquee(child, hold=1))
    assert frames[0].tobytes() != frames[-1].tobytes()


def test_a_scene_wider_than_the_display_is_a_loud_error_naming_marquee():
    with pytest.raises(sc.SceneOverflowError) as e:
        sc.render_scene(sc.Text("x" * 40))
    msg = str(e.value)
    assert "160" in msg and "64" in msg and "Marquee" in msg


def test_a_scene_taller_than_the_display_is_a_loud_error():
    with pytest.raises(sc.SceneOverflowError, match="Marquee"):
        sc.render_scene(sc.Column([sc.Text("x") for _ in range(10)]))


def test_a_marquee_root_is_never_an_overflow():
    tall = sc.Column([sc.Text("x") for _ in range(10)])
    assert sc.render_scene(sc.Marquee(tall, hold=1))       # must not raise


def test_render_is_deterministic():
    node = sc.Column([sc.Text("a"), sc.Text("b")], gap=1)
    assert ([f.tobytes() for f in sc.render_scene(node)] ==
            [f.tobytes() for f in sc.render_scene(node)])
