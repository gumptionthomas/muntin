import pytest
from PIL import Image, ImageDraw

from llmbyt import font


def test_available_lists_both_shipped_fonts():
    assert set(font.available()) >= {"tom-thumb", "spleen-5x8"}


def test_tom_thumb_cell_is_4x6_from_dwidth_not_boundingbox():
    # FONTBOUNDINGBOX says 3 wide; DWIDTH says 4. DWIDTH wins.
    f = font.load("tom-thumb")
    assert (f.char_w, f.char_h) == (4, 6)


def test_spleen_cell_is_5x8():
    f = font.load("spleen-5x8")
    assert (f.char_w, f.char_h) == (5, 8)


def test_text_width_is_advance_times_length():
    f = font.load("tom-thumb")
    assert f.text_width("abc") == 12
    assert f.text_width("") == 0


def test_load_is_cached():
    assert font.load("tom-thumb") is font.load("tom-thumb")


def test_unknown_font_names_the_available_ones():
    with pytest.raises(font.FontError) as e:
        font.load("comic-sans")
    assert "comic-sans" in str(e.value)
    assert "tom-thumb" in str(e.value)


def _ink(s, name="tom-thumb"):
    """Render s and return the set of lit pixel coordinates."""
    f = font.load(name)
    img = Image.new("RGB", (f.text_width(s) + 2, f.char_h + 2), (0, 0, 0))
    f.draw(ImageDraw.Draw(img), (0, 0), s, (255, 255, 255))
    return {xy for xy in
            ((x, y) for x in range(img.width) for y in range(img.height))
            if img.getpixel(xy) != (0, 0, 0)}


def test_space_draws_nothing():
    assert _ink(" ") == set()


def test_exclam_sits_on_the_baseline_leaving_the_descender_row_blank():
    # tom-thumb cell is 6 tall with 1 row of descent, so '!' occupies
    # rows 0-4 and never row 5.
    ink = _ink("!")
    assert ink
    assert max(y for _, y in ink) == 4


def test_lowercase_g_reaches_into_the_descender_row():
    assert max(y for _, y in _ink("g")) == 5


def test_draw_returns_the_width_it_advanced():
    f = font.load("tom-thumb")
    img = Image.new("RGB", (40, 10))
    assert f.draw(ImageDraw.Draw(img), (0, 0), "hey", (255, 255, 255)) == 12


def test_glyphs_never_exceed_the_cell():
    for name in ("tom-thumb", "spleen-5x8"):
        f = font.load(name)
        for ch, cell in f.glyphs.items():
            assert len(cell) == f.char_h, (name, ch)
            assert all(len(row) == f.char_w for row in cell), (name, ch)


def test_unknown_character_renders_blank_rather_than_crashing():
    assert _ink("☃") == set()   # snowman, not in either font


def test_parse_rejects_bdf_without_fontboundingbox(tmp_path):
    """BDF file missing FONTBOUNDINGBOX must state the fix."""
    bdf_file = tmp_path / "no_bbox.bdf"
    bdf_file.write_text("FONT TestFont\nENDCHAR\n", encoding="latin-1")

    with pytest.raises(font.FontError) as exc_info:
        font._parse("test", str(bdf_file))

    error_msg = str(exc_info.value)
    assert "FONTBOUNDINGBOX" in error_msg
    assert "fix" in error_msg.lower() or "add" in error_msg.lower()


def test_parse_rejects_bdf_without_ascii_glyphs(tmp_path):
    """BDF file with FONTBOUNDINGBOX but no ASCII glyphs must state the fix."""
    bdf_file = tmp_path / "no_ascii.bdf"
    bdf_file.write_text(
        "FONTBOUNDINGBOX 4 6 0 0\n"
        "ENCODING 200\n"  # Non-ASCII codepoint
        "DWIDTH 4 0\n"
        "BBX 4 6 0 0\n"
        "BITMAP\n"
        "00\nENDCHAR\n",
        encoding="latin-1"
    )

    with pytest.raises(font.FontError) as exc_info:
        font._parse("test", str(bdf_file))

    error_msg = str(exc_info.value)
    assert "ASCII" in error_msg or "32-126" in error_msg
    assert "fix" in error_msg.lower() or "add" in error_msg.lower()


def test_parse_rejects_ascii_glyphs_without_dwidth(tmp_path):
    """BDF file with ASCII glyphs but no DWIDTH must state the fix."""
    bdf_file = tmp_path / "no_dwidth.bdf"
    bdf_file.write_text(
        "FONTBOUNDINGBOX 4 6 0 0\n"
        "ENCODING 65\n"  # 'A'
        "BBX 4 6 0 0\n"
        "BITMAP\n"
        "00\nENDCHAR\n",
        encoding="latin-1"
    )

    with pytest.raises(font.FontError) as exc_info:
        font._parse("test", str(bdf_file))

    error_msg = str(exc_info.value)
    assert "DWIDTH" in error_msg
    assert "fix" in error_msg.lower() or "add" in error_msg.lower()
