"""celebrate.py varies between runs, which the other example tests cannot
cover: test_example_draws_something_visible samples exactly one render,
and a varying example that can produce a blank frame would turn that into
an intermittent failure. These pin the invariants that make the variation
safe."""
import importlib.util
import pathlib

from muntin import canvas as cv
from muntin import runner

CELEBRATE = pathlib.Path(__file__).parent.parent / "examples" / "celebrate.py"


def _module():
    spec = importlib.util.spec_from_file_location("celebrate", CELEBRATE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_every_run_draws_something_on_the_first_frame():
    """The example picks its message and palette at random. Every
    combination it can reach must paint frame 0, or the shared example
    test flakes roughly one run in N."""
    for _ in range(50):
        frames, _ = runner.frames_from(CELEBRATE)
        assert frames[0].convert("RGB").getbbox() is not None


def test_the_message_varies_between_runs():
    """If it never varies, the example is a template to copy rather than
    a display composed for a moment -- which is the whole point of it."""
    seen = set()
    for _ in range(60):
        m = _module()
        node = m.render()
        seen.add(_headline(node))
    assert len(seen) > 1


def _headline(node):
    """Pull the Text string out of the scene, wherever it sits."""
    if hasattr(node, "s"):
        return node.s
    for attr in ("children", "child"):
        child = getattr(node, attr, None)
        if child is None:
            continue
        for c in (child if isinstance(child, list) else [child]):
            found = _headline(c)
            if found is not None:
                return found
    return None


def test_confetti_draw_is_a_pure_function_of_box_and_t():
    """The scene contract, and the reason goldens can be trusted. Drawing
    the same t twice must produce identical pixels, and drawing it must
    not mutate the node."""
    m = _module()
    node = m.Confetti((cv.YELLOW, cv.CYAN))
    a, b = cv.Canvas(), cv.Canvas()
    node.draw(a, (0, 0, cv.W, cv.H), 7)
    node.draw(b, (0, 0, cv.W, cv.H), 7)
    assert a.img.tobytes() == b.img.tobytes()


def test_confetti_actually_moves_between_frames():
    m = _module()
    node = m.Confetti((cv.YELLOW, cv.CYAN))
    a, b = cv.Canvas(), cv.Canvas()
    node.draw(a, (0, 0, cv.W, cv.H), 0)
    node.draw(b, (0, 0, cv.W, cv.H), 3)
    assert a.img.tobytes() != b.img.tobytes()


def test_confetti_never_paints_outside_the_box_it_is_given():
    """Silent clipping exists for Marquee, not as a licence for a node to
    scribble past the box it was handed. Drawn into a small box in the
    middle of the canvas, every lit pixel must fall inside it -- an
    assertion that merely checked 'something was drawn' would pass against
    a node painting over the whole display."""
    m = _module()
    node = m.Confetti((cv.WHITE,), count=60)
    bx, by, bw, bh = 10, 8, 20, 16
    c = cv.Canvas()
    node.draw(c, (bx, by, bw, bh), 5)
    px = c.img.convert("RGB").load()
    outside = [(x, y) for x in range(cv.W) for y in range(cv.H)
               if not (bx <= x < bx + bw and by <= y < by + bh)
               and px[x, y] != cv.BLACK]
    assert outside == [], f"painted outside the box at {outside[:5]}"
    inside = [(x, y) for x in range(bx, bx + bw) for y in range(by, by + bh)
              if px[x, y] != cv.BLACK]
    assert inside, "drew nothing inside the box"
