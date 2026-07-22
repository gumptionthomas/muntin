# Agent adoption: getting agents to choose the display

**Status:** approved, not implemented
**Date:** 2026-07-22

## The problem

muntin works. Nothing uses it.

The capability exists (a CLI), and the craft guidance exists (`CRAFT.md`). What is
missing is a **trigger surface** — something that puts the display in an agent's mind at
the moment it would be worth using. The README's answer is a line in
`~/.claude/CLAUDE.md`. That line is not present on the author's own machine, which is
evidence about how well it travels.

The comparison that prompted this was the Chrome extension: an agent reaches for the
browser readily. Worth being precise about why, because the obvious answer is wrong. It
is not that the browser is exposed over MCP. It is that a **skill description** tells the
agent when the browser applies and how to use it well. Tools with no guidance are tools
nobody picks up. muntin's gap is the same shape, and it does not require MCP to close.

## Decisions taken

| Question | Answer |
|---|---|
| Audience | Both distribution and local, **local first** — prove the trigger fires before packaging it |
| What it is for | **Delight, not status.** Something made for the moment, not a notification channel |
| Cadence | **A few times a session** — when something lands |
| Mechanism | A **skill**, with the `CLAUDE.md` one-liner kept as the fallback for harnesses without skills |

"Delight, not status" is the load-bearing decision. It rules out the ambient-status
design, and it means the skill cannot merely grant permission — it has to carry craft. An
agent that pushes something illegible at 64×32 is worse than one that never pushes at
all.

It also keeps muntin out of familiar's territory. familiar pushes on a Claude Code hook:
the harness fires it, the agent is not involved, and it holds a permanent installation
slot. muntin is the opposite on every axis — the agent chooses, and the push is ephemeral.
The two coexist because they occupy different roles, and this design must not blur that.

## Non-goals

- **An MCP server.** Already scoped out of v1 deliberately. It solves shell-less
  harnesses, which is a distribution problem, not an adoption one. An MCP tool with no
  guidance would not be reached for either, so it does not substitute for the skill.
- **Hooks or any automatic firing.** That is familiar's model and contradicts muntin's
  stated premise that it is something an agent *chooses* to use.
- **Enforcing cadence.** Nothing can enforce it. It is stated as a norm.

## Design

### Artifacts

1. `skills/muntin/SKILL.md` in this repo — source of truth, versioned alongside the CLI
   it describes.
2. A symlink from `~/.claude/skills/muntin/` during the proving period, so the trigger
   text can be iterated without reinstalling.
3. A README section documenting the `~/.claude/CLAUDE.md` one-liner fallback.
4. `examples/celebrate.py` — the genre the skill is asking for, specified below.

Packaging as a plugin waits until the trigger is shown to fire. There is no point
packaging something that does not work.

### The description

The description is the only text an agent sees before deciding whether to open the skill,
so it does all the triggering work. It must fire on *work just landed and marking it
would be nice*, and not on *the user is asking about LED displays*.

> Put something on the desk's 64×32 LED display — a small drawing, a reaction, a
> flourish. Use when a piece of work lands and marking it would be genuinely nice: a
> feature finally working, a stubborn bug dying, a long build going green. Show something
> made for the moment, not a status readout. A few times a session at most; you do not
> need to ask permission.

Load-bearing choices:

- **"lands"** binds the trigger to completion, not to the topic of displays.
- **"made for the moment"** pushes toward composing a display rather than
  `muntin text "done"`.
- **"you do not need to ask permission"** is carried from the README. Without it an agent
  asks first, and asking ruins the effect.
- **"a few times a session"** states the cadence as a norm.

### The body

Short. Long skills do not get followed. Four parts:

**The loop, as non-negotiable.** Write a display, `muntin preview`, **open the PNG and
look**, fix, `muntin show`. This is the step an agent will skip, because rendering feels
like finishing. The skill states plainly that the agent cannot see the device and the
preview is its only evidence.

**A pointer to `CRAFT.md`, not a copy.** `CLAUDE.md` establishes that rationale lives at
its site and is not restated elsewhere; the same applies here. The skill links, CRAFT.md
teaches.

**One inline worked example, plus a pointer to the genre.** Inline: a Column with a
bright headline over a dim subtitle, small enough to convey the shape of a display
without opening four files first. Then a pointer to `examples/celebrate.py` for what a
display made *for a moment* looks like — the inline snippet teaches syntax, celebrate.py
teaches intent, and the two are doing different jobs.

**Guardrails.** Do not announce it in chat beforehand. Do not push what you have not
looked at. Do not use it for status; familiar owns the glass for ambient things. A few
times a session.

### Testing

**Automatable: a skill-rot test.** Every `muntin …` command line in `SKILL.md` is
extracted and parsed against the real `build_parser()`. If a flag is removed or
mistyped, the suite fails. A skill that teaches commands which no longer exist is worse
than no skill, and nothing else in the repo would catch that. This is the only new test
the design requires.

**Not automatable: real sessions.** Whether an agent *spontaneously* reaches for the
skill can only be observed. A proving period of a few days across normal work, watching
three things: does it fire at all, does it fire at reasonable moments, and is what it
makes any good. The symlink exists so this period is cheap to iterate through.

## Success criteria

1. The skill fires unprompted in ordinary sessions, without the user mentioning the
   display.
2. When it fires, the agent previews and looks before pushing — verifiable from the
   session transcript.
3. What reaches the glass is legible at 64×32.
4. Cadence lands near a few times a session, not once a week and not constantly.

Failing 1 means the description needs work. Failing 2 or 3 means the body does. Failing 4
in either direction is a wording problem, not a mechanism problem.

## `examples/celebrate.py`

Required, not optional. All four current examples are informational — clock, message,
sparkline, bounce. None is celebratory, so without this the skill would be asking for
delight while pointing at a clock, leaving the agent to invent the genre unaided.

**Confetti falling over a headline.** A `Stack` of a short bright word over a field of
particles. Motion is the point: a still frame reads as information, and things falling
read as *something just happened*. At 64×32 there is no room for nuance, so the motion
carries the feeling that detail cannot.

**It varies between runs** — the message and palette are drawn from small curated sets.
This demonstrates composing a display for a moment rather than copying a template, which
is the behaviour the skill is trying to produce.

### Where the variation lives

This is the part that would otherwise look like a violation of the purity invariant, so
it is stated plainly: **variation happens at scene-construction time, never at draw
time.** `render()` picks a seed, a message and a palette once, then builds a scene whose
`draw()` closes over those as constants. Every frame remains a pure function of
`(box, t)`; each particle's position is closed-form, `y = (i * 7 + t * 3) % 40`, with no
state carried between frames and no mutation of `self`.

Two constraints follow from the existing test suite:

- `test_example_draws_something_visible` renders the first frame and asserts it is not
  black. Every combination the randomiser can produce must therefore draw something on
  frame 0 — the headline is always drawn, and no random choice may move content
  off-screen. A varying example that can flake is worse than a fixed one.
- Examples are collected by glob, so this file is covered by the existing example tests
  the moment it lands. No golden pins example pixels — goldens cover font sheets, the
  preview grid, and scene-layout primitives — which is what makes a varying example
  permissible at all.

## Generated images

Not part of this spec, recorded because it came up and the answer is non-obvious.

Generated rasters work at 64×32 only within a narrow band. Evidence from this project's
own testing: a generated sunset survived beautifully — large shapes, strong gradient,
high contrast — while its thin water glints vanished without a trace. **Silhouette and
colour survive; anything thin does not.** A prompt for this medium must ask for a bold
centred subject, two to four colours, no text and no fine lines.

Two reasons it is not the default for celebration. It produces a single still frame,
giving up the motion that makes something read as an event. And it depends on an
image-generation tool the agent may not have, so the skill cannot assume one.

Worth stating for whoever picks this up later: **muntin is already generative.** The agent
writes code that draws, which is generation native to the medium — nothing is downsampled
away, and it can respond to the actual moment. A generated image is a picture of
celebration; a drawn display can say `247 GREEN` with confetti falling on it, which is a
picture of *this* celebration. If the two are ever combined, the shape is a generated
backdrop with drawn motion and text over it in a `Stack`.

## Deferred

- **Plugin packaging** and any `muntin skill --install` convenience — after the proving
  period.
