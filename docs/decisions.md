# Decisions

Things that are deliberate and would otherwise read as oversights.

Decisions that live at one site are commented at that site — `preview.candidates`,
`encode.take`, `device.load_config`, and `scene.Marquee.measure` all carry their own
rationale. This file is for what spans modules, what looks like an omission, and what a
reasonable contributor would try to "fix".

## Architecture

**A display's `render()` return type *is* the escape hatch.** A `Scene` node is laid out
for you; a `PIL.Image` is one hand-drawn frame; an iterable of them is an animation.
There is no mode flag and no second entry point, because adding one would mean choosing a
level of control before writing any code. Returning something lower-level is how you take
more control.

**Every push is an ephemeral interrupt.** `background: false` and **no `installationID`
at all**. `muntin` never creates, deletes, or reorders installations — including its own.
That single constraint removes an entire category of device-state management and makes
the tool safe to point at a display other apps already own. Rotation management is not a
missing feature — it is out of scope on purpose.

The two fields do different jobs, and conflating them was a real bug: `background`
controls *when* a frame appears, and the absence of an `installationID` is what stops it
from **staying**. Tidbyt's own client documents the flag as "Give your installation an ID
to keep it in the rotation" — supplying one is precisely what makes a push persist. This
entry previously described a fixed `installationID` as part of what made a push ephemeral.
It was the opposite: the pushed frame became a permanent app cycling on the device beside
its owner's real ones, found only when someone walked away and came back to a display
still showing a test card. `device.INSTALLATION_ID` is `""` and must stay `""`; the test
named `test_push_is_always_an_ephemeral_interrupt` asserted only `background` and passed
against the bug its name described.

**The preview loop is the product, not a convenience.** The agent driving this tool
cannot see the physical device, so a preview file is its only means of verification.
`preview` exists as its own command, reaching no network, so iteration is free and `show`
is a deliberate act. Anything that makes the preview less trustworthy — a stale artifact,
a silent truncation — is a defect in the core feature, not a rough edge.

**Clamping the animation budget has exactly one owner: `encode.take`.** This was learned
the hard way. Three layers independently clamped the frame count, and the only one that
could build a report never saw the pre-clamp number, so over-budget animations were
silently truncated on every path while `--help` promised the opposite. If you find
yourself adding a `[:max_frames]` anywhere, route it through `take` instead.

## Behaviour that looks wrong and isn't

**Drawing outside the canvas clips silently instead of raising.** `Marquee` scrolls an
oversized child by painting it at negative coordinates; if out-of-bounds drawing raised,
scrolling would be impossible. The clip behaviour is pinned by tests that assert *where*
the pixels land, not merely that nothing raised.

**`Marquee.measure()` clamps only the axis it scrolls.** Clamping both would exempt the
whole subtree from `render_scene`'s overflow check on the axis that does *not* scroll,
silently cropping content. An `axis="y"` marquee must still fit within 64px of width.

**`Marquee(hold=0)` shows no resting frame** — the first frame is already advanced one
step. `hold` is the count of static frames, so zero of them means motion starts
immediately. This differs from an earlier, accidentally-correct version.

**`hold` rests at *both* ends, so `frame_count()` is `hold + travel + hold`.** Arriving at
full travel is the only moment the child's far edge is visible — for a wrapped message,
its last line. Ending the animation on that frame showed it for a single frame before the
loop snapped back to the top, which made the end of every scroll unreadable. `draw()`
already clamps the offset to `travel`, so the appended frames need no special case.

**`Stack` hands each child the Stack's own box,** not a box sized to the child. Sizing to
the child gives an alignment-aware container zero slack, silently disabling its
`align`/`justify`.

**Containers reject `set` and `frozenset`.** Not because `PIL.Image` is unhashable — that
only rules out a set *of frames* — but because a set is unordered and animation frames
are inherently ordered.

**Non-ASCII characters render as blanks.** The bitmap fonts are ASCII-only. This is
documented in `CRAFT.md` rather than worked around; transliteration would guess at intent.

## Deliberate duplication

**`_check_frame_ms` exists in both `encode` and `preview`.** Two copies of a four-line
guard, differing only in the exception they raise. Parameterizing it would buy nothing and
couple two modules that are otherwise independent.

Frame-size validation went the other way: it was duplicated three times, drifted, and one
copy lost its "name the fix" clause. It now lives once in `canvas.check_frame_sizes`,
parameterized by error class. The line between these two cases is whether the copies have
somewhere to drift *to* — a guard with one correct form does not, a message does.

## Environment facts, established the expensive way

**Pillow's GIF writer coalesces pixel-identical consecutive frames.** Two identical frames
become one, with the durations summed. Never assert `n_frames == len(frames)` unless the
frames genuinely differ.

**tom-thumb's `FONTBOUNDINGBOX` understates its width.** It says 3; the font is 4 wide.
Cell width comes from `DWIDTH`, over ASCII glyphs only — some of its non-ASCII glyphs
advance 6.

**`raise ... from None` does not clear `__context__`.** It only suppresses it from
printed tracebacks; the original exception object stays reachable as an attribute. Where
an inner exception could carry the API token, the error is constructed inside the `except`
block and raised *outside* it, so nothing is being handled at raise time and `__context__`
is never attached. `device.push` and `device.load_config` both do this.

**`json.dumps` is not a TOML string encoder.** With `ensure_ascii=True` it emits UTF-16
surrogate pairs for non-BMP characters, which `tomllib` rejects — `save_config` would
succeed and every later run would fail to read it. `ensure_ascii=False` is required.

## Errors

Every error derives from `errors.MuntinError` and names **the constraint, the measured
violation, and the fix**. An error that describes a problem without saying what to do
about it does not meet the bar. This matters more than usual here: for an agent running in
a harness with nothing else loaded, the error message is the only teaching surface that
arrives at the moment it is needed.

`cli.main` catches `MuntinError` and prints it without a traceback — the message is the
interface. Anything else keeps its traceback, because anything else is a bug in `muntin`.
Do not broaden that `except`.

## Deletion

`preview` removes stale artifacts before rendering, so a failed render cannot leave a
previous image behind under a name an agent would open. Getting this wrong caused the
worst defect in the project's history: the delete path was written as a *superset* of the
write path, so the default invocation deleted an unrelated user file named `out`, and
`-o clock.py` deleted the user's own display source and then reported "No such display".

**The blast radius of a deletion must be derived from what the tool actually authors,
never assumed.** `preview.candidates` exists to make that derivation explicit and is
tested against paths `write()` could not have produced.

**`README.md`'s links to other repo files are absolute, not relative.** The README is the
PyPI long description, and a relative link resolves against `pypi.org` there — so
`[CRAFT.md](CRAFT.md)` 404s on the project page while looking correct on GitHub. New links
to files in this repo must be full `https://github.com/gumptionthomas/muntin/...` URLs.
(`[project.urls]` was absent for the same family of reason — no remote existed, and a
fabricated `Homepage` is worse than an absent optional field. The remote now exists and the
field is populated.)

## Known gaps and open follow-ups

**Not yet published to PyPI.** Until it is, the README's `uv tool install muntin` line
describes an install that does not work. The name is unclaimed; the package builds and
passes `twine check`.

**Out of scope for v1, each deserving its own design:** an MCP server (the expected next
piece, for harnesses without a shell), a live web preview, installation/rotation
management, scheduling, and multi-device support.
