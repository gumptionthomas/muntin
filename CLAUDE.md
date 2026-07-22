# Working on muntin

This file is for agents **developing** muntin. `AGENTS.md` and `CRAFT.md` are for agents
**using** it to drive a display — different audience, don't merge them.

## Commands

    uv sync                  # after a fresh clone or a moved directory
    uv run pytest -q         # full suite, must stay warning-free
    uv run muntin --help

## Read first

`docs/decisions.md` records what is deliberate and would otherwise read as an oversight —
silent clipping, `Marquee(hold=0)`, the deliberately-duplicated `_check_frame_ms`, why
`[project.urls]` is absent. **Read it before "fixing" something that looks wrong.** Several
entries exist because someone already tried.

Site-local rationale lives in comments at the site. `preview.candidates`, `encode.take`,
`device.load_config`, and `scene.Marquee.measure` each explain themselves; don't restate
them elsewhere.

## Invariants

- **Pillow is the only runtime dependency.** stdlib `urllib` for HTTP, `tomllib` for TOML.
- **Every error derives from `errors.MuntinError` and names the constraint, the measured
  violation, and the fix.** An error that describes a problem without saying what to do is
  incomplete. This produced a review finding in every task of the original build.
- **`cli.main` catches `MuntinError` only.** Anything else keeps its traceback, because
  anything else is a bug in muntin. Do not broaden that `except`.
- **No test touches the network.** `device.push` takes an injected `poster`.
- **The API token is never printed or reachable** — not in messages, `repr`, or via
  `__context__` on a raised error.
- **Clamping the frame budget has one owner: `encode.take`.** If you are about to write
  `[:max_frames]`, route it through `take` instead.
- `scene` nodes: `draw(canvas, box, t)` must be a **pure function of `(box, t)`**. No state
  between frames, no mutation of `self`. Golden tests depend on it.

## Tests

Golden fixtures live in `tests/golden/`. On a genuine visual change, re-bless with
`GOLDEN_UPDATE=1 uv run pytest tests/test_golden.py` — then **open the regenerated PNGs and
confirm they look right**, since a golden blesses whatever it is handed.

Two tests in the original build passed against broken code: one asserted a number that
appeared in unrelated output, one used a solid-color fixture that could not distinguish
correct behavior from the bug it guarded. When adding a test, check that it **fails**
against the unfixed code.

## Verifying by eye

muntin exists so an agent can see its own output. Use it:

    uv run muntin preview examples/clock.py -o /tmp/check

then open the PNG. A passing suite does not tell you a display is legible.
