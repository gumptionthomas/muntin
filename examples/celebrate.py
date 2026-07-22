"""Something landed. A display made for the moment, not a status readout.

The confetti is a custom Node rather than a stack of Sprites because a
particle's position is cheaper to state as arithmetic than to store:
`ly = (i * 5 + t * 2) % h` is closed-form in (index, t), so draw() stays
a pure function of (box, t) with nothing carried between frames.

The message and palette are chosen once per render(), not per frame --
the variation lives in scene construction, and every frame the scene
produces is still deterministic. That distinction is what keeps this
example inside the purity contract while still being different each time
you run it.
"""
import random

from muntin import canvas as cv
from muntin import scene as sc

MESSAGES = ("SHIPPED", "GREEN", "IT WORKS", "DONE", "NAILED IT", "FIXED")

PALETTES = (
    (cv.YELLOW, cv.ORANGE, cv.WHITE),
    (cv.CYAN, cv.GREEN, cv.WHITE),
    (cv.MAGENTA, cv.YELLOW, cv.CYAN),
)


class Confetti(sc.Node):
    """Flecks falling on a loop, behind whatever is stacked over them."""

    def __init__(self, colors, count=24, frames=45):
        self.colors = tuple(colors)
        self.count = count
        self.frames = frames

    def measure(self):
        return (cv.W, cv.H)

    def frame_count(self):
        return self.frames

    def draw(self, canvas, box, t):
        x0, y0, w, h = box
        for i in range(self.count):
            # Both coordinates stay inside the box by construction: the
            # modulus is the box's own size, so there is no off-canvas
            # case to clip and no combination that paints nothing.
            lx = (i * 11 + 3) % w
            ly = (i * 5 + t * 2) % h
            canvas.pixel((x0 + lx, y0 + ly),
                         self.colors[i % len(self.colors)])


def render():
    r = random.Random()
    message = r.choice(MESSAGES)
    palette = r.choice(PALETTES)
    # Confetti first so the headline paints over it: Stack draws children
    # in order and the last one wins. The Column is what centres the text
    # -- Stack hands every child the full box, so a bare Text would land
    # flush against the top-left corner.
    return sc.Stack([
        Confetti(palette),
        sc.Column([sc.Text(message, color=cv.WHITE)],
                  justify="center", align="center"),
    ])
