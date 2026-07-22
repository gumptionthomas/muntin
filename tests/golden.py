"""Pixel-exact image fixtures.

On mismatch, writes <name>.actual.png and <name>.diff.png beside the
fixture so the failure is inspectable rather than just a byte count.
Re-bless intentional changes with GOLDEN_UPDATE=1.
"""
import os
import pathlib

from PIL import Image, ImageChops

DIR = pathlib.Path(__file__).parent / "golden"


def assert_golden(img, name):
    DIR.mkdir(exist_ok=True)
    path = DIR / f"{name}.png"
    img = img.convert("RGB")

    if os.environ.get("GOLDEN_UPDATE") or not path.exists():
        img.save(path)
        if os.environ.get("GOLDEN_UPDATE"):
            return
        raise AssertionError(
            f"Created new golden {path}. Inspect it, then re-run. "
            f"If it is wrong, fix the code and delete the file."
        )

    expected = Image.open(path).convert("RGB")
    if img.size != expected.size:
        raise AssertionError(
            f"{name}: size {img.size} != golden {expected.size}")

    diff = ImageChops.difference(img, expected)
    if diff.getbbox() is not None:
        img.save(DIR / f"{name}.actual.png")
        ImageChops.invert(diff.convert("L")).save(DIR / f"{name}.diff.png")
        n = sum(1 for p in diff.convert("L").get_flattened_data() if p)
        raise AssertionError(
            f"{name}: {n} pixels differ from the golden. Wrote "
            f"{name}.actual.png and {name}.diff.png beside it. "
            f"Re-bless with GOLDEN_UPDATE=1 if the change is intended."
        )
