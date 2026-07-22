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
