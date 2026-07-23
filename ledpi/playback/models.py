"""Playback data models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlaylistFrame:
    path: Path
    duration_seconds: float


@dataclass(frozen=True)
class PlaylistItem:
    manifest_path: Path
    source_name: str
    media_type: str
    width: int
    height: int
    frames: tuple[PlaylistFrame, ...]


@dataclass(frozen=True)
class Playlist:
    items: tuple[PlaylistItem, ...]

    @property
    def is_empty(self) -> bool:
        return not self.items


@dataclass(frozen=True)
class PlaybackSummary:
    items_played: int
    frames_shown: int
    used_fallback: bool
