import pytest
from PIL import Image

from muntin import canvas as cv


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
    from muntin import font
    c = cv.Canvas()
    assert c.text((0, 0), "hi", font="spleen-5x8") == 10
    assert c.text((0, 10), "hi", font=font.load("spleen-5x8")) == 10


def test_text_clips_at_the_edge_rather_than_raising():
    """Text drawn so it runs off the right edge clips silently instead of
    raising or wrapping; the visible sliver of the first glyph still renders."""
    c = cv.Canvas()
    # "overflowing" at (60, 0): only the first glyph's 4px cell (canvas
    # columns 60-63) is on-canvas; the rest of the string (columns 64+)
    # must be dropped silently, not raise and not wrap to column 0.
    c.text((60, 0), "overflowing")     # must not raise
    # 'o' row 1 lights source column rx=1 -> canvas x = 60 + 1 = 61.
    assert c.img.getpixel((61, 1)) == cv.WHITE
    # Nothing should have wrapped around to the far side of the canvas.
    assert c.img.getpixel((0, 0)) == cv.BLACK
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
    """Literal Marquee case: an oversized sprite at a negative offset must land
    its content at the position implied by that offset, not get clamped to
    (0, 0). A solid-color fixture can't tell those two apart (a 128x64 solid
    block still covers the canvas either way), so this uses a marker block at
    a known source coordinate and checks where it actually lands.
    """
    c = cv.Canvas()
    # 128x64 source, GREEN background with a 4x4 RED marker whose top-left
    # corner sits at source (40, 20).
    large_img = Image.new("RGB", (128, 64), cv.GREEN)
    for dx in range(4):
        for dy in range(4):
            large_img.putpixel((40 + dx, 20 + dy), cv.RED)
    # Draw it at negative offset: (-30, -10)
    # This means pixels from (30, 10) to (127, 63) of the image map to (0, 0) to (97, 53) on canvas
    # Due to canvas size, only (30, 10) to (63, 31) of the image will be visible
    c.sprite(large_img, (-30, -10))
    # Correct clipping: source (sx, sy) lands at canvas (sx - 30, sy - 10).
    # Marker top-left (40, 20) -> canvas (10, 10); check a pixel inside it:
    # source (41, 21) -> canvas (41 - 30, 21 - 10) = (11, 11).
    assert c.img.getpixel((11, 11)) == cv.RED
    # The visible portion should otherwise be covered with GREEN
    assert c.img.getpixel((0, 0)) == cv.GREEN  # (30, 10) of source
    assert c.img.getpixel((33, 21)) == cv.GREEN  # (63, 31) of source
    # Negative-space check: a clamp-to-origin bug (pasting at (0, 0) instead
    # of (-30, -10)) would leave the marker at its unshifted source
    # coordinates, i.e. canvas (40, 20)-(43, 23). Canvas (41, 21) sits inside
    # that wrong location -- under correct clipping it must stay background
    # GREEN, not the marker's RED.
    assert c.img.getpixel((41, 21)) == cv.GREEN
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
    """Rectangle with negative origin and dimensions exceeding canvas clips to filled interior.

    NOTE: the original fixture here was (-10, -5, 80, 50) -- 80x50 is so
    oversized that it covers the *entire* canvas whether the negative
    origin is honored or clamped to (0, 0) (clamped: (0, 0, 80, 50) still
    reaches (79, 49), past both edges). That made every possible pixel
    assertion identical under a clamp-to-origin bug, so the fixture is
    changed to 80x20: still wider than the canvas (exceeds on the right
    either way) but short enough that where it stops vertically depends on
    whether the -5 y-offset is honored.
    """
    c = cv.Canvas()
    # Draw a filled rect starting at (-10, -5) with size 80x20.
    # x: covers -10..69 (80 wide) -> clipped to the full canvas width [0, 63]
    #    regardless of whether the negative x offset is honored or clamped,
    #    since w=80 alone exceeds the 64px canvas.
    # y: covers -5..14 (20 tall) -> clipped to [0, 14]
    #    (last visible row = -5 + 20 - 1 = 14; rows below 14 must stay BLACK).
    c.rect((-10, -5, 80, 20), cv.CYAN, fill=True)
    # Full width is covered (w=80 overruns the canvas on the right regardless
    # of whether the negative x offset is honored).
    assert c.img.getpixel((0, 0)) == cv.CYAN
    assert c.img.getpixel((63, 0)) == cv.CYAN
    assert c.img.getpixel((32, 7)) == cv.CYAN
    # Last row the rect actually reaches under correct clipping: -5+20-1=14.
    assert c.img.getpixel((0, 14)) == cv.CYAN
    # Negative-space check: under correct clipping the rect stops at row 14,
    # so row 17 must stay BLACK. A clamp-to-origin bug (y clamped to 0
    # instead of -5, height kept at 20) would instead fill through row 19
    # (0 + 20 - 1 = 19), wrongly lighting this pixel CYAN.
    assert c.img.getpixel((32, 17)) == cv.BLACK
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
    """Line with one or both endpoints outside canvas clips to the
    geometrically-correct visible path, not just "orange exists somewhere"."""
    c = cv.Canvas()
    # Draw a line from (-10, 10) to (70, 20)
    # This is a nearly-horizontal line that extends beyond canvas on both sides
    # slope = dy/dx = (20-10) / (70-(-10)) = 10/80 = 0.125
    # y(x) = 10 + 0.125 * (x - (-10))
    # y(0)  = 10 + 0.125*10 = 11.25 -> ~11
    # y(63) = 10 + 0.125*73 = 19.125 -> ~19
    c.line((-10, 10), (70, 20), cv.ORANGE)
    tolerance = 2  # rasterization slack
    assert any(c.img.getpixel((0, y)) == cv.ORANGE
               for y in range(11 - tolerance, 11 + tolerance + 1)), \
        "line should cross the left edge near (0, 11)"
    assert any(c.img.getpixel((63, y)) == cv.ORANGE
               for y in range(19 - tolerance, 19 + tolerance + 1)), \
        "line should cross the right edge near (63, 19)"
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)


def test_text_at_negative_xy_clips():
    """Text at negative coordinates clips to canvas without shifting the
    remaining glyphs into the wrong columns.

    With the default 4x6 font (tom-thumb, char_w=4), "test" at (-5, 0):
    - char 0 ('t') occupies canvas columns -5..-2 -> fully off-canvas.
    - char 1 ('e') occupies canvas columns -1..2 -> only its rightmost
      cell column (source rx=3, structurally blank -- 'e' is only 3px
      wide) reaches canvas x=2; ink columns (rx=1,2) land at canvas x=0,1.
    - char 2 ('s') occupies canvas columns 3..6 (fully on-canvas).
    - char 3 ('t') occupies canvas columns 7..10 (fully on-canvas).
    """
    c = cv.Canvas()
    # Draw text at (-5, 0) - the leftmost part is off-canvas
    width = c.text((-5, 0), "test", color=cv.WHITE)
    # Should return a width (text drawing succeeded)
    assert width > 0
    # A pixel from the visible sliver of 'e': row 1 has ink at source rx=1,
    # landing at canvas x = -1 + 1 = 0.
    assert c.img.getpixel((0, 1)) == cv.WHITE
    # Negative-space check: canvas x=2 maps to source rx=3 of 'e', which that
    # glyph never lights (its ink is only 3px wide) -- BLACK under correct
    # clipping for every row it draws. A clamp-to-origin bug (drawing "test"
    # as if it started at x=0) would instead put the *first* char ('t') at
    # that column, whose row-1 ink (rx=0,1,2) reaches canvas x=2 and would
    # wrongly light it WHITE.
    assert c.img.getpixel((2, 1)) == cv.BLACK
    # Dimensions unchanged
    assert (c.width, c.height) == (64, 32)
