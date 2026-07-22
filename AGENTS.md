# muntin, for agents

A 64x32 LED display you can put anything on.

## The loop

    muntin preview thing.py    # writes out.png / out.gif -- OPEN IT AND LOOK
    muntin show thing.py       # push it to the device

Never `show` without previewing and actually looking at the image first.
You cannot see the device; the preview is the only way you know what you
made.

The one-shot verbs push as soon as you run them. Add `--no-push` to get
the same preview file without touching the device:

    muntin text "back in 5" --no-push
    muntin image photo.jpg --no-push     # then look, then drop the flag

Worth it for `image` especially -- fitting to 64x32 is where thin detail
disappears.

## Constraints

| | |
|---|---|
| Display | 64 x 32 RGB |
| Chars per line | 16 (`tom-thumb` 4x6), 12 (`spleen-5x8` 5x8) |
| Animation cap | 14500ms total (145 frames at the 100ms default) |
| Colour | use `muntin.canvas` constants; pure blue reads as black |

## A display

A Python file exposing `render()`, returning one of:

    from muntin import scene as sc
    def render():
        return sc.Column([sc.Text("hello")], justify="center")   # Scene node

    def render():
        return canvas.snapshot()                                  # one Image

    def render():
        return [c1, c2, c3]                                       # animation

Nodes: `Text` `Row` `Column` `Stack` `Marquee` `Sprite` `Plot`.

**Read [CRAFT.md](CRAFT.md) before designing anything.** It covers
legibility, colour, and animation at this size -- the things that decide
whether a display is readable rather than merely valid. Working examples
are in [`examples/`](examples/).
