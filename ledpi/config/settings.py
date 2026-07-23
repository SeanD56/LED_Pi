"""Typed application configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


PLAYBACK_ORDERS = {"deterministic", "shuffle"}
FIT_MODES = {"cover", "contain"}


class ConfigError(ValueError):
    """Raised when a configuration file is invalid."""


@dataclass(frozen=True)
class PanelConfig:
    width: int = 64
    height: int = 64
    address_lines: int = 5
    brightness: float = 0.25


@dataclass(frozen=True)
class MediaConfig:
    inbox: Path = Path("media/inbox")
    processed: Path = Path("media/processed")


@dataclass(frozen=True)
class PlaybackConfig:
    image_duration_seconds: float = 8.0
    order: str = "deterministic"


@dataclass(frozen=True)
class ProcessingConfig:
    fit: str = "cover"


@dataclass(frozen=True)
class RuntimeConfig:
    dry_run: bool = False


@dataclass(frozen=True)
class AppConfig:
    panel: PanelConfig = PanelConfig()
    media: MediaConfig = MediaConfig()
    playback: PlaybackConfig = PlaybackConfig()
    processing: ProcessingConfig = ProcessingConfig()
    runtime: RuntimeConfig = RuntimeConfig()


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load application config from TOML, or return defaults when no path is given."""

    defaults = AppConfig()
    if path is None:
        return defaults

    config_path = Path(path)
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {config_path}: {exc}") from exc

    if not isinstance(raw, Mapping):
        raise ConfigError("Config root must be a TOML table")

    base_dir = config_path.parent

    panel = _load_panel(_section(raw, "panel"), defaults.panel)
    media = _load_media(_section(raw, "media"), defaults.media, base_dir)
    playback = _load_playback(_section(raw, "playback"), defaults.playback)
    processing = _load_processing(_section(raw, "processing"), defaults.processing)
    runtime = _load_runtime(_section(raw, "runtime"), defaults.runtime)

    return AppConfig(
        panel=panel,
        media=media,
        playback=playback,
        processing=processing,
        runtime=runtime,
    )


def _load_panel(raw: Mapping[str, Any], defaults: PanelConfig) -> PanelConfig:
    width = _positive_int(raw.get("width", defaults.width), "panel.width")
    height = _positive_int(raw.get("height", defaults.height), "panel.height")
    address_lines = _positive_int(
        raw.get("address_lines", defaults.address_lines),
        "panel.address_lines",
    )
    brightness = _bounded_float(
        raw.get("brightness", defaults.brightness),
        "panel.brightness",
        minimum=0.0,
        maximum=1.0,
    )

    return PanelConfig(
        width=width,
        height=height,
        address_lines=address_lines,
        brightness=brightness,
    )


def _load_media(
    raw: Mapping[str, Any],
    defaults: MediaConfig,
    base_dir: Path,
) -> MediaConfig:
    return MediaConfig(
        inbox=_path(raw.get("inbox", defaults.inbox), "media.inbox", base_dir),
        processed=_path(
            raw.get("processed", defaults.processed),
            "media.processed",
            base_dir,
        ),
    )


def _load_playback(
    raw: Mapping[str, Any],
    defaults: PlaybackConfig,
) -> PlaybackConfig:
    return PlaybackConfig(
        image_duration_seconds=_positive_float(
            raw.get(
                "image_duration_seconds",
                defaults.image_duration_seconds,
            ),
            "playback.image_duration_seconds",
        ),
        order=_choice(
            raw.get("order", defaults.order),
            "playback.order",
            PLAYBACK_ORDERS,
        ),
    )


def _load_processing(
    raw: Mapping[str, Any],
    defaults: ProcessingConfig,
) -> ProcessingConfig:
    return ProcessingConfig(
        fit=_choice(raw.get("fit", defaults.fit), "processing.fit", FIT_MODES),
    )


def _load_runtime(raw: Mapping[str, Any], defaults: RuntimeConfig) -> RuntimeConfig:
    return RuntimeConfig(
        dry_run=_bool(raw.get("dry_run", defaults.dry_run), "runtime.dry_run"),
    )


def _section(raw: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be a TOML table")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{field_name} must be an integer")
    if value <= 0:
        raise ConfigError(f"{field_name} must be greater than 0")
    return value


def _positive_float(value: Any, field_name: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a number")
    value = float(value)
    if value <= 0.0:
        raise ConfigError(f"{field_name} must be greater than 0")
    return value


def _bounded_float(
    value: Any,
    field_name: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a number")
    value = float(value)
    if not minimum <= value <= maximum:
        raise ConfigError(f"{field_name} must be between {minimum} and {maximum}")
    return value


def _choice(value: Any, field_name: str, choices: set[str]) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string")
    if value not in choices:
        options = ", ".join(sorted(choices))
        raise ConfigError(f"{field_name} must be one of: {options}")
    return value


def _bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name} must be true or false")
    return value


def _path(value: Any, field_name: str, base_dir: Path) -> Path:
    if not isinstance(value, str | Path):
        raise ConfigError(f"{field_name} must be a path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path
