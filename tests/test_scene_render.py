import pytest

from llmbyt import canvas as cv
from llmbyt import scene as sc


def test_a_static_scene_renders_exactly_one_frame():
    frames, _ = sc.render_scene(sc.Text("hello"))
    assert len(frames) == 1
    assert frames[0].size == (cv.W, cv.H)


def test_an_animated_scene_renders_one_frame_per_tick():
    child = sc.Column([sc.Text("x") for _ in range(8)])   # 48px tall
    m = sc.Marquee(child, axis="y", hold=2, speed=1)
    frames, _ = sc.render_scene(m)
    assert len(frames) == m.frame_count()


def test_render_clamps_to_the_device_budget():
    child = sc.Column([sc.Text("x") for _ in range(400)])
    frames, _ = sc.render_scene(sc.Marquee(child, hold=1), frame_ms=100)
    assert len(frames) == 145


def test_the_budget_reports_the_count_the_scene_asked_for():
    """render_scene renders at most the budget, but the Budget it hands
    back must still name the full count the scene wanted -- that number
    is the only thing that can tell an agent how much it lost."""
    child = sc.Column([sc.Text("x") for _ in range(400)])   # 2400px tall
    node = sc.Marquee(child, hold=1)
    frames, budget = sc.render_scene(node, frame_ms=100)
    assert node.frame_count() == 2369
    assert budget.requested == 2369
    assert budget.kept == 145 == len(frames)
    assert budget.dropped == 2224
    assert budget.fits is False
    assert "2224" in budget.message()


def test_an_over_budget_scene_never_renders_the_frames_it_would_drop():
    """Requirement, not an optimization: a scene asking for 10,000
    frames must not paint 10,000 canvases only to throw 9,855 away."""
    drawn = []

    class Greedy(sc.Node):
        def measure(self):
            return (1, 1)

        def draw(self, canvas, box, t):
            drawn.append(t)

        def frame_count(self):
            return 10_000

    frames, budget = sc.render_scene(Greedy(), frame_ms=100)
    assert budget.requested == 10_000
    assert len(drawn) == 145 == len(frames)


def test_frames_are_independent_images_not_the_same_object():
    child = sc.Column([sc.Text("x") for _ in range(8)])
    frames, _ = sc.render_scene(sc.Marquee(child, hold=1))
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
    frames, _ = sc.render_scene(sc.Marquee(tall, hold=1))  # must not raise
    assert frames


def test_render_is_deterministic():
    node = sc.Column([sc.Text("a"), sc.Text("b")], gap=1)
    assert ([f.tobytes() for f in sc.render_scene(node)[0]] ==
            [f.tobytes() for f in sc.render_scene(node)[0]])
