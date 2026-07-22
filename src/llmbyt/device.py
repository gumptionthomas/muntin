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
    body = (f"device_id = {json.dumps(cfg.device_id)}\n"
            f"api_token = {json.dumps(cfg.api_token)}\n")
    path.write_text(body)
    path.chmod(0o600)
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
    403: "the API token is not permitted to push to this device.",
    404: "no such device. Check the device ID, or re-run `llmbyt init`.",
}


def push(webp: bytes, cfg: Config, *, poster=None) -> None:
    if not webp:
        raise PushError("Refusing to push an empty payload.")

    body = json.dumps({
        "image": base64.b64encode(webp).decode(),
        "installationID": INSTALLATION_ID,
        "background": False,
    }).encode()
    headers = {"Authorization": "Bearer " + cfg.api_token,
               "Content-Type": "application/json"}

    try:
        status = (poster or _post)(PUSH_URL % cfg.device_id, body, headers)
    except Exception as e:                    # noqa: BLE001 -- reraised below
        raise PushError(
            f"Push failed before a response: {cfg.redact(e)}"
        ) from None

    if status != 200:
        hint = _HINTS.get(status, "the Tidbyt API rejected the push.")
        raise PushError(cfg.redact(f"Push returned HTTP {status} -- {hint}"))
