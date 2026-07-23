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


def test_placeholder_commands_are_explicit(capsys):
    exit_code = main(["scan"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not implemented yet" in captured.out
