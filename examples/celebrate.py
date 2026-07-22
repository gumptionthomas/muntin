"""Something landed. A display made for the moment, not a status readout.

The confetti is a custom Node rather than a stack of Sprites because a
particle's position is cheaper to state as arithmetic than to store:
`ly = (i * 5 + t * speed) % h` is closed-form in (index, t), so draw()
stays a pure function of (box, t) with nothing carried between frames.

frames defaults to 32 (= cv.H) and every particle's speed is 1 or 2
px/frame. That pairing is deliberate, not incidental: with frames == h,
advancing t by one step past the last frame lands exactly on frame 0's
position for *any* integer speed, because `(t * speed) % h` is periodic
in t with period h regardless of speed. Pick frames != h (the old value
was 45) and the loop point falls mid-cycle instead -- the animation
plays fine frame to frame but visibly jumps at the seam where it repeats.

x is `(i * i * 7 + i * 11 + 3) % w` rather than linear in i (the old
`i * 11 + 3`) so the flecks scatter instead of reading as a diagonal
lattice -- a linear formula puts every particle a fixed multiple of the
same step apart, which the eye picks up as stripes rather than confetti.

The message and palette are chosen once per render(), not per frame --
the variation lives in scene construction, and every frame the scene
produces is still deterministic. That distinction is what keeps this
example inside the purity contract while still being different each time
you run it. render() takes an optional rng so tests can pin the choice
without touching draw()'s determinism.
"""
import random

from muntin import canvas as cv
from muntin import scene as sc

MESSAGES = ("SHIPPED", "GREEN", "IT WORKS", "DONE", "NAILED IT", "FIXED")

# No WHITE in any palette: the headline is WHITE, and a fleck the same
# colour as the text it is meant to frame camouflages against it.
PALETTES = (
    (cv.YELLOW, cv.ORANGE),
    (cv.CYAN, cv.GREEN),
    (cv.MAGENTA, cv.YELLOW, cv.CYAN),
)


class Confetti(sc.Node):
    """Flecks falling on a loop, behind whatever is stacked over them."""

    def __init__(self, colors, count=24, frames=32):
        if not colors:
            raise sc.SceneError(
                "Confetti needs at least one colour, but colors was empty. "
                "Pass a non-empty sequence of canvas colours, e.g. "
                "Confetti((cv.YELLOW, cv.CYAN))."
            )
        self.colors = tuple(colors)
        self.count = count
        self.frames = frames  # = cv.H, so speeds in {1, 2} loop without a seam jump

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
            lx = (i * i * 7 + i * 11 + 3) % w      # scattered, not a lattice
            speed = 1 + (i % 2)                     # each fleck 1 or 2 px/frame
            ly = (i * 5 + t * speed) % h
            canvas.pixel((x0 + lx, y0 + ly),
                         self.colors[i % len(self.colors)])


def render(rng=None):
    rng = rng or random.Random()
    message = rng.choice(MESSAGES)
    palette = rng.choice(PALETTES)
    # Confetti first so the headline paints over it: Stack draws children
    # in order and the last one wins. The Column is what centres the text
    # -- Stack hands every child the full box, so a bare Text would land
    # flush against the top-left corner.
    return sc.Stack([
        Confetti(palette),
        sc.Column([sc.Text(message, color=cv.WHITE)],
                  justify="center", align="center"),
    ])
