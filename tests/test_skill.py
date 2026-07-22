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
