"""Pixel-exact fixtures over the arithmetic nothing else pins down.

The spec calls goldens the backbone, and the pure draw(canvas, box, t)
contract exists specifically to make them reliable. Three layers of
integer arithmetic decide where a pixel lands and none of them had
pixel-level regression cover:

  * font.py     BDF bit-unpacking, byte-stride padding, baseline placement
  * scene.py    the layout offsets Row/Column/gap/align/justify compute
  * preview.py  the bezel and grid geometry an agent reads the result from

Every assertion here is "these exact pixels". Re-bless an intentional
change with GOLDEN_UPDATE=1 -- and look at the new fixture, because a
golden blesses whatever it is handed.
"""
from PIL import Image

from golden import assert_golden

from muntin import canvas as cv
from muntin import font as _font
from muntin import preview
from muntin import scene as sc

ASCII = "".join(chr(c) for c in range(32, 127))     # every glyph both fonts have
PER_ROW = 16


def _ascii_sheet(font_name):
    """The whole printable range laid out on a grid, one glyph per cell."""
    f = _font.load(font_name)
    rows = -(-len(ASCII) // PER_ROW)
    c = cv.Canvas(PER_ROW * f.char_w, rows * f.char_h)
    for i in range(rows):
        c.text((0, i * f.char_h), ASCII[i * PER_ROW:(i + 1) * PER_ROW],
               font=f, color=cv.WHITE)
    return c.snapshot()


def test_golden_tom_thumb_ascii():
    """95 glyphs on one sheet. Any drift in cell width, baseline offset,
    or the byte-stride shift in font._cell moves ink here."""
    assert_golden(_ascii_sheet("tom-thumb"), "font_tom_thumb_ascii")


def test_golden_spleen_ascii():
    """The second shipped face, whose 5x8 cell exercises a different
    byte-stride and descent than tom-thumb's 4x6."""
    assert_golden(_ascii_sheet("spleen-5x8"), "font_spleen_ascii")


def test_golden_text_scene():
    """A real render_scene() pass: glyph placement plus the centring
    arithmetic that positions the block on the display."""
    frames, _ = sc.render_scene(sc.Column([
        sc.Text("DEPLOY", font="spleen-5x8"),
        sc.Text("green", color=cv.GREEN),
        sc.Text("14:32 +4", color=cv.DIM),
    ], gap=2, align="center", justify="center"))
    assert len(frames) == 1
    assert_golden(frames[0], "scene_text")


def test_golden_row_column_layout():
    """All three align modes side by side, two gap sizes, and a Plot.

    The root Row is the only node with slack to distribute, so its
    justify/align are what _offset() actually decides; the inner Columns
    differ only in `align`, which puts their short second line in three
    visibly different places. A change to _offset() or to the gap
    arithmetic moves pixels here instead of hiding behind an unchanged
    measure() tuple.
    """
    frames, _ = sc.render_scene(sc.Row([
        sc.Column([sc.Text("ab"), sc.Text("c", color=cv.RED)],
                  gap=1, align="start"),
        sc.Column([sc.Text("de"), sc.Text("f", color=cv.CYAN)],
                  gap=3, align="center"),
        sc.Column([sc.Text("gh"), sc.Text("i", color=cv.YELLOW)],
                  gap=1, align="end"),
        sc.Column([sc.Text("jk"),
                   sc.Plot([1, 4, 2, 8, 5], color=cv.GREEN)],
                  gap=1, align="center"),
    ], gap=4, justify="center", align="center"))
    assert len(frames) == 1
    assert_golden(frames[0], "scene_row_column")


def test_golden_preview_grid_and_bezel(tmp_path):
    """The preview is the only thing an agent can actually look at, so
    its geometry -- 1px bezel, NEAREST upscale, a grid line every cell --
    is load-bearing. scale=4 keeps the fixture small while still drawing
    the grid (which switches on at scale >= 4)."""
    c = cv.Canvas()
    c.rect((0, 0, cv.W, cv.H), cv.DIM)              # edges, against the bezel
    c.pixel((0, 0), cv.RED)                         # the very first cell
    c.pixel((cv.W - 1, cv.H - 1), cv.GREEN)         # and the very last
    c.text((2, 2), "grid", color=cv.WHITE)
    path = preview.write([c.snapshot()], tmp_path / "o", scale=4, grid=True)
    assert_golden(Image.open(path), "preview_grid")
