import base64
import json

import pytest

from llmbyt import device


def cfg(token="secret-token-value"):
    return device.Config(device_id="dev123", api_token=token)


class Poster:
    """Records the call and returns a canned status."""

    def __init__(self, status=200):
        self.status = status
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        return self.status


# --- config ----------------------------------------------------------

def test_env_supplies_the_whole_config():
    c = device.load_config(env={"LLMBYT_DEVICE_ID": "d",
                                "LLMBYT_API_TOKEN": "t"})
    assert (c.device_id, c.api_token) == ("d", "t")


def test_config_file_is_read_when_env_is_absent(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('device_id = "from-file"\napi_token = "tok"\n')
    c = device.load_config(env={}, path=p)
    assert c.device_id == "from-file"


def test_env_overrides_the_file(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('device_id = "from-file"\napi_token = "tok"\n')
    c = device.load_config(env={"LLMBYT_DEVICE_ID": "from-env"}, path=p)
    assert c.device_id == "from-env"
    assert c.api_token == "tok"


def test_missing_config_tells_you_how_to_fix_it(tmp_path):
    with pytest.raises(device.ConfigError) as e:
        device.load_config(env={}, path=tmp_path / "nope.toml")
    msg = str(e.value)
    assert "llmbyt init" in msg
    assert "LLMBYT_API_TOKEN" in msg


def test_partial_config_names_only_the_missing_key(tmp_path):
    with pytest.raises(device.ConfigError) as e:
        device.load_config(env={"LLMBYT_DEVICE_ID": "d"},
                           path=tmp_path / "nope.toml")
    assert "api_token" in str(e.value)
    assert "device_id" not in str(e.value)


def test_save_then_load_roundtrips(tmp_path):
    p = tmp_path / "sub" / "config.toml"
    device.save_config(cfg(), path=p)
    assert device.load_config(env={}, path=p) == cfg()


def test_saved_config_is_not_world_readable(tmp_path):
    p = device.save_config(cfg(), path=tmp_path / "config.toml")
    assert p.stat().st_mode & 0o077 == 0


def test_a_token_with_quotes_survives_the_roundtrip(tmp_path):
    p = tmp_path / "config.toml"
    device.save_config(device.Config("d", 'we"ird\\token'), path=p)
    assert device.load_config(env={}, path=p).api_token == 'we"ird\\token'


# --- redaction -------------------------------------------------------

def test_redact_replaces_the_token():
    c = cfg()
    out = c.redact("Bearer secret-token-value failed")
    assert "secret-token-value" not in out
    assert "REDACTED" in out


def test_repr_never_contains_the_token():
    assert "secret-token-value" not in repr(cfg())


# --- push ------------------------------------------------------------

def test_push_targets_the_configured_device():
    p = Poster()
    device.push(b"webp", cfg(), poster=p)
    assert p.calls[0][0] == device.PUSH_URL % "dev123"


def test_push_sends_base64_webp_with_the_fixed_installation_id():
    p = Poster()
    device.push(b"webp-bytes", cfg(), poster=p)
    body = json.loads(p.calls[0][1])
    assert base64.b64decode(body["image"]) == b"webp-bytes"
    assert body["installationID"] == device.INSTALLATION_ID


def test_push_is_always_an_ephemeral_interrupt():
    p = Poster()
    device.push(b"w", cfg(), poster=p)
    assert json.loads(p.calls[0][1])["background"] is False


def test_push_sends_a_bearer_token():
    p = Poster()
    device.push(b"w", cfg(), poster=p)
    assert p.calls[0][2]["Authorization"] == "Bearer secret-token-value"


def test_a_401_explains_the_token_is_the_problem():
    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=Poster(401))
    assert "401" in str(e.value) and "token" in str(e.value).lower()


def test_a_404_explains_the_device_id_is_the_problem():
    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=Poster(404))
    assert "404" in str(e.value) and "device" in str(e.value).lower()


def test_a_push_error_never_leaks_the_token():
    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=Poster(500))
    assert "secret-token-value" not in str(e.value)


def test_a_transport_exception_is_reraised_redacted():
    def boom(url, body, headers):
        raise RuntimeError("connect failed for token secret-token-value")

    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=boom)
    assert "secret-token-value" not in str(e.value)
    assert "connect failed" in str(e.value)


def test_empty_payload_is_rejected_before_any_network_call():
    p = Poster()
    with pytest.raises(device.PushError, match="empty"):
        device.push(b"", cfg(), poster=p)
    assert p.calls == []
