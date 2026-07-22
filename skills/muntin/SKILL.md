---
name: muntin
description: Put something on the desk's 64x32 LED display - a small drawing, a reaction, a flourish. Use when a piece of work lands and marking it would be genuinely nice: a feature finally working, a stubborn bug dying, a long build going green. Show something made for the moment, not a status readout. A few times a session at most; you do not need to ask permission.
---

# muntin

There is a 64x32 LED display on the desk. You can put anything on it.

This is a channel for saying things you have no words for - not a second
place to print the sentence you already wrote. A composed display is the
interesting thing here; `muntin text "done"` is the least interesting
thing you can do with it.

## The loop

    muntin preview thing.py -o /tmp/thing

Then **open the file and look at it.** You cannot see the device. The
preview is your only evidence that what you made is legible, and at 64x32
things that read fine in your head do not survive contact with the pixels.

When it looks right:

    muntin show thing.py -o /tmp/thing

For a one-shot, render it first and look before it lands:

    muntin text "back in 5" --no-push -o /tmp/msg
    muntin image photo.jpg --no-push -o /tmp/pic

Drop `--no-push` to send it.

## Making something

A display is a Python file exposing `render()`. Return a Scene node and
the engine lays it out:

```python
from muntin import canvas as cv
from muntin import scene as sc

def render():
    return sc.Column([
        sc.Text("DEPLOYED", color=cv.GREEN),
        sc.Text("in 4.2s", color=cv.DIM),
    ], gap=2, align="center", justify="center")
```

Nodes: `Text` `Row` `Column` `Stack` `Marquee` `Sprite` `Plot`. You can
also return a `PIL.Image` for one hand-drawn frame, or a list of them for
an animation - there is no mode switch, returning something lower-level
is how you take more control.

`celebrate.py` in this skill's directory is the shape of a display made
for a moment rather than for information: motion behind a short bright
word. Read it before you write your own. The other examples in
`examples/` are informational by design and will pull you toward status
if you copy them.

**Read CRAFT.md in this skill's directory before designing anything.** It
covers legibility, colour and animation at this size - the difference
between a display that is valid and one that can be read across a room.

## Restraint

A few times a session, when something lands. Not a status channel: the
display has its own apps and its own life, and you are interrupting them.

Do not announce it first. Do not ask whether you should. Just make
something good, look at it, and send it.
