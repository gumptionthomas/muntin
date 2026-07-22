"""Command line surface.

--help is a teaching surface, not a reference card: an agent that runs it
and nothing else should still know the display size, the duration ceiling,
and the three things render() may return.
"""
import argparse
import getpass
import sys

from . import canvas as cv
from . import device, encode, preview, runner
from . import scene as sc
from .errors import MuntinError

EPILOG = f"""\
The display is {cv.W}x{cv.H} pixels. Animations are capped at
{encode.MAX_MS}ms; anything longer is truncated and reported.

A display is a Python file exposing render(), which returns one of:
  * a Scene node        -- laid out by the scene engine (Text, Row,
                           Column, Stack, Marquee, Sprite, Plot)
  * a PIL Image         -- one static {cv.W}x{cv.H} frame
  * an iterable of them -- an animation, frame by frame

Always `preview` and look at the image before you `show`.

  muntin preview clock.py      # render to a file, no network
  muntin show clock.py         # render, look, then push to the device
  muntin text "back in 5"      # one-shot message
  muntin image cat.jpg --no-push   # one-shot, but look before it lands

`text` and `image` push as soon as they run; --no-push writes the preview
and stops there.
"""


def build_parser():
    p = argparse.ArgumentParser(
        prog="muntin",
        description="Put pixels on a Tidbyt.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    def with_output(sp):
        sp.add_argument("-o", "--out", default="out",
                        help="preview path (extension chosen automatically)")
        sp.add_argument("--scale", type=int, default=preview.DEFAULT_SCALE,
                        help="preview upscale factor (default 8)")
        sp.add_argument("--frame-ms", type=int,
                        default=encode.FRAME_MS_DEFAULT,
                        help="milliseconds per frame (default 100)")
        sp.add_argument("--no-grid", action="store_true",
                        help="omit the pixel grid in the preview")
        return sp

    def with_no_push(sp):
        # Only on the one-shot verbs. `preview` never pushes and `show`
        # exists to, so --no-push there would just be a second spelling of
        # `preview`. On `text` and `image` it is the only way to obey
        # AGENTS.md's "look at it before it reaches the device" -- most of
        # all for `image`, where the fit to 64x32 is what quietly loses
        # thin detail.
        sp.add_argument("--no-push", action="store_true",
                        help="write the preview only; never touch the network")
        return sp

    sub.add_parser("init", help="save your device ID and API token")
    with_output(sub.add_parser(
        "preview", help="render a display to a file; never touches the network")
    ).add_argument("display", help="path to a Python file exposing render()")
    with_output(sub.add_parser(
        "show", help="render a display, then push it to the device")
    ).add_argument("display", help="path to a Python file exposing render()")
    with_no_push(with_output(sub.add_parser(
        "text", help="show a one-shot message"))
    ).add_argument("message")
    with_no_push(with_output(sub.add_parser(
        "image", help="fit an image to the display and show it"))
    ).add_argument("path")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 2
    try:
        return _dispatch(args)
    except MuntinError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _dispatch(args) -> int:
    if args.cmd == "init":
        return _init()

    # Before anything is rendered, not after it succeeds: if the render
    # raises, the previous run's preview must not still be sitting there
    # looking current.
    preview.clear(args.out)

    if args.cmd == "preview":
        return _render(*runner.frames_from(args.display, args.frame_ms),
                       args=args, push=False)
    if args.cmd == "show":
        return _render(*runner.frames_from(args.display, args.frame_ms),
                       args=args, push=True)
    if args.cmd == "text":
        return _render(*sc.render_scene(_message(args.message),
                                        frame_ms=args.frame_ms),
                       args=args, push=not args.no_push)
    if args.cmd == "image":
        node = sc.Sprite(args.path, fit="contain")
        # Column, not Stack: Stack hands its child the full box, so a
        # fitted image landed flush against the top edge instead of
        # centred. A Column of one centres on both axes.
        return _render(*sc.render_scene(
            sc.Column([node], justify="center", align="center"),
            frame_ms=args.frame_ms), args=args, push=not args.no_push)
    raise AssertionError(f"unreachable command {args.cmd!r}")


def _message(text):
    """Wrap text to the display, scrolling it if it does not fit."""
    from . import font
    f = font.load()
    per_line = cv.W // f.char_w
    words, lines, cur = text.split(), [], ""
    for w in words:
        # A word longer than a whole line can never join `cur` -- break it
        # into line-sized chunks itself, the way a terminal wrapper would,
        # so no produced line ever exceeds per_line and every character of
        # the input is still displayed.
        while len(w) > per_line:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:per_line])
            w = w[per_line:]
        cand = (cur + " " + w).strip()
        if len(cand) > per_line and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    def stack(gap):
        return sc.Column([sc.Text(ln) for ln in lines], gap=gap,
                         align="center")

    column = stack(1)
    if column.measure()[1] > cv.H:
        # A single pixel of leading is what puts five wrapped lines at
        # 34px -- 2px over the display. A Marquee can only express 2px of
        # travel as a crawl that snaps back when the loop repeats, which
        # reads as a glitch, not a scroll. Closing the leading fits the
        # same text in 30px: readable all at once, no motion needed. The
        # 4x6 font carries its own vertical spacing, so the lines do not
        # collide. Only worth it when it actually decides the question --
        # anything still overflowing at gap=0 scrolls as before.
        tight = stack(0)
        if tight.measure()[1] <= cv.H:
            column = tight
    if column.measure()[1] > cv.H:
        return sc.Marquee(column, axis="y", hold=14)
    return sc.Column([column], justify="center", align="center")


def _render(frames, budget, args, push) -> int:
    path = preview.write(frames, args.out, scale=args.scale,
                         grid=not args.no_grid, frame_ms=args.frame_ms)
    print(f"preview: {path}  ({len(frames)} frame"
          f"{'s' if len(frames) != 1 else ''})")
    # On preview as well as show. An agent iterating with preview alone
    # has to learn its animation is over budget before it ever pushes,
    # and the frame count printed above cannot tell it -- that count is
    # what survived, not what was asked for.
    message = budget.message()
    if message:
        print(message, file=sys.stderr)
    if not push:
        return 0

    webp, _ = encode.to_webp(frames, frame_ms=args.frame_ms)
    device.push(webp, device.load_config())
    print(f"pushed {len(webp)} bytes to the device")
    return 0


def _init() -> int:
    # `init` is the only command that prompts, so it is the only one that
    # needs a terminal to prompt on -- and muntin's whole premise is being
    # driven by an agent, which is precisely an environment without one.
    # A pipe gave input() an EOFError and a closed stdin (sys.stdin is
    # None) gave it "RuntimeError: lost sys.stdin"; both escaped as
    # tracebacks, which main() reserves for bugs in muntin. This is a
    # usage problem with a documented way out, so it says so. Checked
    # before the first prompt: half a prompt written into a pipe and then
    # a failure is worse than no prompt at all.
    if sys.stdin is None or not sys.stdin.isatty():
        raise device.ConfigError(
            "`muntin init` prompts for a device ID and an API token, so it "
            "needs an interactive terminal -- stdin here is not one. Run "
            "`muntin init` in a terminal, or skip the prompts entirely by "
            "setting MUNTIN_DEVICE_ID and MUNTIN_API_TOKEN in the "
            "environment, which every other command reads too. Nothing "
            "was written."
        )
    print("Get both values from the Tidbyt mobile app: "
          "Settings > General > Get API Key.")
    device_id = input("Device ID: ").strip()
    # getpass.getpass(), not input(): input() echoes whatever is typed to
    # the terminal, which would make a token-bearing prompt claiming
    # otherwise a lie. getpass suppresses the echo for real.
    token = getpass.getpass("API token (hidden, not echoed): ").strip()

    missing = [n for n, v in (("a device ID", device_id),
                              ("an API token", token)) if not v]
    if missing:
        raise device.ConfigError(
            f"Missing {' and '.join(missing)}. Both a device ID and an "
            f"API token are required -- re-run `muntin init` and paste "
            f"both values from the Tidbyt app (Settings > General > Get "
            f"API Key). Nothing was written."
        )
    path = device.save_config(device.Config(device_id, token),
                              path=device.CONFIG_PATH)
    print(f"wrote {path} (mode 600)")
    return 0
