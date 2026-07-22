import base64
import json
import stat

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


def test_saved_config_is_never_looser_than_0600(tmp_path):
    # Finding 1 (TOCTOU): under a permissive umask, the file must never be
    # observable at a mode looser than 0600. We can't observe the open
    # window directly in a unit test, so we pin the exact final mode --
    # see the fix-round report for how the window itself is closed.
    p = tmp_path / "config.toml"
    device.save_config(cfg(), path=p)
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_saved_config_tightens_a_preexisting_looser_mode(tmp_path):
    # os.open()'s mode argument is only applied when the file is newly
    # created -- if config.toml already exists (e.g. from an older,
    # looser save) that mode must still be corrected.
    p = tmp_path / "config.toml"
    p.write_text("stale")
    p.chmod(0o644)
    device.save_config(cfg(), path=p)
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_a_token_with_quotes_survives_the_roundtrip(tmp_path):
    p = tmp_path / "config.toml"
    device.save_config(device.Config("d", 'we"ird\\token'), path=p)
    assert device.load_config(env={}, path=p).api_token == 'we"ird\\token'


def test_a_token_with_a_non_bmp_character_survives_the_roundtrip(tmp_path):
    # Finding 2: json.dumps(..., ensure_ascii=True) emits non-BMP
    # characters as UTF-16 surrogate pairs, which are not valid TOML
    # \uXXXX escapes -- tomllib then refuses to load the file we just
    # wrote.
    p = tmp_path / "config.toml"
    token = "tok-\U0001F600-en"
    device.save_config(device.Config("d", token), path=p)
    assert device.load_config(env={}, path=p).api_token == token


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


# --- Finding 3: every PushError names the fix, not just the violation ---

def test_empty_payload_error_names_a_fix():
    with pytest.raises(device.PushError) as e:
        device.push(b"", cfg())
    msg = str(e.value).lower()
    assert "empty" in msg
    assert "before calling push" in msg or "render a frame" in msg


def test_transport_error_names_a_fix():
    def boom(url, body, headers):
        raise RuntimeError("connect failed for token secret-token-value")

    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=boom)
    msg = str(e.value).lower()
    assert "connect failed" in msg
    assert "check your network connection" in msg or "retry" in msg


def test_generic_status_error_names_a_fix():
    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=Poster(500))
    msg = str(e.value).lower()
    assert "500" in str(e.value)
    assert "retry" in msg or "support" in msg


def test_a_403_names_a_concrete_fix():
    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=Poster(403))
    msg = str(e.value).lower()
    assert "403" in str(e.value)
    assert "llmbyt init" in msg or "new token" in msg or "regenerate" in msg


# --- Finding 4: no unredacted token reachable via __context__/__cause__ ---

def test_transport_error_leaves_no_unredacted_context():
    def boom(url, body, headers):
        raise RuntimeError("connect failed for token secret-token-value")

    with pytest.raises(device.PushError) as e:
        device.push(b"w", cfg(), poster=boom)
    err = e.value
    assert err.__cause__ is None
    assert err.__context__ is None


# --- a corrupt config must not leak the token it contains --------------

MALFORMED = ('device_id = "dev123"\n'
             'api_token = "secret-token-value\n')      # unterminated string


def test_a_malformed_config_is_a_clean_error_naming_the_path_and_the_fix(
        tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(MALFORMED)
    with pytest.raises(device.ConfigError) as e:
        device.load_config(env={}, path=p)
    msg = str(e.value)
    assert str(p) in msg
    assert "llmbyt init" in msg


def test_a_malformed_config_leaves_no_token_bearing_exception_reachable(
        tmp_path):
    """tomllib.TOMLDecodeError carries the entire document it failed on
    in its .doc attribute -- api_token and all. str(e) never prints it,
    but the reachability bar set by the push() finding is that no
    attribute walk can get to it either, so the ConfigError is built and
    raised outside the except block and nothing links back."""
    p = tmp_path / "config.toml"
    p.write_text(MALFORMED)
    with pytest.raises(device.ConfigError) as e:
        device.load_config(env={}, path=p)
    err = e.value
    assert err.__cause__ is None
    assert err.__context__ is None
    assert "secret-token-value" not in str(err)
    assert not any("secret-token-value" in str(v)
                   for v in vars(err).values())


def test_a_malformed_config_does_not_escape_the_cli_as_a_traceback(
        tmp_path, monkeypatch, capsys):
    from llmbyt import cli
    p = tmp_path / "config.toml"
    p.write_text(MALFORMED)
    monkeypatch.setattr(device, "CONFIG_PATH", p)
    monkeypatch.delenv("LLMBYT_DEVICE_ID", raising=False)
    monkeypatch.delenv("LLMBYT_API_TOKEN", raising=False)
    assert cli.main(["text", "hi", "-o", str(tmp_path / "o")]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "secret-token-value" not in err
    assert "llmbyt init" in err


def test_an_unreadable_config_is_a_clean_error_too(tmp_path):
    import os
    if os.geteuid() == 0:
        pytest.skip("root ignores the permission bits this test relies on")
    p = tmp_path / "config.toml"
    p.write_text('device_id = "d"\napi_token = "t"\n')
    p.chmod(0o000)
    try:
        with pytest.raises(device.ConfigError) as e:
            device.load_config(env={}, path=p)
    finally:
        p.chmod(0o600)
    msg = str(e.value)
    assert str(p) in msg and "llmbyt init" in msg
    assert e.value.__context__ is None
