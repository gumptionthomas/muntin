# Agent Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give agents a reason and a way to choose the display — a Claude Code skill that triggers at the right moment, and a celebratory example that shows the genre the skill is asking for.

**Architecture:** Three artifacts over the existing CLI, no new runtime. `examples/celebrate.py` adds a custom `scene.Node` subclass whose particle positions are closed-form in `(index, t)`, wrapped in a `Stack` under a centred headline; it varies between runs by choosing message and palette once inside `render()`. `skills/muntin/SKILL.md` carries the trigger description and the loop. A skill-rot test parses every `muntin …` line in that markdown against the real `cli.build_parser()`, so a skill teaching commands that no longer exist fails the suite.

**Tech Stack:** Python 3.11+, Pillow, pytest, stdlib `random` and `shlex`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-22-agent-adoption-design.md`

## Global Constraints

- **Pillow is the only runtime dependency.** stdlib only otherwise (`random`, `shlex`, `importlib` are fine).
- **Every error derives from `errors.MuntinError`** and names the constraint, the measured violation, and the fix.
- **`cli.main` catches `MuntinError` only.** Do not broaden that `except`.
- **No test touches the network.**
- **`scene` nodes: `draw(canvas, box, t)` must be a pure function of `(box, t)`.** No state between frames, no mutation of `self`.
- **TDD: the failing test comes first**, and it must fail for the intended reason before any implementation.
- **The suite must stay warning-free.** Run `uv run pytest -q` from the repo root.
- Commit after each task.
- Display is 64×32; `tom-thumb` is 4×6, so 16 characters per line.

---

### Task 1: `examples/celebrate.py`

The genre the skill points at: confetti falling behind a centred headline, varying between runs.

**Files:**
- Create: `examples/celebrate.py`
- Create: `tests/test_celebrate.py`

**Interfaces:**
- Consumes: `muntin.scene.Node`, `muntin.scene.Stack`, `muntin.scene.Column`, `muntin.scene.Text`, `muntin.canvas` colour constants and `Canvas.pixel`.
- Produces: `examples/celebrate.py` exposing `render() -> scene.Stack`, and a module-level class `Confetti(colors, count=24, frames=45)` with `measure()`, `frame_count()` and `draw(canvas, box, t)`. `tests/test_celebrate.py` exposes no shared helpers.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_celebrate.py`:

```python
"""celebrate.py varies between runs, which the other example tests cannot
cover: test_example_draws_something_visible samples exactly one render,
and a varying example that can produce a blank frame would turn that into
an intermittent failure. These pin the invariants that make the variation
safe."""
import importlib.util
import pathlib

from muntin import canvas as cv
from muntin import runner

CELEBRATE = pathlib.Path(__file__).parent.parent / "examples" / "celebrate.py"


def _module():
    spec = importlib.util.spec_from_file_location("celebrate", CELEBRATE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_every_run_draws_something_on_the_first_frame():
    """The example picks its message and palette at random. Every
    combination it can reach must paint frame 0, or the shared example
    test flakes roughly one run in N."""
    for _ in range(50):
        frames, _ = runner.frames_from(CELEBRATE)
        assert frames[0].convert("RGB").getbbox() is not None


def test_the_message_varies_between_runs():
    """If it never varies, the example is a template to copy rather than
    a display composed for a moment -- which is the whole point of it."""
    seen = set()
    for _ in range(60):
        m = _module()
        node = m.render()
        seen.add(_headline(node))
    assert len(seen) > 1


def _headline(node):
    """Pull the Text string out of the scene, wherever it sits."""
    if hasattr(node, "s"):
        return node.s
    for attr in ("children", "child"):
        child = getattr(node, attr, None)
        if child is None:
            continue
        for c in (child if isinstance(child, list) else [child]):
            found = _headline(c)
            if found is not None:
                return found
    return None


def test_confetti_draw_is_a_pure_function_of_box_and_t():
    """The scene contract, and the reason goldens can be trusted. Drawing
    the same t twice must produce identical pixels, and drawing it must
    not mutate the node."""
    m = _module()
    node = m.Confetti((cv.YELLOW, cv.CYAN))
    a, b = cv.Canvas(), cv.Canvas()
    node.draw(a, (0, 0, cv.W, cv.H), 7)
    node.draw(b, (0, 0, cv.W, cv.H), 7)
    assert a.img.tobytes() == b.img.tobytes()


def test_confetti_actually_moves_between_frames():
    m = _module()
    node = m.Confetti((cv.YELLOW, cv.CYAN))
    a, b = cv.Canvas(), cv.Canvas()
    node.draw(a, (0, 0, cv.W, cv.H), 0)
    node.draw(b, (0, 0, cv.W, cv.H), 3)
    assert a.img.tobytes() != b.img.tobytes()


def test_confetti_never_paints_outside_the_box_it_is_given():
    """Silent clipping exists for Marquee, not as a licence for a node to
    scribble past the box it was handed. Drawn into a small box in the
    middle of the canvas, every lit pixel must fall inside it -- an
    assertion that merely checked 'something was drawn' would pass against
    a node painting over the whole display."""
    m = _module()
    node = m.Confetti((cv.WHITE,), count=60)
    bx, by, bw, bh = 10, 8, 20, 16
    c = cv.Canvas()
    node.draw(c, (bx, by, bw, bh), 5)
    px = c.img.convert("RGB").load()
    outside = [(x, y) for x in range(cv.W) for y in range(cv.H)
               if not (bx <= x < bx + bw and by <= y < by + bh)
               and px[x, y] != cv.BLACK]
    assert outside == [], f"painted outside the box at {outside[:5]}"
    inside = [(x, y) for x in range(bx, bx + bw) for y in range(by, by + bh)
              if px[x, y] != cv.BLACK]
    assert inside, "drew nothing inside the box"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_celebrate.py -q`

Expected: FAIL at collection or in `_module()` with `FileNotFoundError` / `ImportError`, because `examples/celebrate.py` does not exist yet.

- [ ] **Step 3: Write the example**

Create `examples/celebrate.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_celebrate.py -q`
Expected: PASS, 6 tests.

Then run the whole suite, which picks the new example up by glob:

Run: `uv run pytest -q`
Expected: PASS. The count rises by more than 6 — `test_examples.py` parametrizes over `examples/*.py`, so `celebrate` gains its own ids there too.

- [ ] **Step 5: Look at it**

Run: `uv run muntin preview examples/celebrate.py -o /tmp/celebrate`

Open `/tmp/celebrate.gif` and confirm: the headline is legible, the confetti reads as falling rather than as noise, and the two do not camouflage each other. Run it three or four times to see different messages and palettes. A passing suite does not tell you a display is legible.

If the confetti makes the text hard to read, reduce `count` from 24 rather than dimming the palette — fewer bright flecks read better at this size than many dim ones.

- [ ] **Step 6: Commit**

```bash
git add examples/celebrate.py tests/test_celebrate.py
git commit -m "feat: celebrate.py, a display made for a moment

All four existing examples are informational. This is the genre the
adoption skill asks for, so it needs something honest to point at.

Confetti is a custom Node: each fleck's position is closed-form in
(index, t), so draw() stays a pure function of (box, t). The message and
palette vary per run, chosen once in render() -- the variation lives in
scene construction, never in draw, which is what keeps a varying example
inside the purity contract.

Both coordinates are modulo the box size, so every combination paints on
frame 0 and test_example_draws_something_visible cannot flake."
```

---

### Task 2: The skill and its rot test

**Files:**
- Create: `skills/muntin/SKILL.md`
- Create: `tests/test_skill.py`

**Interfaces:**
- Consumes: `muntin.cli.build_parser()` (already in the repo, unchanged by this plan), and `examples/celebrate.py` from Task 1, which the skill references by path.
- Produces: `skills/muntin/SKILL.md` with YAML frontmatter containing `name: muntin` and a `description:` field. `tests/test_skill.py` exposes no shared helpers.

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill.py`:

```python
"""A skill that teaches commands muntin cannot run is worse than no skill:
the agent follows it, the command fails, and the failure looks like the
tool is broken. Nothing else in the repo would catch that -- the skill is
markdown, and markdown does not get imported."""
import pathlib
import shlex

import pytest

from muntin import cli

SKILL = (pathlib.Path(__file__).parent.parent
         / "skills" / "muntin" / "SKILL.md")


def _commands():
    if not SKILL.exists():
        return []
    out = []
    for raw in SKILL.read_text().splitlines():
        line = raw.strip()
        # --help exits zero through SystemExit, which parse_args cannot
        # distinguish from a rejection here; it is also the one command
        # that cannot go stale.
        if line.startswith("muntin ") and "--help" not in line:
            out.append(line)
    return out


def test_the_skill_file_exists():
    assert SKILL.exists(), f"no skill at {SKILL}"


def test_the_skill_teaches_some_commands():
    assert len(_commands()) >= 3


def test_the_skill_names_the_preview_loop():
    """The one instruction an agent will skip, because rendering feels
    like finishing. If the words are not there, the loop is not taught."""
    text = SKILL.read_text().lower() if SKILL.exists() else ""
    assert "preview" in text
    assert "look" in text


@pytest.mark.parametrize("line", _commands() or ["<no skill file>"])
def test_every_command_in_the_skill_parses(line):
    if line == "<no skill file>":
        pytest.fail(f"no commands found in {SKILL}")
    parser = cli.build_parser()
    try:
        parser.parse_args(shlex.split(line, comments=True)[1:])
    except SystemExit:
        pytest.fail(
            f"SKILL.md teaches a command muntin cannot parse: {line!r}. "
            f"Either the flag was removed from cli.build_parser() or the "
            f"skill has a typo -- fix whichever is wrong, but they must "
            f"agree.")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_skill.py -q`
Expected: FAIL — `test_the_skill_file_exists` fails with "no skill at …", `test_the_skill_teaches_some_commands` fails `assert 0 >= 3`, and the parametrized case fails with "no commands found".

- [ ] **Step 3: Write the skill**

Create `skills/muntin/SKILL.md`:

```markdown
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

`examples/celebrate.py` is the shape of a display made for a moment
rather than for information: motion behind a short bright word. Read it
before you write your own. The other examples in `examples/` are
informational by design and will pull you toward status if you copy them.

**Read CRAFT.md before designing anything.** It covers legibility,
colour and animation at this size - the difference between a display that
is valid and one that can be read across a room.

## Restraint

A few times a session, when something lands. Not a status channel: the
display has its own apps and its own life, and you are interrupting them.

Do not announce it first. Do not ask whether you should. Just make
something good, look at it, and send it.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_skill.py -q`
Expected: PASS. The parametrized test should now report 5 cases — the five `muntin …` lines in the skill.

Run: `uv run pytest -q`
Expected: PASS, whole suite, warning-free.

- [ ] **Step 5: Prove the rot test actually bites**

The test is worthless if it passes against a broken skill. Verify it fails on a command muntin cannot run:

The file is not committed yet at this point, so restore from a copy rather than from git:

```bash
cp skills/muntin/SKILL.md /tmp/SKILL.md.bak
printf '\n    muntin text "x" --bogus-flag\n' >> skills/muntin/SKILL.md
uv run pytest tests/test_skill.py -q 2>&1 | tail -5
```

Expected: FAIL, with the message naming `--bogus-flag`. Then restore and confirm green:

```bash
cp /tmp/SKILL.md.bak skills/muntin/SKILL.md
uv run pytest tests/test_skill.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/muntin/SKILL.md tests/test_skill.py
git commit -m "feat: a skill so agents find the display on their own

muntin works and nothing uses it. The capability and the craft guidance
both exist; what was missing is a trigger surface. The description is the
whole design -- it is the only text an agent sees before deciding whether
to open the skill, so it fires on work landing rather than on the topic
of displays.

The rot test parses every 'muntin ...' line in the markdown against the
real build_parser(). A skill teaching commands that no longer exist is
worse than no skill: the agent follows it, the command fails, and muntin
looks broken. Nothing else here would catch that, since markdown is never
imported."
```

---

### Task 3: Install it locally, and document the fallback

**Files:**
- Modify: `README.md` (the "Giving an agent the display" section)
- No test file — this task's verification is the skill appearing in a real session.

**Interfaces:**
- Consumes: `skills/muntin/SKILL.md` from Task 2.
- Produces: a symlink at `~/.claude/skills/muntin`; no code artefacts.

- [ ] **Step 1: Symlink the skill into the local agent config**

```bash
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/skills/muntin" ~/.claude/skills/muntin
ls -l ~/.claude/skills/muntin
```

Expected: a symlink pointing at `<repo>/skills/muntin`. A symlink rather than a copy so the trigger text can be iterated during the proving period without reinstalling.

- [ ] **Step 2: Verify the skill is well-formed where the harness will read it**

```bash
head -4 ~/.claude/skills/muntin/SKILL.md
```

Expected: the YAML frontmatter, with `name: muntin` and the full `description:` on one line. A description broken across lines will not parse as YAML.

- [ ] **Step 3: Update the README**

In `README.md`, replace the body of the "Giving an agent the display" section — keep the heading — with:

```markdown
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
```

- [ ] **Step 4: Verify the README's own instructions work**

Run the two commands from the README section verbatim in a scratch shell and confirm the symlink resolves:

```bash
readlink -f ~/.claude/skills/muntin/SKILL.md
```

Expected: the absolute path to `skills/muntin/SKILL.md` in this repo.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, warning-free.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: point the README at the skill, keep the line as fallback

The one-line-in-global-config mechanism was the README's only answer and
it was not installed on the author's own machine -- evidence about how
well it travels. Claude Code now gets the skill, which carries the trigger
and the craft together; the line stays for harnesses without skills."
```

---

## After the plan

The remaining work is observation, not implementation. Over the next few days of ordinary
sessions, watch three things and record them in the spec's success criteria:

1. **Does it fire unprompted?** If not, the description needs work — it is the only text
   that decides.
2. **Does the agent preview and look before pushing?** Check a transcript. If not, the
   loop section of the body needs strengthening.
3. **Is what reaches the glass legible, and is the cadence near a few times a session?**

Plugin packaging and any `muntin skill --install` convenience wait until the proving
period answers those. There is no point packaging a trigger that does not trigger.
