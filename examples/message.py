"""Text too long for one screen: hold, then scroll."""
from muntin import canvas as cv
from muntin import scene as sc

WORDS = ("the build is green and every test passed on the first try "
         "which has never once happened before")


def render():
    lines = [WORDS[i:i + 16] for i in range(0, len(WORDS), 16)]
    return sc.Marquee(
        sc.Column([sc.Text(ln, color=cv.CYAN) for ln in lines],
                  gap=1, align="center"),
        axis="y", hold=14, speed=1)
