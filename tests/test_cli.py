import pytest

from llmbyt import cli


def display(tmp_path, body="""
from llmbyt import scene as sc
def render():
    return sc.Text("hi")
"""):
    p = tmp_path / "d.py"
    p.write_text(body)
    return p


class FakePush:
    def __init__(self):
        self.calls = []

    def __call__(self, webp, cfg, *, poster=None):
        self.calls.append(webp)


@pytest.fixture
def no_network(monkeypatch):
    fake = FakePush()
    monkeypatch.setattr(cli.device, "push", fake)
    monkeypatch.setattr(cli.device, "load_config",
                        lambda **kw: cli.device.Config("d", "t"))
    return fake


def test_no_arguments_prints_help_and_fails(capsys):
    assert cli.main([]) == 2
    assert "preview" in capsys.readouterr().out


def test_help_states_the_display_size_and_the_render_contract(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert "64x32" in out
    assert "render()" in out
    assert "14500" in out or "14.5" in out


def test_preview_writes_a_file_and_reports_the_path(tmp_path, capsys):
    out = tmp_path / "o.png"
    assert cli.main(["preview", str(display(tmp_path)), "-o", str(out)]) == 0
    assert out.exists()
    assert str(out) in capsys.readouterr().out


def test_preview_never_pushes(tmp_path, no_network):
    cli.main(["preview", str(display(tmp_path)),
              "-o", str(tmp_path / "o.png")])
    assert no_network.calls == []


def test_show_previews_and_then_pushes(tmp_path, no_network, capsys):
    out = tmp_path / "o.png"
    assert cli.main(["show", str(display(tmp_path)), "-o", str(out)]) == 0
    assert out.exists()
    assert len(no_network.calls) == 1
    assert no_network.calls[0][:4] == b"RIFF"


def test_text_shows_a_one_shot_message(tmp_path, no_network):
    assert cli.main(["text", "hello there",
                     "-o", str(tmp_path / "o")]) == 0
    assert len(no_network.calls) == 1


def test_text_that_overflows_scrolls_rather_than_erroring(tmp_path, no_network):
    long = "this message is far too long to fit on a tiny sixty four pixel display"
    assert cli.main(["text", long, "-o", str(tmp_path / "o")]) == 0


def test_image_fits_a_real_picture(tmp_path, no_network):
    from PIL import Image
    src = tmp_path / "src.png"
    Image.new("RGB", (400, 300), (200, 0, 0)).save(src)
    assert cli.main(["image", str(src), "-o", str(tmp_path / "o")]) == 0
    assert len(no_network.calls) == 1


def test_a_display_error_prints_the_message_without_a_traceback(
        tmp_path, capsys):
    bad = display(tmp_path, "def render():\n    return 42\n")
    assert cli.main(["preview", str(bad), "-o", str(tmp_path / "o")]) == 1
    err = capsys.readouterr().err
    assert "int" in err
    assert "Traceback" not in err


def test_an_over_budget_animation_reports_the_clamp(tmp_path, no_network,
                                                    capsys):
    d = display(tmp_path, """
from PIL import Image
def render():
    return [Image.new("RGB", (64, 32)) for _ in range(500)]
""")
    cli.main(["show", str(d), "-o", str(tmp_path / "o")])
    combined = capsys.readouterr()
    assert "145" in (combined.out + combined.err)


def test_frame_ms_alone_over_the_ceiling_reports_that_distinct_failure(
        tmp_path, no_network, capsys):
    """Budget.message() has two distinct failure modes: frames dropped,
    and duration over the ceiling with nothing dropped. A single frame
    at a large enough frame_ms trips the second without ever dropping a
    frame; the CLI must surface that message too, not just the
    dropped-frames one."""
    assert cli.main(["show", str(display(tmp_path)),
                     "-o", str(tmp_path / "o"),
                     "--frame-ms", "20000"]) == 0
    err = capsys.readouterr().err
    assert "frame_ms alone" in err


def test_missing_config_on_show_is_a_clean_error(tmp_path, monkeypatch,
                                                 capsys):
    def missing(**kw):
        raise cli.device.ConfigError("Missing api_token. Run `llmbyt init`.")

    monkeypatch.setattr(cli.device, "load_config", missing)
    assert cli.main(["show", str(display(tmp_path)),
                     "-o", str(tmp_path / "o")]) == 1
    assert "llmbyt init" in capsys.readouterr().err


def test_init_writes_the_config_from_prompts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "dev-abc")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "token-xyz")
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr(cli.device, "CONFIG_PATH", cfg_path)
    assert cli.main(["init"]) == 0
    assert 'dev-abc' in cfg_path.read_text()
    assert 'token-xyz' in cfg_path.read_text()


def test_init_does_not_echo_the_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "dev-abc")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "token-xyz")
    monkeypatch.setattr(cli.device, "CONFIG_PATH", tmp_path / "config.toml")
    cli.main(["init"])
    assert "token-xyz" not in capsys.readouterr().out


def test_init_reads_the_token_via_getpass_not_input(tmp_path, monkeypatch):
    """The 'init' prompt claims the token is hidden / not echoed back --
    that claim is only true if the token genuinely goes through
    getpass.getpass() rather than input(). input() echoes on a real
    terminal, so this pins the fix rather than just re-checking
    behaviour that a monkeypatched input() can't actually exercise."""
    input_calls = []
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (input_calls.append(prompt), "dev-abc")[1])
    getpass_calls = []
    monkeypatch.setattr(
        cli.getpass, "getpass",
        lambda prompt: (getpass_calls.append(prompt), "token-xyz")[1])
    monkeypatch.setattr(cli.device, "CONFIG_PATH", tmp_path / "config.toml")

    assert cli.main(["init"]) == 0
    assert len(input_calls) == 1     # only the device ID goes through input()
    assert len(getpass_calls) == 1   # the token goes through getpass, not input()


def test_init_requires_both_values_and_writes_nothing(tmp_path, monkeypatch,
                                                       capsys):
    monkeypatch.setattr("builtins.input", lambda _: "")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "")
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr(cli.device, "CONFIG_PATH", cfg_path)
    assert cli.main(["init"]) == 1
    assert not cfg_path.exists()
    err = capsys.readouterr().err
    assert "device ID" in err
    assert "API token" in err


def test_scale_option_changes_the_preview_size(tmp_path):
    from PIL import Image
    out = tmp_path / "o.png"
    cli.main(["preview", str(display(tmp_path)), "-o", str(out), "--scale", "4"])
    assert Image.open(out).size == (64 * 4 + 2, 32 * 4 + 2)
