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

**One inline worked example.** Small — a Column with a bright headline over a dim
subtitle — enough to convey the shape of a display without opening four files first.
`examples/` carries the rest.

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

## Optional, deferred

- **A fifth example built for delight.** All four current examples are informational —
  clock, message, sparkline, bounce. None is celebratory, so the skill has nothing honest
  to point at for the thing it is actually asking for. A `celebrate.py` would be covered
  by the existing example tests. Deferred pending the author's call.
- **Plugin packaging** and any `muntin skill --install` convenience — after the proving
  period.
