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


# Tests below guard the Marquee scrolling contract: drawing outside the
# surface must clip rather than raise or corrupt state. Marquee will draw
# oversized content at negative coordinates to scroll it through the viewport.


def test_sprite_at_negative_xy_with_oversized_image_clips_to_canvas():
    """Literal Marquee case: oversized sprite at negative offset, visible portion covered."""
    c = cv.Canvas()
    # Create an image larger than the canvas (128x64)
    large_img = Image.new("RGB", (128, 64), cv.GREEN)
    # Draw it at negative offset: (-30, -10)
    # This means pixels from (30, 10) to (127, 63) of the image map to (0, 0) to (97, 53) on canvas
    # Due to canvas size, only (30, 10) to (63, 31) of the image will be visible
    c.sprite(large_img, (-30, -10))
    # The visible portion should be covered with GREEN
    assert c.img.getpixel((0, 0)) == cv.GREEN  # (30, 10) of source
    assert c.img.getpixel((33, 21)) == cv.GREEN  # (63, 31) of source
    # Canvas dimensions must be unchanged
    assert (c.width, c.height) == (64, 32)


def test_sprite_positioned_entirely_off_canvas_is_ignored():
    """Sprite completely outside the canvas should not paint anything."""
    c = cv.Canvas()
    small_img = Image.new("RGB", (8, 8), cv.MAGENTA)
    # Draw completely off the right edge
    c.sprite(small_img, (100, 100))
    # Canvas should remain entirely black
    assert c.img.getpixel((0, 0)) == cv.BLACK
    assert c.img.getpixel((63, 31)) == cv.BLACK
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)


def test_rect_with_negative_origin_and_large_dimensions_clips():
    """Rectangle with negative origin and dimensions exceeding canvas clips to filled interior."""
    c = cv.Canvas()
    # Draw a filled rect starting at (-10, -5) with size 80x50
    # Should fill from (-10, -5) to (69, 44), clipped to canvas (0, 0) to (63, 31)
    c.rect((-10, -5, 80, 50), cv.CYAN, fill=True)
    # Top-left corner of canvas should be filled
    assert c.img.getpixel((0, 0)) == cv.CYAN
    # Middle of canvas should be filled
    assert c.img.getpixel((32, 16)) == cv.CYAN
    # Right edge should be filled
    assert c.img.getpixel((63, 0)) == cv.CYAN
    # Bottom edge should be filled
    assert c.img.getpixel((0, 31)) == cv.CYAN
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)


def test_rect_extending_past_right_and_bottom_edges_clips():
    """Rectangle extending past right and bottom edges clips properly."""
    c = cv.Canvas()
    # Draw a rect at (40, 15, 40, 30) - extends to (79, 44), beyond canvas
    c.rect((40, 15, 40, 30), cv.YELLOW, fill=True)
    # Pixels inside the rect's bounds on the canvas should be filled
    assert c.img.getpixel((50, 20)) == cv.YELLOW
    # Pixels outside the rect's x bounds should be black
    assert c.img.getpixel((30, 20)) == cv.BLACK
    # Pixel at canvas edge should be covered if within rect bounds
    assert c.img.getpixel((63, 15)) == cv.YELLOW
    assert c.img.getpixel((40, 31)) == cv.YELLOW
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)


def test_line_with_endpoints_outside_canvas_clips():
    """Line with one or both endpoints outside canvas clips to visible region."""
    c = cv.Canvas()
    # Draw a line from (-10, 10) to (70, 20)
    # This is a nearly-horizontal line that extends beyond canvas on both sides
    c.line((-10, 10), (70, 20), cv.ORANGE)
    # The portion inside the canvas should have pixels from the line
    # Due to clipping and anti-aliasing, find the y range where the line appears
    line_found = False
    for y in range(32):
        if any(c.img.getpixel((x, y)) == cv.ORANGE for x in range(64)):
            line_found = True
            break
    assert line_found, "Line should be visible somewhere on canvas"
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)


def test_text_at_negative_xy_clips():
    """Text at negative coordinates clips to canvas, does not raise."""
    c = cv.Canvas()
    # Draw text at (-5, 0) - the leftmost part is off-canvas
    width = c.text((-5, 0), "test", color=cv.WHITE)
    # Should return a width (text drawing succeeded)
    assert width > 0
    # Should not raise an error (this is the main contract)
    # The visible portion of the text should have white pixels
    assert any(c.img.getpixel((x, y)) == cv.WHITE
               for x in range(64) for y in range(6))
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)
