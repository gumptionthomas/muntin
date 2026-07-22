import pytest
from PIL import Image

from llmbyt import canvas as cv
from llmbyt import scene as sc


def lit(canvas):
    return {(x, y) for x in range(canvas.width) for y in range(canvas.height)
            if canvas.img.getpixel((x, y)) != cv.BLACK}


# --- Marquee ---------------------------------------------------------

def test_marquee_measure_clamps_to_the_display_so_it_never_overflows():
    tall = sc.Column([sc.Text("line") for _ in range(20)])
    assert tall.measure()[1] > cv.H
    assert sc.Marquee(tall).measure() == (16, cv.H)


def test_marquee_frame_count_is_hold_plus_travel():
    child = sc.Column([sc.Text("x") for _ in range(10)])   # 60px tall
    m = sc.Marquee(child, axis="y", hold=5, speed=1)
    assert m.frame_count() == 5 + (60 - cv.H)


def test_marquee_that_fits_does_not_scroll():
    assert sc.Marquee(sc.Text("hi"), hold=5).frame_count() == 5


def test_marquee_holds_still_through_the_hold_frames():
    child = sc.Column([sc.Text("x") for _ in range(10)])
    m = sc.Marquee(child, axis="y", hold=3)
    a, b = cv.Canvas(), cv.Canvas()
    m.draw(a, (0, 0, cv.W, cv.H), 0)
    m.draw(b, (0, 0, cv.W, cv.H), 2)
    assert a.img.tobytes() == b.img.tobytes()


def test_marquee_has_moved_by_the_frame_after_the_hold():
    child = sc.Column([sc.Text("x") for _ in range(10)])
    m = sc.Marquee(child, axis="y", hold=3)
    a, b = cv.Canvas(), cv.Canvas()
    m.draw(a, (0, 0, cv.W, cv.H), 2)
    m.draw(b, (0, 0, cv.W, cv.H), 4)
    assert a.img.tobytes() != b.img.tobytes()


def test_marquee_scrolls_horizontally_on_the_x_axis():
    m = sc.Marquee(sc.Text("a" * 40), axis="x", hold=1)
    assert m.frame_count() > 1
    assert m.measure()[0] == cv.W


def test_marquee_rejects_an_unknown_axis():
    with pytest.raises(sc.SceneError, match="axis"):
        sc.Marquee(sc.Text("x"), axis="z")


def test_marquee_last_frame_reaches_full_travel_on_the_y_axis():
    marker = cv.MAGENTA
    img = Image.new("RGB", (10, 40), cv.BLACK)   # travel = 40 - 32 = 8
    for x in range(10):
        img.putpixel((x, 39), marker)            # mark the child's last row
    m = sc.Marquee(sc.Sprite(img), axis="y", hold=2, speed=1)
    c = cv.Canvas()
    m.draw(c, (0, 0, cv.W, cv.H), m.frame_count() - 1)
    # the child's last row must land exactly on the viewport's bottom edge
    assert any(c.img.getpixel((x, cv.H - 1)) == marker for x in range(10))


def test_marquee_last_frame_reaches_full_travel_on_the_x_axis():
    marker = cv.MAGENTA
    img = Image.new("RGB", (72, 10), cv.BLACK)   # travel = 72 - 64 = 8
    for y in range(10):
        img.putpixel((71, y), marker)            # mark the child's last column
    m = sc.Marquee(sc.Sprite(img), axis="x", hold=2, speed=1)
    c = cv.Canvas()
    m.draw(c, (0, 0, cv.W, cv.H), m.frame_count() - 1)
    # the child's last column must land exactly on the viewport's right edge
    assert any(c.img.getpixel((cv.W - 1, y)) == marker for y in range(10))


def test_marquee_static_frame_count_matches_hold_exactly():
    child = sc.Column([sc.Text("x") for _ in range(10)])
    hold = 4
    m = sc.Marquee(child, axis="y", hold=hold)
    base, before, at = cv.Canvas(), cv.Canvas(), cv.Canvas()
    m.draw(base, (0, 0, cv.W, cv.H), 0)
    m.draw(before, (0, 0, cv.W, cv.H), hold - 1)
    m.draw(at, (0, 0, cv.W, cv.H), hold)
    # frames [0, hold) are all static -- t=hold-1 must match t=0 exactly
    assert before.img.tobytes() == base.img.tobytes()
    # motion begins at t=hold -- it must differ from the static frame
    assert at.img.tobytes() != base.img.tobytes()


def test_marquee_speed_over_one_still_lands_exactly_on_full_travel():
    marker = cv.MAGENTA
    img = Image.new("RGB", (10, 45), cv.BLACK)   # travel = 45 - 32 = 13
    for x in range(10):
        img.putpixel((x, 44), marker)            # mark the child's last row
    m = sc.Marquee(sc.Sprite(img), axis="y", hold=1, speed=4)
    travel = 45 - cv.H
    assert travel % m.speed != 0, "test needs a non-exact-multiple travel"
    c = cv.Canvas()
    m.draw(c, (0, 0, cv.W, cv.H), m.frame_count() - 1)
    assert any(c.img.getpixel((x, cv.H - 1)) == marker for x in range(10))


def test_marquee_rejects_a_negative_hold():
    with pytest.raises(sc.SceneError, match="hold"):
        sc.Marquee(sc.Text("x"), hold=-1)


# --- Sprite ----------------------------------------------------------

def test_sprite_measures_as_the_source_image():
    assert sc.Sprite(Image.new("RGB", (10, 6))).measure() == (10, 6)


def test_sprite_paints_its_pixels():
    c = cv.Canvas()
    sc.Sprite(Image.new("RGB", (4, 4), cv.RED)).draw(c, (2, 2, 4, 4), 0)
    assert c.img.getpixel((3, 3)) == cv.RED


def test_sprite_contain_scales_a_large_image_down_within_the_display():
    s = sc.Sprite(Image.new("RGB", (256, 256), cv.RED), fit="contain")
    w, h = s.measure()
    assert (w, h) == (32, 32)          # limited by the 32px height


def test_sprite_cover_fills_the_display_and_crops():
    s = sc.Sprite(Image.new("RGB", (256, 256), cv.RED), fit="cover")
    assert s.measure() == (cv.W, cv.H)


def test_sprite_does_not_upscale_a_small_image_under_contain():
    s = sc.Sprite(Image.new("RGB", (8, 8), cv.RED), fit="contain")
    assert s.measure() == (8, 8)


def test_sprite_loads_from_a_path(tmp_path):
    p = tmp_path / "x.png"
    Image.new("RGB", (5, 5), cv.CYAN).save(p)
    assert sc.Sprite(str(p)).measure() == (5, 5)


def test_missing_sprite_path_names_the_file():
    with pytest.raises(sc.SceneError, match="nope.png"):
        sc.Sprite("nope.png")


def test_sprite_on_a_non_image_file_names_the_path_and_the_fix(tmp_path):
    p = tmp_path / "notimage.png"
    p.write_text("not an image")
    with pytest.raises(sc.SceneError) as exc_info:
        sc.Sprite(str(p))
    msg = str(exc_info.value)
    assert str(p) in msg
    assert "not a" in msg or "not readable" in msg
    # actionable fix: what the caller should do about it
    assert "PIL.Image" in msg or "pass a" in msg


def test_sprite_on_a_directory_raises_a_scene_error_not_a_traceback(tmp_path):
    d = tmp_path / "somedir"
    d.mkdir()
    with pytest.raises(sc.SceneError) as exc_info:
        sc.Sprite(str(d))
    assert str(d) in str(exc_info.value)


def test_sprite_rejects_an_unknown_fit():
    with pytest.raises(sc.SceneError, match="stretch"):
        sc.Sprite(Image.new("RGB", (4, 4)), fit="stretch")


def test_sprite_on_a_decompression_bomb_raises_a_scene_error_not_a_traceback(tmp_path):
    """PIL.Image.DecompressionBombError is not an OSError. It should still be
    caught and wrapped in SceneError, not escape as a raw traceback."""
    # Create a valid PNG and temporarily lower Image.MAX_IMAGE_PIXELS to trigger
    # the decompression bomb check.
    p = tmp_path / "bomb.png"
    Image.new("RGB", (100, 100), color=cv.RED).save(str(p))

    original_max = Image.MAX_IMAGE_PIXELS
    try:
        # Set limit to 100 pixels; 100x100 image = 10,000 pixels > limit
        Image.MAX_IMAGE_PIXELS = 100
        with pytest.raises(sc.SceneError) as exc_info:
            sc.Sprite(str(p))
        msg = str(exc_info.value)
        # The error message should name the problematic path
        assert str(p) in msg
        # Should provide an actionable fix (pointing to PIL.Image or recommending
        # a different file/passing an Image object)
        assert "PIL.Image" in msg or "pass a" in msg or "image" in msg.lower()
    finally:
        Image.MAX_IMAGE_PIXELS = original_max


# --- Plot ------------------------------------------------------------

def test_plot_measures_one_column_per_value():
    assert sc.Plot([1, 2, 3]).measure() == (3, 8)


def test_plot_puts_the_maximum_at_the_top_and_the_minimum_at_the_bottom():
    c = cv.Canvas()
    sc.Plot([0, 10]).draw(c, (0, 0, 2, 8), 0)
    by_x = {}
    for x, y in lit(c):
        by_x.setdefault(x, []).append(y)
    # smaller y is higher on screen; the larger value must sit above
    assert min(by_x[1]) < min(by_x[0])


def test_plot_of_a_flat_series_draws_a_flat_line():
    c = cv.Canvas()
    sc.Plot([5, 5, 5, 5]).draw(c, (0, 0, 4, 8), 0)
    assert len({y for _, y in lit(c)}) == 1


def test_plot_of_a_single_value_draws_one_point():
    c = cv.Canvas()
    sc.Plot([3]).draw(c, (0, 0, 1, 8), 0)
    assert len(lit(c)) == 1


def test_empty_plot_is_a_loud_error():
    with pytest.raises(sc.SceneError, match="no values"):
        sc.Plot([])


def test_plot_is_a_single_frame():
    assert sc.Plot([1, 2]).frame_count() == 1
