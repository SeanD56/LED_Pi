from ledpi import __version__
from ledpi.service.cli import COMMANDS, main


def test_cli_help_exits_successfully(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "Raspberry Pi 5 LED matrix appliance." in captured.out
    for command in COMMANDS:
        assert command in captured.out


def test_cli_version_exits_successfully(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_scan_dry_run_exits_successfully_with_empty_inbox(tmp_path, capsys):
    config_path = tmp_path / "ledpi.toml"
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    config_path.write_text(
        """
        [media]
        inbox = "inbox"
        processed = "processed"
        """,
        encoding="utf-8",
    )

    exit_code = main(["scan", "--config", str(config_path), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No media found." in captured.out


def test_scan_invalid_config_returns_error(tmp_path, capsys):
    config_path = tmp_path / "ledpi.toml"
    config_path.write_text("[panel]\nwidth = 0\n", encoding="utf-8")

    exit_code = main(["scan", "--config", str(config_path), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "panel.width" in captured.err


def test_run_dry_run_once_uses_fallback_with_empty_playlist(tmp_path, capsys):
    config_path = tmp_path / "ledpi.toml"
    (tmp_path / "processed").mkdir()
    config_path.write_text(
        """
        [panel]
        width = 2
        height = 2

        [media]
        inbox = "inbox"
        processed = "processed"
        """,
        encoding="utf-8",
    )

    exit_code = main(["run", "--config", str(config_path), "--dry-run", "--once"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "frames=1" in captured.out
    assert "fallback=true" in captured.out


def test_placeholder_commands_are_explicit(capsys):
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not implemented yet" in captured.out
