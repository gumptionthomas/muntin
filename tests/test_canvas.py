import pytest
from PIL import Image

from llmbyt import canvas as cv


def test_default_canvas_is_the_display_size_and_black():
    c = cv.Canvas()
    assert (c.width, c.height) == (64, 32)
    assert c.img.getpixel((0, 0)) == cv.BLACK


def test_pixel_sets_one_point():
    c = cv.Canvas()
    c.pixel((3, 4), cv.RED)
    assert c.img.getpixel((3, 4)) == cv.RED
    assert c.img.getpixel((4, 4)) == cv.BLACK


def test_pixel_outside_the_canvas_is_ignored_not_an_error():
    c = cv.Canvas()
    c.pixel((-1, 0), cv.RED)
    c.pixel((999, 999), cv.RED)
    assert c.img.getpixel((0, 0)) == cv.BLACK


def test_fill_covers_everything():
    c = cv.Canvas()
    c.fill(cv.GREEN)
    assert c.img.getpixel((0, 0)) == c.img.getpixel((63, 31)) == cv.GREEN


def test_rect_outline_draws_edges_but_not_the_middle():
    c = cv.Canvas()
    c.rect((0, 0, 5, 5), cv.WHITE)
    assert c.img.getpixel((0, 0)) == cv.WHITE
    assert c.img.getpixel((4, 4)) == cv.WHITE
    assert c.img.getpixel((2, 2)) == cv.BLACK


def test_rect_filled_covers_the_middle():
    c = cv.Canvas()
    c.rect((0, 0, 5, 5), cv.WHITE, fill=True)
    assert c.img.getpixel((2, 2)) == cv.WHITE


def test_line_connects_two_points():
    c = cv.Canvas()
    c.line((0, 0), (0, 5), cv.CYAN)
    assert c.img.getpixel((0, 3)) == cv.CYAN


def test_text_returns_width_and_paints_ink():
    c = cv.Canvas()
    assert c.text((0, 0), "hi") == 8
    assert any(c.img.getpixel((x, y)) == cv.WHITE
               for x in range(8) for y in range(6))


def test_text_accepts_a_font_by_name_or_object():
    from llmbyt import font
    c = cv.Canvas()
    assert c.text((0, 0), "hi", font="spleen-5x8") == 10
    assert c.text((0, 10), "hi", font=font.load("spleen-5x8")) == 10


def test_text_clips_at_the_edge_rather_than_raising():
    c = cv.Canvas()
    c.text((60, 0), "overflowing")     # must not raise
    assert c.width == 64


def test_sprite_pastes_an_image():
    c = cv.Canvas()
    c.sprite(Image.new("RGB", (4, 4), cv.MAGENTA), (2, 2))
    assert c.img.getpixel((3, 3)) == cv.MAGENTA
    assert c.img.getpixel((7, 7)) == cv.BLACK


def test_snapshot_is_an_independent_copy():
    c = cv.Canvas()
    snap = c.snapshot()
    c.fill(cv.RED)
    assert snap.getpixel((0, 0)) == cv.BLACK


def test_palette_maps_names_to_the_constants():
    assert cv.PALETTE["red"] == cv.RED
    assert all(len(v) == 3 for v in cv.PALETTE.values())


def test_blue_is_lifted_off_pure_blue_to_survive_the_panel():
    assert cv.BLUE != (0, 0, 255)
    assert cv.BLUE[2] > 200
