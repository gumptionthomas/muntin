"""Configuration and the Tidbyt push client.

Every push is an ephemeral interrupt: background=false against a fixed
installationID, so the frame shows immediately, the device then resumes
its own rotation, and repeated pushes overwrite one slot rather than
accumulating installations. llmbyt never creates, deletes, or reorders
anyone else's apps.

The API token is never printed. Config.redact() scrubs it from any string,
and every error out of push() goes through it first.
"""
import base64
import json
import os
import pathlib
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass

from .errors import LlmbytError

PUSH_URL = "https://api.tidbyt.com/v0/devices/%s/push"
INSTALLATION_ID = "llmbyt"
CONFIG_PATH = pathlib.Path(
    os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")
) / "llmbyt" / "config.toml"
TIMEOUT = 15


class ConfigError(LlmbytError):
    pass


class PushError(LlmbytError):
    pass


@dataclass(frozen=True)
class Config:
    device_id: str
    api_token: str

    def redact(self, text: str) -> str:
        if self.api_token:
            return str(text).replace(self.api_token, "<REDACTED>")
        return str(text)

    def __repr__(self):
        return f"Config(device_id={self.device_id!r}, api_token='<REDACTED>')"


def load_config(env=None, path=None) -> Config:
    env = os.environ if env is None else env
    path = CONFIG_PATH if path is None else pathlib.Path(path)

    values = {}
    if path.exists():
        with open(path, "rb") as f:
            values = tomllib.load(f)

    device_id = env.get("LLMBYT_DEVICE_ID") or values.get("device_id")
    api_token = env.get("LLMBYT_API_TOKEN") or values.get("api_token")

    missing = [n for n, v in (("device_id", device_id),
                              ("api_token", api_token)) if not v]
    if missing:
        raise ConfigError(
            f"Missing {' and '.join(missing)}. Run `llmbyt init` to write "
            f"{path}, or set LLMBYT_DEVICE_ID and LLMBYT_API_TOKEN in the "
            f"environment. Get both from https://tidbyt.dev/ -- the device "
            f"ID and API key are in the Tidbyt mobile app under "
            f"Settings > General > Get API Key."
        )
    return Config(device_id=device_id, api_token=api_token)


def save_config(cfg: Config, path=None) -> pathlib.Path:
    path = CONFIG_PATH if path is None else pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False: with the default (True), characters outside the
    # Basic Multilingual Plane are emitted as UTF-16 surrogate pairs, which
    # are not valid TOML \uXXXX escapes (a lone surrogate is not a Unicode
    # scalar value) -- tomllib then refuses to load the file we just wrote.
    # With ensure_ascii=False those characters are written literally, which
    # is valid inside a TOML basic string; ", \, and control characters are
    # still escaped either way, since that escaping doesn't depend on
    # ensure_ascii.
    body = (f"device_id = {json.dumps(cfg.device_id, ensure_ascii=False)}\n"
            f"api_token = {json.dumps(cfg.api_token, ensure_ascii=False)}\n")

    # Open with the restrictive mode from the outset so the token-bearing
    # file is never created world- or group-readable, regardless of the
    # process umask (umask can only clear bits, and 0o600 has none set in
    # the group/other range for it to clear). os.open()'s mode argument
    # only applies at creation time though -- if `path` already exists
    # (e.g. a prior, looser save) its mode is left untouched by O_CREAT, so
    # fchmod it explicitly before writing any bytes. That closes the gap
    # for both the new-file and pre-existing-file cases before the token
    # ever hits disk.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
    except BaseException:
        os.close(fd)
        raise
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def _post(url, body, headers) -> int:
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


_HINTS = {
    401: "the API token was rejected. Check it, or re-run `llmbyt init`.",
    403: ("the API token is not permitted to push to this device. Generate "
          "a new token for this device in the Tidbyt app, then re-run "
          "`llmbyt init`."),
    404: "no such device. Check the device ID, or re-run `llmbyt init`.",
}

_GENERIC_STATUS_HINT = (
    "the Tidbyt API rejected the push. Wait a moment and retry; if it keeps "
    "happening, check https://tidbyt.dev/status or contact Tidbyt support "
    "with this status code."
)


def push(webp: bytes, cfg: Config, *, poster=None) -> None:
    if not webp:
        raise PushError(
            "Refusing to push an empty payload -- render or encode a frame "
            "before calling push()."
        )

    body = json.dumps({
        "image": base64.b64encode(webp).decode(),
        "installationID": INSTALLATION_ID,
        "background": False,
    }).encode()
    headers = {"Authorization": "Bearer " + cfg.api_token,
               "Content-Type": "application/json"}

    # Build the wrapped error inside the except block (which only records
    # its message as a string, not the original exception object) but
    # raise it after the try/except statement has fully exited. At that
    # point no exception is being handled, so the interpreter has nothing
    # to attach as __context__ -- the unredacted transport exception is
    # never reachable from the raised PushError, not even via
    # err.__context__ for tooling that walks it directly.
    transport_error = None
    try:
        status = (poster or _post)(PUSH_URL % cfg.device_id, body, headers)
    except Exception as e:                    # noqa: BLE001 -- wrapped below
        transport_error = PushError(
            f"Push failed before a response reached the Tidbyt API: "
            f"{cfg.redact(e)}. Check your network connection and that "
            f"api.tidbyt.com is reachable, then retry."
        )

    if transport_error is not None:
        raise transport_error

    if status != 200:
        hint = _HINTS.get(status, _GENERIC_STATUS_HINT)
        raise PushError(cfg.redact(f"Push returned HTTP {status} -- {hint}"))
