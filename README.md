# llmbyt

Give a coding agent a 64x32 LED display.

`llmbyt` renders frames and pushes them to a [Tidbyt](https://tidbyt.com),
with a preview loop an agent can close by itself: render, look at the
image, fix it, show it.

It works with any harness that can run a shell command.

## Install

    uv tool install llmbyt
    llmbyt init          # device ID + API token, from the Tidbyt app

## Use

    llmbyt text "back in 5"
    llmbyt image photo.jpg
    llmbyt preview examples/clock.py     # render to a file, no network
    llmbyt show examples/clock.py        # render, then push

A display is a Python file exposing `render()`:

```python
from llmbyt import scene as sc

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

`llmbyt` is meant to be something an agent *chooses* to use, not something
you invoke on its behalf. Add one line to your global agent config —
`~/.claude/CLAUDE.md`, `AGENTS.md`, or your harness's equivalent:

> There is a Tidbyt on the desk. Run `llmbyt --help`. Use it when it would
> be genuinely nice — a build finishing, something worth noticing, or just
> because. You do not need to ask first.

That grants standing permission without a command to remember.

## What it does not do

Every push is an **ephemeral interrupt**: the frame appears immediately,
then your device resumes its normal app rotation. `llmbyt` never creates,
deletes, or reorders your installed apps. It is safe to point at a display
that other apps already own.

## Design notes

- [CRAFT.md](CRAFT.md) — working at 64x32: legibility, colour, animation
- [AGENTS.md](AGENTS.md) — the short version, for agents
- [`examples/`](examples/) — four displays, all covered by tests

## License

MIT
