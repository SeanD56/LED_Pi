"""Load processed media manifests into playlists."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
import json

from ledpi.config import AppConfig
from ledpi.media.pipeline import MANIFEST_NAME
from ledpi.playback.models import Playlist, PlaylistFrame, PlaylistItem


class ShuffleSource(Protocol):
    def shuffle(self, items: list[PlaylistItem]) -> None:
        """Shuffle a mutable list of playlist items in place."""


class PlaybackError(RuntimeError):
    """Raised when playback cannot proceed."""


def load_playlist(
    config: AppConfig,
    *,
    random_source: ShuffleSource | None = None,
) -> Playlist:
    """Load valid processed media manifests from the configured cache."""

    manifests = _manifest_paths(config.media.processed)
    items = [
        item
        for manifest_path in manifests
        if (item := _load_item(manifest_path, config)) is not None
    ]
    items.sort(key=lambda item: (item.source_name.lower(), str(item.manifest_path)))

    if config.playback.order == "shuffle":
        if random_source is None:
            import random

            random_source = random
        random_source.shuffle(items)

    return Playlist(items=tuple(items))


def _manifest_paths(processed_dir: Path) -> tuple[Path, ...]:
    if not processed_dir.exists():
        return ()
    return tuple(sorted(processed_dir.glob(f"*/{MANIFEST_NAME}")))


def _load_item(manifest_path: Path, config: AppConfig) -> PlaylistItem | None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    dimensions = manifest.get("dimensions")
    if not isinstance(dimensions, dict):
        return None
    width = dimensions.get("width")
    height = dimensions.get("height")
    if width != config.panel.width or height != config.panel.height:
        return None

    source = manifest.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("name"), str):
        return None

    frames = _load_frame_refs(manifest_path.parent, manifest.get("frames"))
    if not frames:
        return None

    media_type = manifest.get("media_type")
    if not isinstance(media_type, str):
        return None

    return PlaylistItem(
        manifest_path=manifest_path,
        source_name=source["name"],
        media_type=media_type,
        width=width,
        height=height,
        frames=frames,
    )


def _load_frame_refs(
    base_dir: Path,
    raw_frames: Any,
) -> tuple[PlaylistFrame, ...]:
    if not isinstance(raw_frames, list):
        return ()

    frames: list[PlaylistFrame] = []
    for raw_frame in raw_frames:
        if not isinstance(raw_frame, dict):
            return ()

        raw_path = raw_frame.get("path")
        raw_duration = raw_frame.get("duration_seconds")
        if not isinstance(raw_path, str):
            return ()
        if not isinstance(raw_duration, int | float) or raw_duration <= 0:
            return ()

        frame_path = Path(raw_path)
        if frame_path.is_absolute() or ".." in frame_path.parts:
            return ()

        resolved_path = base_dir / frame_path
        if not resolved_path.exists():
            return ()

        frames.append(
            PlaylistFrame(
                path=resolved_path,
                duration_seconds=float(raw_duration),
            ),
        )

    return tuple(frames)
