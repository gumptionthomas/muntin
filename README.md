# muntin

Give a coding agent a 64x32 LED display.

`muntin` renders frames and pushes them to a [Tidbyt](https://tidbyt.com),
with a preview loop an agent can close by itself: render, look at the
image, fix it, show it.

It works with any harness that can run a shell command.

*A muntin is the slender bar that divides a window into panes — the thing
that turns a sheet of glass into a grid of lit rectangles. Which is also a
reasonable description of a 64x32 LED matrix.*

## Install

    uv tool install muntin
    muntin init          # device ID + API token, from the Tidbyt app

## Use

    muntin text "back in 5"
    muntin image photo.jpg
    muntin image photo.jpg --no-push     # render it, look, don't send it
    muntin preview examples/clock.py     # render to a file, no network
    muntin show examples/clock.py        # render, then push

A display is a Python file exposing `render()`:

```python
from muntin import scene as sc

def render():
    return sc.Column([
        sc.Text("DEPLOY"),
        sc.Text("green", color=(0, 255, 0)),
    ], gap=2, align="center", justify="center")
```

Return a `Scene` node to be laid out for you, a `PIL.Image` for one
hand-drawn frame, or an iterable of images for an animation. There is no
mode switch — returning something lower-level is how you take more
control.

## Giving an agent the display

`muntin` is meant to be something an agent *chooses* to use, not something
you invoke on its behalf.

**Claude Code:** symlink the bundled skill, which carries the trigger and
the craft guidance together:

    mkdir -p ~/.claude/skills
    ln -sfn "$PWD/skills/muntin" ~/.claude/skills/muntin

**Any other harness:** add one line to your global agent config —
`AGENTS.md`, or whatever your harness reads:

> There is a Tidbyt on the desk. Run `muntin --help`. Use it when it would
> be genuinely nice — a build finishing, something worth noticing, or just
> because. You do not need to ask first.

Either way it grants standing permission without a command to remember.

## What it does not do

Every push is an **ephemeral interrupt**: the frame appears immediately,
then your device resumes its normal app rotation. `muntin` never creates,
deletes, or reorders your installed apps. It is safe to point at a display
that other apps already own.

## Design notes

- [CRAFT.md](https://github.com/gumptionthomas/muntin/blob/main/CRAFT.md) — working at
  64x32: legibility, colour, animation
- [AGENTS.md](https://github.com/gumptionthomas/muntin/blob/main/AGENTS.md) — the short
  version, for agents
- [`examples/`](https://github.com/gumptionthomas/muntin/tree/main/examples) — four
  displays, all covered by tests
- [docs/decisions.md](https://github.com/gumptionthomas/muntin/blob/main/docs/decisions.md)
  — what's deliberate and would otherwise look like an oversight. Read before "fixing"
  something that seems odd.

## License

MIT
