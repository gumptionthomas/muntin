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


def test_sprite_rejects_an_unknown_fit():
    with pytest.raises(sc.SceneError, match="stretch"):
        sc.Sprite(Image.new("RGB", (4, 4)), fit="stretch")


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
