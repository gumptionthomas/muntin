import pytest

from llmbyt import canvas as cv
from llmbyt import scene as sc


def lit(canvas):
    return {(x, y) for x in range(canvas.width) for y in range(canvas.height)
            if canvas.img.getpixel((x, y)) != cv.BLACK}


def test_text_measures_as_advance_width_by_cell_height():
    assert sc.Text("abc").measure() == (12, 6)


def test_text_measures_with_the_font_it_was_given():
    assert sc.Text("abc", font="spleen-5x8").measure() == (15, 8)


def test_empty_text_has_zero_width_but_full_line_height():
    assert sc.Text("").measure() == (0, 6)


def test_text_is_a_single_frame():
    assert sc.Text("hi").frame_count() == 1


def test_text_draws_at_the_box_origin():
    # Asserted as a translation rather than an absolute x, because glyphs
    # carry their own left bearing ('!' has xoff=1 inside its 4px cell).
    a, b = cv.Canvas(), cv.Canvas()
    sc.Text("!").draw(a, (0, 0, 64, 32), 0)
    sc.Text("!").draw(b, (10, 4, 54, 28), 0)
    assert {(x + 10, y + 4) for x, y in lit(a)} == lit(b)


def test_column_stacks_heights_and_takes_the_widest_child():
    col = sc.Column([sc.Text("ab"), sc.Text("abcd")])
    assert col.measure() == (16, 12)


def test_column_gap_adds_between_children_not_around_them():
    col = sc.Column([sc.Text("a"), sc.Text("b"), sc.Text("c")], gap=2)
    assert col.measure() == (4, 6 * 3 + 2 * 2)


def test_row_sums_widths_and_takes_the_tallest_child():
    row = sc.Row([sc.Text("ab"), sc.Text("c", font="spleen-5x8")])
    assert row.measure() == (8 + 5, 8)


def test_empty_container_measures_zero():
    assert sc.Column([]).measure() == (0, 0)
    assert sc.Row([]).measure() == (0, 0)


def test_column_center_align_centres_children_on_the_cross_axis():
    c = cv.Canvas()
    sc.Column([sc.Text("!")], align="center").draw(c, (0, 0, 64, 32), 0)
    xs = {x for x, _ in lit(c)}
    # a 4px-wide glyph centred in 64px starts at x=30
    assert min(xs) >= 30


def test_column_end_justify_pushes_content_to_the_bottom():
    c = cv.Canvas()
    sc.Column([sc.Text("!")], justify="end").draw(c, (0, 0, 64, 32), 0)
    assert max(y for _, y in lit(c)) == 31 - 1   # '!' leaves the descender row


def test_row_center_justify_centres_on_the_main_axis():
    start, center = cv.Canvas(), cv.Canvas()
    sc.Row([sc.Text("!!")], justify="start").draw(start, (0, 0, 64, 32), 0)
    sc.Row([sc.Text("!!")], justify="center").draw(center, (0, 0, 64, 32), 0)
    # 8px of content in a 64px box shifts right by (64 - 8) // 2
    assert (min(x for x, _ in lit(center))
            - min(x for x, _ in lit(start))) == 28


def test_stack_measures_as_the_largest_child():
    st = sc.Stack([sc.Text("ab"), sc.Text("abcdef")])
    assert st.measure() == (24, 6)


def test_stack_paints_children_in_order_so_the_last_wins():
    c = cv.Canvas()
    sc.Stack([sc.Text("!", color=cv.RED),
              sc.Text("!", color=cv.GREEN)]).draw(c, (0, 0, 64, 32), 0)
    assert cv.GREEN in {c.img.getpixel(p) for p in lit(c)}
    assert cv.RED not in {c.img.getpixel(p) for p in lit(c)}


def test_container_frame_count_is_the_max_over_children():
    class Ticker(sc.Node):
        def measure(self):
            return (1, 1)

        def draw(self, canvas, box, t):
            pass

        def frame_count(self):
            return 7

    assert sc.Column([sc.Text("a"), Ticker()]).frame_count() == 7


def test_bad_align_names_the_valid_values():
    with pytest.raises(sc.SceneError) as e:
        sc.Column([], align="middle")
    assert "middle" in str(e.value) and "center" in str(e.value)


def test_drawing_is_deterministic_for_the_same_box_and_t():
    a, b = cv.Canvas(), cv.Canvas()
    node = sc.Column([sc.Text("same"), sc.Text("twice")], gap=1)
    node.draw(a, (0, 0, 64, 32), 0)
    node.draw(b, (0, 0, 64, 32), 0)
    assert a.img.tobytes() == b.img.tobytes()


def test_stack_hands_children_its_own_box_so_they_can_still_align():
    # An alignment-aware child nested in a Stack must land at the same
    # pixels as the same child drawn directly with the same box. Before
    # the fix, Stack.draw handed each child a box sized to the child's
    # own measure() (available == used), collapsing every align/justify
    # mode to "start" -- silently, with no error.
    direct = cv.Canvas()
    sc.Row([sc.Text("!")], justify="center").draw(direct, (0, 0, 64, 32), 0)
    direct_min_x = min(x for x, _ in lit(direct))

    nested = cv.Canvas()
    sc.Stack([sc.Row([sc.Text("!")], justify="center")]).draw(
        nested, (0, 0, 64, 32), 0)
    nested_min_x = min(x for x, _ in lit(nested))

    assert direct_min_x == 31
    assert nested_min_x == direct_min_x


def test_negative_gap_names_the_constraint_and_the_fix():
    with pytest.raises(sc.SceneError) as e:
        sc.Row([sc.Text("a"), sc.Text("b")], gap=-100)
    msg = str(e.value)
    assert "gap" in msg and "-100" in msg
