from pathlib import Path

import pytest

from ledpi.config import ConfigError, load_config


def test_default_config_values():
    config = load_config()

    assert config.panel.width == 64
    assert config.panel.height == 64
    assert config.panel.address_lines == 5
    assert config.panel.brightness == 0.25
    assert config.media.inbox == Path("media/inbox")
    assert config.media.processed == Path("media/processed")
    assert config.playback.image_duration_seconds == 8.0
    assert config.playback.order == "deterministic"
    assert config.processing.fit == "cover"
    assert config.runtime.dry_run is False


def test_example_config_loads():
    config = load_config("config.example.toml")

    assert config.panel.width == 64
    assert config.panel.height == 64
    assert config.panel.address_lines == 5
    assert config.media.inbox == Path("media/inbox")
    assert config.media.processed == Path("media/processed")


def test_loads_explicit_toml_config(tmp_path):
    config_path = tmp_path / "ledpi.toml"
    config_path.write_text(
        """
        [panel]
        width = 32
        height = 64
        address_lines = 4
        brightness = 0.5

        [media]
        inbox = "uploads"
        processed = "cache"

        [playback]
        image_duration_seconds = 3.5
        order = "shuffle"

        [processing]
        fit = "contain"

        [runtime]
        dry_run = true
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.panel.width == 32
    assert config.panel.height == 64
    assert config.panel.address_lines == 4
    assert config.panel.brightness == 0.5
    assert config.media.inbox == tmp_path / "uploads"
    assert config.media.processed == tmp_path / "cache"
    assert config.playback.image_duration_seconds == 3.5
    assert config.playback.order == "shuffle"
    assert config.processing.fit == "contain"
    assert config.runtime.dry_run is True


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ("[panel]\nwidth = 0\n", "panel.width"),
        ("[panel]\nheight = -1\n", "panel.height"),
        ("[panel]\naddress_lines = 0\n", "panel.address_lines"),
        ("[panel]\nbrightness = 1.5\n", "panel.brightness"),
        ("[playback]\nimage_duration_seconds = 0\n", "playback.image_duration_seconds"),
        ('[playback]\norder = "randomish"\n', "playback.order"),
        ('[processing]\nfit = "stretch"\n', "processing.fit"),
        ('[runtime]\ndry_run = "yes"\n', "runtime.dry_run"),
    ],
)
def test_rejects_invalid_config_values(tmp_path, toml, message):
    config_path = tmp_path / "ledpi.toml"
    config_path.write_text(toml, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_config(config_path)
