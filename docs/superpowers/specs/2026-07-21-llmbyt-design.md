# llmbyt — design

**Date:** 2026-07-21
**Status:** approved (design), pending implementation plan

## What this is

`llmbyt` gives a coding agent a 64×32 LED display. It turns intent into pixels on a
Tidbyt and closes the loop the agent needs to do that well: **render → look at it →
fix it → show it.**

It is a standalone, harness-agnostic Python package and CLI. It is not tied to Claude,
and it is not part of the `familiar` project.

The design target is agency, not invocation. The agent should be able to notice the
display exists and choose to use it — not wait to be told.

## Decisions

| Decision | Choice |
|---|---|
| Distribution | New public repo + PyPI package, `llmbyt` (name verified free 2026-07-21) |
| Language | Python ≥3.11, `uv`, Pillow as the only runtime dependency |
| Display model | Ephemeral interrupt — show now, device resumes its own rotation |
| Render core | Layered: declarative scene DSL + raw frame escape hatch |
| Feedback loop | Render to file; the agent reads the image back itself |
| Interface | CLI. MCP server deferred to a later spec |
| Teaching surface | Instructive errors + `--help`, backed by one `CRAFT.md` |
| Error posture | Loud |

## Display model

Every push uses `background: false` against
`POST https://api.tidbyt.com/v0/devices/{id}/push`. The frame appears immediately and
the device then resumes its normal app rotation.

Pushes carry a stable `installationID` of `llmbyt`, so repeated pushes overwrite one
slot rather than accumulating installations on the device.

`llmbyt` never creates, deletes, or reorders anyone else's installations. That single
constraint removes an entire category of device-state management, and makes the tool
safe to run against a display that other apps already own.

Managing the rotation is explicitly out of scope (see Out of scope).

## The display contract

A *display* is a Python module exposing one function:

```python
def render():
    ...
```

Its return type decides how much control the author took:

| Returns | Meaning |
|---|---|
| a `Scene` node | declarative — laid out by the widget engine |
| a `PIL.Image` | one static frame, hand-drawn |
| an iterable of `PIL.Image` | animation, hand-drawn frame by frame |

`runner.py` loads the module by path and normalizes all three into a single list of
frames. There is no mode flag and no second entry point: the escape hatch is simply
returning something lower-level. An author reaches for raw frames by returning raw
frames.

Anything other than these three types is an error naming what was returned and listing
the three accepted forms.

## Module layout

```
canvas.py    Canvas over a 64x32 PIL image + drawing primitives
font.py      BDF bitmap font loader (extensible; ships two faces)
scene.py     the declarative widget vocabulary
encode.py    frames -> animated WebP, device caps enforced
preview.py   frames -> upscaled PNG/GIF with pixel grid
device.py    push client + config resolution
runner.py    load a display module, normalize render() output
cli.py       argument surface
```

`scene` depends on `canvas`; `canvas` depends on `font`. Nothing depends upward. Each
module is independently testable and small enough to hold in context at once.

## The scene engine

Every node implements exactly two methods:

```python
measure() -> (w, h)              # intrinsic size in pixels
draw(canvas, box, t) -> None     # paint into box at frame index t
```

`t` is the frame index, and it is the entire animation story. Static nodes ignore it.
Time-varying nodes additionally declare:

```python
frame_count() -> int
```

The root takes the maximum `frame_count()` across the tree, clamps it to the device
ceiling, and renders `t = 0 .. N-1`. There is no timeline object, no scheduler, and no
state carried between frames. A node given the same `(box, t)` always paints the same
pixels — which is also what makes golden-image testing meaningful.

### Vocabulary

Seven nodes:

- `Text(s, font=, color=)`
- `Row(children, gap=, align=, justify=)`
- `Column(children, gap=, align=, justify=)`
- `Stack(children)` — z-ordered overlay
- `Marquee(child, axis=, hold=, speed=)`
- `Sprite(image_or_path, fit=)`
- `Plot(values, color=)` — sparkline

`Row`/`Column` are Pixlet's box model minus the parts that go unused. `Plot` is the one
judgement call in the set: it is hand-rollable through the raw layer, but it is the most
useful single thing at this size and fiddly to get right, so it ships. Everything else
is load-bearing.

## Craft encoded in the layers

Three things matter only at 64×32, and so belong in code rather than in the author's
memory:

**Fonts carry the display.** 4×6 tom-thumb fits ~16 characters per line and is the
workhorse; a taller face is for anything read at a glance across a room. The loader
accepts any BDF from a fonts directory, so adding a face is dropping in a file. v1 ships
tom-thumb (4×6) and spleen (5×8); confirming both licenses permit redistribution is an
implementation task, and a face that fails that check is swapped, not shipped.

**A curated palette.** Saturated primaries read cleanly on the LEDs; mid-grays and
pastels turn to mush. The palette ships as named constants, and `CRAFT.md` explains why
the color that looked right on a monitor does not survive the panel.

**The animation ceiling is real and fails silently on the device.** Total duration is
capped at 14.5s, under the device's 15s limit. The encoder clamps and says so, naming
how many frames it dropped. Silent truncation is precisely the bug class that costs an
hour of confused iteration.

## Feedback loop

`preview.py` writes a PNG (single frame) or GIF (animation), upscaled 8× with a pixel
grid, before anything touches the network. The agent opens that file and sees the actual
pixels.

This is the core of the tool, not a convenience. Without it an agent designs 64×32 pixel
art blind and reports success it cannot have verified. `preview` exists as its own
command so the iteration loop costs nothing and reaches no network, which makes `show` a
deliberate act.

## Error posture

`llmbyt` is loud. Errors surface with full context and never fall back to a stale
artifact — an agent iterating against a stale PNG cannot tell that it is.

This is a deliberate inversion of `familiar`, which swallows every error by design so a
network hiccup cannot disturb its hardware path. That is correct for a background daemon
and wrong for an interactive authoring tool.

Errors also teach. They name the constraint, the measured violation, and the fix:

```
Text("the quick brown fox jumps") is 25 chars x 4px = 100px wide,
exceeds the 64px display. Wrap it, shorten it, or wrap it in Marquee.
```

This is the only teaching surface that reaches an agent in a harness with nothing
loaded, and it arrives exactly when it is needed.

## CLI

```
llmbyt init                    walk through device ID + token, write config
llmbyt preview <display.py>    render to out.gif/png; never touches the network
llmbyt show <display.py>       preview, then push
llmbyt text "..."              one-shot: type something, see it now
llmbyt image <path>            one-shot: fit + dither a real image down to 64x32
```

`--help` is a teaching surface and is written as one: it states the display size, the
duration cap, and the three accepted `render()` return types.

## Configuration

`~/.config/llmbyt/config.toml`:

```toml
device_id = "..."
api_token = "..."
```

Environment overrides `LLMBYT_DEVICE_ID` and `LLMBYT_API_TOKEN` take precedence, for CI
and for keeping the token out of the filesystem.

The token is redacted everywhere it could be printed — including in error output and
tracebacks, which is where credentials actually leak.

## Discovery

An invoked tool is not an available one. `llmbyt` is meant to be something an agent can
choose, so discovery is a standing invitation rather than a command.

The README ships a one-line addition for a user's global agent config — `~/.claude/CLAUDE.md`,
`AGENTS.md`, or the harness equivalent — to the effect of:

> There is a Tidbyt on the desk. Run `llmbyt --help`. Use it when it would be genuinely
> nice; you do not need to ask first.

That grants standing permission without a slash command, and works in any harness that
reads a config file.

The repo's own `AGENTS.md` is a thin pointer: the constraints table, the three
`render()` return types, and a link to `CRAFT.md`. It is deliberately not a second copy
of `CRAFT.md` — two copies of the same prose drift, and the condensed one rots first.

### CRAFT.md

The single canonical document behind the errors and `--help`. It covers what an error
message has no room to explain:

- **The loop.** Never `show` without `preview` and actually opening the image. Left
  unprompted, an agent will push blind and report that it looks great.
- **Legibility.** Characters per line for each shipped font, contrast minimums, why 1px
  detail reads as noise from across a room, why color alone cannot carry meaning on an
  LED matrix.
- **Animation.** The 14.5s budget, hold-then-scroll for text people need time to finish
  reading, frame rates that do not strobe.
- **The palette,** and why a color chosen on a monitor turns to mud on the panel.
- **Worked examples** to pattern-match from: a clock, a sparkline, a scrolling message,
  and one hand-drawn animation using the raw escape hatch.

## Testing

**Golden images are the backbone.** Render a scene, compare the PNG against a committed
fixture pixel-by-pixel with zero tolerance, emitting a diff image on failure.
`--update-goldens` re-blesses intentional changes. The deterministic `draw(canvas, box, t)`
contract is what makes this reliable.

Around that:

- Unit tests on `measure()` layout arithmetic for every node
- Encoder clamp tests — frame count, duration, the reported drop count
- Config resolution precedence: env over file, missing values, redaction
- Runner normalization across all three `render()` return types, plus the rejection path

The push client takes an injected poster, so no test touches the network. That pattern
works well in `familiar` and carries over directly.

## Out of scope for v1

Each is a candidate for its own later spec:

- **MCP server** — the expected next piece, for harnesses without shell access
- **Live web preview** — a browser panel to watch iteration in real time
- **Installation / rotation management** — creating, deleting, reordering device apps
- **Scheduling** — recurring or triggered displays
- **Multi-device** — one configured device only in v1

## Open questions

None. Ready for an implementation plan.
