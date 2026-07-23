"""A skill that teaches commands muntin cannot run is worse than no skill:
the agent follows it, the command fails, and the failure looks like the
tool is broken. Nothing else in the repo would catch that -- the skill is
markdown, and markdown does not get imported."""
import argparse
import pathlib
import shlex

import pytest

from muntin import cli
from muntin import scene as sc

SKILL = (pathlib.Path(__file__).parent.parent
         / "skills" / "muntin" / "SKILL.md")

# Prefixes a copy-pasted command line plausibly carries in front of the
# real invocation -- a shell prompt, or running through uv. _commands()
# strips these before checking whether what remains is a muntin command;
# anything else containing "muntin " is a form this test cannot vouch
# for, and must be surfaced rather than silently dropped.
_SHELL_PREFIXES = ("$ ", "uv run ")


def _strip_shell_prefix(line):
    for prefix in _SHELL_PREFIXES:
        if line.startswith(prefix):
            return line[len(prefix):]
    return line


def _commands():
    if not SKILL.exists():
        return []
    out = []
    for raw in SKILL.read_text().splitlines():
        line = _strip_shell_prefix(raw.strip())
        # --help exits zero through SystemExit, which parse_args cannot
        # distinguish from a rejection here; it is also the one command
        # that cannot go stale.
        if line.startswith("muntin ") and "--help" not in line:
            out.append(line)
    return out


def _disguised_commands():
    """Lines that mention 'muntin ' but, even after stripping a leading
    shell prompt or 'uv run ', still don't start with 'muntin ' -- a form
    _commands() above would silently skip rather than parse. A rot test
    that quietly ignores lines it cannot handle is worse than one with no
    coverage at all, because it looks green.

    Restricted to indented lines -- this skill's only code blocks are
    4-space-indented shell examples -- so prose that merely mentions
    `muntin text "done"` inline, or an import statement inside the
    fenced python snippet (neither of which is a command to run), is not
    mistaken for a command this test failed to parse."""
    if not SKILL.exists():
        return []
    out = []
    for raw in SKILL.read_text().splitlines():
        if raw == raw.lstrip():
            continue  # not an indented shell-example line
        line = raw.strip()
        if "muntin " not in line or "--help" in line:
            continue
        if not _strip_shell_prefix(line).startswith("muntin "):
            out.append(line)
    return out


def _body():
    """The document below the frontmatter fence. The `description:` line
    in the frontmatter is packed with words like "preview" is not --
    tests anchored to the whole file can pass even if the body's actual
    instruction was deleted."""
    if not SKILL.exists():
        return ""
    text = SKILL.read_text()
    parts = text.split("---", 2)
    return parts[2] if len(parts) > 2 else text


def _first_python_fence():
    text = SKILL.read_text()
    marker = "```python"
    start = text.index(marker) + len(marker)
    end = text.index("```", start)
    return text[start:end]


def _real_option_strings(subcommand):
    """The flags cli.build_parser() actually defines for `subcommand`,
    read from the live parser rather than restated by hand -- so this
    check cannot itself drift from the CLI it is checking."""
    parser = cli.build_parser()
    sub_action = next(a for a in parser._subparsers._group_actions
                       if isinstance(a, argparse._SubParsersAction))
    child = sub_action.choices[subcommand]
    strings = set()
    for action in child._actions:
        strings.update(action.option_strings)
    return strings


def test_the_skill_file_exists():
    assert SKILL.exists(), f"no skill at {SKILL}"


def test_the_skill_teaches_some_commands():
    assert len(_commands()) >= 3


def test_the_skill_has_no_commands_this_test_cannot_extract():
    disguised = _disguised_commands()
    assert disguised == [], (
        f"SKILL.md has a line containing 'muntin ' that this test cannot "
        f"extract as a command to parse: {disguised!r}. Rewrite it as a "
        f"bare `muntin ...` line (optionally prefixed with '$ ' or "
        f"'uv run '), or extend _SHELL_PREFIXES / _commands() to cover "
        f"the new form -- do not let it silently pass unchecked.")


def test_the_skill_names_the_preview_loop():
    """The one instruction an agent will skip, because rendering feels
    like finishing. If the words are not there, the loop is not taught.
    Anchored to the body, not the whole file, so deleting the loop
    section cannot pass just because the frontmatter still says
    "preview" and "look"."""
    text = _body().lower()
    assert "preview" in text
    assert "look" in text


def test_the_loop_is_phrased_as_non_negotiable():
    """AGENTS.md says 'Never show without previewing' and CRAFT.md says
    'Never show without preview'. A skill that only says the loop is a
    good idea sets a lower bar than the two documents it is meant to
    agree with."""
    text = _body().lower()
    assert "always" in text or "never" in text or "must" in text, (
        "the loop section should say the preview step is mandatory -- "
        "'always', 'never', or 'must' -- not merely encourage it")


def test_the_skill_states_its_preconditions():
    """An agent that has never run muntin does not know it needs to be
    on PATH, or that pushing needs a device configured -- one line saves
    a confusing first failure."""
    text = _body().lower()
    assert "path" in text
    assert ("muntin init" in text or "muntin_device_id" in text
            or "muntin_api_token" in text)


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


@pytest.mark.parametrize("line", _commands() or ["<no skill file>"])
def test_no_command_in_the_skill_relies_on_an_abbreviated_flag(line):
    """argparse accepts any unambiguous prefix of a long flag by default,
    so `--no-pu` parses today as short for `--no-push` -- and would keep
    "working" right up until a second flag starting with --no-pu is
    added, at which point it breaks with no warning here. Every --flag
    token the skill teaches must match a real option string exactly."""
    if line == "<no skill file>":
        pytest.fail(f"no commands found in {SKILL}")
    tokens = shlex.split(line, comments=True)
    if len(tokens) < 2:
        return
    subcommand = tokens[1]
    parser = cli.build_parser()
    sub_action = next(a for a in parser._subparsers._group_actions
                       if isinstance(a, argparse._SubParsersAction))
    if subcommand not in sub_action.choices:
        return  # test_every_command_in_the_skill_parses already covers this
    valid = _real_option_strings(subcommand)
    for tok in tokens[2:]:
        if not tok.startswith("--"):
            continue
        flag = tok.split("=", 1)[0]
        assert flag in valid, (
            f"{flag!r} in {line!r} is not one of muntin {subcommand}'s "
            f"real flags ({sorted(valid)}). If it still parses, argparse "
            f"is accepting it as an abbreviation, which is not documented "
            f"and will break the moment a second flag shares the prefix -- "
            f"spell it out in full in SKILL.md.")


def test_the_skill_snippet_actually_renders():
    """The fenced python block is what an agent copies verbatim. exec it
    and run it through the real scene engine, so a renamed kwarg or a
    dropped colour constant fails loudly here instead of in someone's
    copy-pasted display."""
    src = _first_python_fence()
    ns = {}
    exec(compile(src, str(SKILL), "exec"), ns)  # noqa: S102
    render = ns.get("render")
    assert render is not None, "the skill's python snippet defines no render()"
    node = render()
    frames, _budget = sc.render_scene(node)
    assert frames, "render_scene() produced no frames from the skill's snippet"
    assert frames[0].convert("RGB").getbbox() is not None, (
        "the skill's snippet renders a blank frame")


def test_the_inline_snippet_is_not_a_status_readout():
    """The skill's own thesis is 'not a status readout' -- an inline
    example reading DEPLOYED / in 4.2s undercuts the point it is meant to
    teach."""
    src = _first_python_fence().lower()
    assert "deployed" not in src
    assert "4.2s" not in src


# The skill is installed globally (~/.claude/skills/muntin -> this repo's
# skills/muntin/) and fires in any session, in any directory. Every file
# the skill's prose points at -- CRAFT.md, celebrate.py -- must resolve
# from inside skills/muntin/ itself, or the craft guidance the skill
# exists to carry is dead the moment the agent is not sitting in this
# repo. Bare relative paths like "CRAFT.md" resolve to nothing outside
# the repo root; only files that actually live in (or are symlinked into)
# skills/muntin/ survive the move.
REFERENCED_FILES = ("CRAFT.md", "celebrate.py")


@pytest.mark.parametrize("name", REFERENCED_FILES)
def test_every_file_referenced_by_the_skill_resolves(name):
    assert name in SKILL.read_text(), (
        f"{name} is no longer mentioned in {SKILL} -- update "
        f"REFERENCED_FILES in this test if that's intentional.")
    target = SKILL.parent / name
    assert target.exists(), (
        f"SKILL.md references {name}, but {target} does not exist. "
        f"The skill is installed globally and runs from its own "
        f"directory -- add a symlink at skills/muntin/{name} pointing at "
        f"the real file, so the reference resolves wherever the skill "
        f"is invoked from.")
