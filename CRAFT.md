# Working at 64x32

The display is 64 pixels wide and 32 tall. That is about 16 characters per
line in the default font. Everything below follows from how small that is
and from the fact that it is an LED panel seen from across a room, not a
screen seen from a foot away.

## The loop

**Never `show` without `preview`, and never `preview` without opening the
image.**

    muntin preview thing.py      # writes out.png or out.gif
    # open it. look at it.
    muntin show thing.py

An agent that skips the middle step will report that a display looks good
without having any way to know. The preview is upscaled 8x with a pixel
grid and a bezel precisely so that overflow, collisions, and unreadable
text are obvious at a glance.

## Legibility

**Characters per line:**

| Font | Cell | Chars/line | Lines (practical) | Lines (max, gap=0) |
|---|---|---|---|---|
| `tom-thumb` (default) | 4x6 | 16 | 4 | 5 |
| `spleen-5x8` | 5x8 | 12 | 3 | 4 |

"Practical" = 2px gap between lines, 1px margin at top and bottom (30px available).
"Max" = zero gap, flush to edges (32px available).

Use `spleen-5x8` for anything read at a glance -- a time, a temperature, a
single number. Use `tom-thumb` when you need the density.

**The fonts are ASCII-only, and non-ASCII drops silently.** Both shipped
faces define codepoints 32-126 and nothing else. Any character outside
that range -- accented letters, curly quotes, em dashes, box drawing,
emoji -- renders as an empty cell of the same width, with no warning and
exit 0:

    muntin text "héllo — wörld ☃"     # shows: h llo  w rld

Spell it in ASCII (`hello - world`), or draw the glyph yourself with
`canvas.pixel`.

**One pixel of detail is noise.** A 1px gap between elements disappears at
distance; a 1px line reads as a smudge. Give elements 2px of separation
before you trust them to look separate.

**Contrast, not colour, carries meaning.** Text at `DIM` next to text at
`WHITE` reads as a hierarchy. Red text next to green text reads as "two
words" until you are close enough to see hue. Encode meaning in position
and brightness first; use colour to reinforce it, never to carry it alone.

**Leave the edges alone.** Content flush against x=0 or y=31 looks like it
has been cut off, because at a glance you cannot tell whether it has. One
pixel of margin fixes it.

## Colour

Use the named constants in `muntin.canvas`. They are chosen to survive the
panel:

    BLACK WHITE DIM RED GREEN BLUE YELLOW ORANGE CYAN MAGENTA

Two things surprise people:

**Pure blue is nearly invisible.** `(0, 0, 255)` on these LEDs reads as
dark grey-violet. `canvas.BLUE` is `(0, 80, 255)` -- lifted off pure blue
so it actually reads as blue.

**Pastels and mid-greys turn to mud.** A colour that looks like a soft
sage on your monitor arrives as an indeterminate grey. If you want a
muted tone, use `DIM` for grey or a saturated hue at low coverage --
fewer lit pixels, not dimmer ones.

## Animation

**The ceiling is 14500ms and the device does not warn you.** Past roughly
15 seconds the Tidbyt simply stops rendering, with nothing to see. muntin
clamps and tells you exactly how many frames it dropped -- on `preview`
as well as `show`, so you find out before you push. If you see that
message, shorten the animation or lower `frame_ms`.

frames x frame_ms must stay under 14500. At the 100ms default that is 145
frames.

**Hold before you scroll.** A `Marquee` that starts moving immediately is
unreadable -- the eye needs time to land. `hold=14` (about 1.4s) before
scrolling is the default for a reason.

**Do not strobe.** Anything alternating faster than about 200ms reads as
flicker rather than motion, and on a device sitting in someone's
peripheral vision that is genuinely unpleasant. Slow is better than fast.

## Choosing a layer

Start declarative. Reach for raw frames when the scene vocabulary is
fighting you:

    def render():
        return sc.Column([...])          # laid out for you

    def render():
        return [canvas.snapshot(), ...]  # you draw every pixel

There is no mode flag. Returning something lower-level *is* how you take
more control. See `examples/bounce.py`.

## Worked examples

| File | Shows |
|---|---|
| `examples/clock.py` | declarative layout, two fonts, centring |
| `examples/sparkline.py` | data, `Plot`, a `Row` label above it |
| `examples/message.py` | overflow handled by scrolling |
| `examples/bounce.py` | the raw escape hatch, frame by frame |

All four are rendered by the test suite, so they cannot rot.
