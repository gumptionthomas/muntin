"""The raw escape hatch: return frames, draw whatever you like.

Nothing here uses the scene engine -- render() hands back a list of
images and llmbyt encodes them as-is.
"""
from llmbyt import canvas as cv

FRAMES = 60


def render():
    frames = []
    for t in range(FRAMES):
        c = cv.Canvas()
        x = abs((t * 2) % (2 * (cv.W - 4)) - (cv.W - 4))
        y = abs((t * 3) % (2 * (cv.H - 4)) - (cv.H - 4))
        c.rect((x, y, 4, 4), cv.ORANGE, fill=True)
        c.line((0, cv.H - 1), (cv.W - 1, cv.H - 1), cv.DIM)
        frames.append(c.snapshot())
    return frames
