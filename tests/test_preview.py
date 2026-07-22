import pytest
from PIL import Image

from llmbyt import canvas as cv
from llmbyt import preview


def frames(n):
    out = []
    for i in range(n):
        c = cv.Canvas()
        c.rect((i, i, 4, 4), cv.RED, fill=True)
        out.append(c.snapshot())
    return out


def test_single_frame_writes_a_png(tmp_path):
    p = preview.write(frames(1), tmp_path / "out")
    assert p.suffix == ".png" and p.exists()


def test_many_frames_write_a_gif(tmp_path):
    p = preview.write(frames(3), tmp_path / "out")
    assert p.suffix == ".gif"
    assert Image.open(p).n_frames == 3


def test_an_explicit_extension_is_respected(tmp_path):
    assert preview.write(frames(1), tmp_path / "shot.png").name == "shot.png"


def test_output_is_upscaled_by_the_scale_factor(tmp_path):
    img = Image.open(preview.write(frames(1), tmp_path / "o", scale=8))
    # 64x32 at 8x, plus a 1px bezel on each side
    assert img.size == (64 * 8 + 2, 32 * 8 + 2)


def test_scale_one_disables_the_grid_and_keeps_true_pixels(tmp_path):
    img = Image.open(preview.write(frames(1), tmp_path / "o",
                                   scale=1, grid=False))
    assert img.size == (66, 34)


def test_upscale_is_nearest_neighbour_not_blurred(tmp_path):
    c = cv.Canvas()
    c.pixel((0, 0), cv.WHITE)
    img = Image.open(preview.write([c.snapshot()], tmp_path / "o",
                                   scale=8, grid=False)).convert("RGB")
    # inside the bezel, the whole 8x8 block is pure white -- no interpolation
    assert img.getpixel((1, 1)) == (255, 255, 255)
    assert img.getpixel((8, 8)) == (255, 255, 255)
    assert img.getpixel((9, 9)) == (0, 0, 0)


def test_grid_draws_lines_between_cells(tmp_path):
    c = cv.Canvas()
    c.fill(cv.WHITE)
    img = Image.open(preview.write([c.snapshot()], tmp_path / "o",
                                   scale=8, grid=True)).convert("RGB")
    assert img.getpixel((1, 1)) == (255, 255, 255)      # cell interior
    assert img.getpixel((8, 1)) != (255, 255, 255)      # grid line


def test_empty_frames_is_a_loud_error(tmp_path):
    with pytest.raises(preview.PreviewError, match="no frames"):
        preview.write([], tmp_path / "o")


def test_parent_directories_are_created(tmp_path):
    p = preview.write(frames(1), tmp_path / "deep" / "nested" / "o")
    assert p.exists()


def test_wrong_size_frame_names_the_offender_expected_size_and_the_fix(tmp_path):
    bad = [cv.Canvas().snapshot(), Image.new("RGB", (10, 10))]
    with pytest.raises(preview.PreviewError) as e:
        preview.write(bad, tmp_path / "o")
    msg = str(e.value)
    assert "frame 1" in msg and "10x10" in msg and "64x32" in msg
    # constraint + violation alone isn't enough; must also say the fix
    assert "resize" in msg.lower() or "crop" in msg.lower()


def test_nonpositive_frame_ms_is_a_loud_error(tmp_path):
    with pytest.raises(preview.PreviewError) as e:
        preview.write(frames(1), tmp_path / "o", frame_ms=-50)
    msg = str(e.value)
    assert "frame_ms" in msg and "-50" in msg
    assert "positive" in msg.lower()


def test_zero_frame_ms_is_a_loud_error(tmp_path):
    with pytest.raises(preview.PreviewError) as e:
        preview.write(frames(1), tmp_path / "o", frame_ms=0)
    msg = str(e.value)
    assert "frame_ms" in msg and "0" in msg
    assert "positive" in msg.lower()


def test_non_integer_scale_is_a_loud_error(tmp_path):
    with pytest.raises(preview.PreviewError) as e:
        preview.write(frames(1), tmp_path / "o", scale=2.5)
    msg = str(e.value)
    assert "scale" in msg and "2.5" in msg
    assert "integer" in msg.lower()


def test_scale_less_than_one_names_the_fix(tmp_path):
    with pytest.raises(preview.PreviewError) as e:
        preview.write(frames(1), tmp_path / "o", scale=0)
    msg = str(e.value)
    assert "scale" in msg and "0" in msg
    # constraint + violation alone isn't enough; must also say the fix
    assert "pass" in msg.lower() or "use" in msg.lower()


def test_foreign_output_suffix_is_a_named_preview_error(tmp_path):
    with pytest.raises(preview.PreviewError) as e:
        preview.write(frames(1), tmp_path / "o.txt")
    msg = str(e.value)
    assert ".txt" in msg
    # names both accepted extensions and the fix
    assert ".png" in msg and ".gif" in msg


# --- candidates()/clear() blast radius ---------------------------------
#
# clear() exists to delete a stale preview before rendering. candidates()
# is what tells it what "a preview" even is, and it must mirror write()'s
# actual behaviour exactly -- write() only ever touches the literal path
# when that path already ends in .png or .gif; a bare stem or a foreign
# suffix are never written to literally. Anything wider than that is a
# data-loss bug: clear() unlinking a file llmbyt never authored.

def test_candidates_for_a_png_path_is_just_that_path(tmp_path):
    p = tmp_path / "o.png"
    assert preview.candidates(p) == [p]


def test_candidates_for_a_gif_path_is_just_that_path(tmp_path):
    p = tmp_path / "o.gif"
    assert preview.candidates(p) == [p]


def test_candidates_for_a_foreign_suffix_is_empty(tmp_path):
    """write() never writes to a .py (or any non-image-suffixed) path
    literally, so clear() must never consider deleting it."""
    assert preview.candidates(tmp_path / "clock.py") == []


def test_candidates_for_a_bare_stem_is_only_the_two_image_variants(tmp_path):
    """The bare stem itself (e.g. the default -o "out") is never a path
    write() would produce -- only "out.png"/"out.gif" are."""
    stem = tmp_path / "out"
    assert preview.candidates(stem) == [
        stem.with_suffix(".png"), stem.with_suffix(".gif")]


def test_clear_never_deletes_a_file_with_a_foreign_suffix(tmp_path):
    src = tmp_path / "clock.py"
    src.write_text("# the user's source, not an llmbyt artifact\n")
    preview.clear(src)
    assert src.exists()
    assert src.read_text() == "# the user's source, not an llmbyt artifact\n"


def test_clear_never_deletes_a_suffixless_file_matching_the_stem(tmp_path):
    """The documented default invocation (`llmbyt preview d.py`, -o
    defaulting to "out") must not destroy a plain file named "out"."""
    out = tmp_path / "out"
    out.write_text("the user's data, not a preview\n")
    preview.clear(out)
    assert out.exists()
    assert out.read_text() == "the user's data, not a preview\n"


def test_clear_still_removes_a_stale_png_and_gif_for_a_bare_stem(tmp_path):
    stem = tmp_path / "o"
    png, gif = stem.with_suffix(".png"), stem.with_suffix(".gif")
    png.write_bytes(b"stale png")
    gif.write_bytes(b"stale gif")
    preview.clear(stem)
    assert not png.exists()
    assert not gif.exists()


def test_clear_still_removes_a_stale_explicit_png(tmp_path):
    p = tmp_path / "o.png"
    p.write_bytes(b"stale")
    preview.clear(p)
    assert not p.exists()
