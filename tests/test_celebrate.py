"""celebrate.py varies between runs, which the other example tests cannot
cover: test_example_draws_something_visible samples exactly one render,
and a varying example that can produce a blank frame would turn that into
an intermittent failure. These pin the invariants that make the variation
safe."""
import importlib.util
import itertools
import pathlib

import pytest

from muntin import canvas as cv
from muntin import scene as sc

CELEBRATE = pathlib.Path(__file__).parent.parent / "examples" / "celebrate.py"


def _module():
    spec = importlib.util.spec_from_file_location("celebrate", CELEBRATE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_every_run_draws_something_on_the_first_frame():
    """Sampling would leave roughly one of eighteen message/palette
    combinations untested per run; iterate every pair deterministically
    instead, via an injectable rng that picks a specific combination."""
    m = _module()

    class _FixedChoice:
        def __init__(self, message, palette):
            self._message = message
            self._palette = palette

        def choice(self, seq):
            return self._message if seq is m.MESSAGES else self._palette

    for message, palette in itertools.product(m.MESSAGES, m.PALETTES):
        node = m.render(rng=_FixedChoice(message, palette))
        frames, _ = sc.render_scene(node)
        assert frames[0].convert("RGB").getbbox() is not None, (
            f"blank frame 0 for message={message!r} palette={palette!r}")


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


def test_confetti_frame_count_is_the_display_height():
    """frames must equal cv.H for the loop-continuity math below to hold:
    with any speed in {1, 2} and frames == h, advancing t by 1 wraps ly
    exactly back to where t=0 started -- see the seam-jump test."""
    m = _module()
    node = m.Confetti((cv.WHITE,))
    assert node.frames == cv.H


def test_confetti_has_no_duplicate_adjacent_frames():
    """The old frames=45 example gave every particle the same speed (2),
    whose position pattern repeats with period 16 -- so 29 of the 45
    frames silently duplicated an earlier one. Adjacent frames of the
    tuned example must always differ."""
    m = _module()
    node = m.Confetti((cv.YELLOW, cv.CYAN, cv.MAGENTA))
    box = (0, 0, cv.W, cv.H)
    rendered = []
    for t in range(node.frames):
        c = cv.Canvas()
        node.draw(c, box, t)
        rendered.append(c.img.tobytes())
    for t in range(len(rendered) - 1):
        assert rendered[t] != rendered[t + 1], (
            f"frame {t} is pixel-identical to frame {t + 1}")


def test_confetti_loops_without_a_seam_jump():
    """Each particle's own speed (1 or 2 px/frame, alternating by index)
    must carry it exactly one more step from the last frame back to frame
    0 -- not the 8px jump the old frames=45/speed=2-for-everyone example
    produced, where the loop point landed mid-cycle."""
    m = _module()
    node = m.Confetti((cv.WHITE,), count=8)
    box = (0, 0, cv.W, cv.H)

    def lit_pixels(t):
        c = cv.Canvas()
        node.draw(c, box, t)
        px = c.img.convert("RGB").load()
        return {(x, y) for x in range(cv.W) for y in range(cv.H)
                if px[x, y] != cv.BLACK}

    first = lit_pixels(0)
    last = lit_pixels(node.frames - 1)
    for i in range(node.count):
        speed = 1 + (i % 2)
        lx = (i * i * 7 + i * 11 + 3) % cv.W
        ly_first = (i * 5 + 0 * speed) % cv.H
        ly_last = (i * 5 + (node.frames - 1) * speed) % cv.H
        assert (lx, ly_first) in first, f"particle {i} missing from frame 0"
        assert (lx, ly_last) in last, (
            f"particle {i} missing from frame {node.frames - 1}")
        assert (ly_last + speed) % cv.H == ly_first, (
            f"particle {i} (speed {speed}) does not land on its frame-0 "
            f"position after one more step -- the loop has a seam.")


def test_confetti_positions_are_not_a_lattice():
    """A linear-in-i formula (the old `i * 11 + 3`) makes every particle's
    x a fixed multiple of 11 apart -- diagonal stripes, not confetti. The
    scattered formula must not reduce to a simple arithmetic progression."""
    m = _module()
    node = m.Confetti((cv.WHITE,), count=10)
    xs = [(i * i * 7 + i * 11 + 3) % cv.W for i in range(node.count)]
    diffs = {b - a for a, b in zip(xs, xs[1:])}
    assert len(diffs) > 1, f"x positions still form a lattice: {xs}"


def test_palettes_exclude_white_so_flecks_dont_camouflage_the_headline():
    """The headline is WHITE. A palette that also contains WHITE lets
    flecks hide directly on top of the text they are meant to frame."""
    m = _module()
    for palette in m.PALETTES:
        assert cv.WHITE not in palette, f"{palette} still contains WHITE"


def test_confetti_requires_at_least_one_colour():
    """Confetti(()) used to raise ZeroDivisionError from
    `i % len(self.colors)` -- an implementation-detail crash instead of
    a MuntinError naming the constraint and the fix."""
    m = _module()
    with pytest.raises(sc.SceneError) as excinfo:
        m.Confetti(())
    message = str(excinfo.value).lower()
    assert "colour" in message or "color" in message
