"""Media pipeline data models."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaType(str, Enum):
    IMAGE = "image"
    GIF = "gif"
    VIDEO = "video"
    UNSUPPORTED = "unsupported"


class ScanStatus(str, Enum):
    PROCESSED = "processed"
    CACHED = "cached"
    WOULD_PROCESS = "would-process"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass(frozen=True)
class SourceMedia:
    path: Path
    media_type: MediaType


@dataclass(frozen=True)
class ProcessedFrame:
    path: str
    duration_seconds: float


@dataclass(frozen=True)
class ScanResult:
    path: Path
    media_type: MediaType
    status: ScanStatus
    message: str
    output_dir: Path | None = None
    manifest_path: Path | None = None


@dataclass(frozen=True)
class ScanReport:
    items: tuple[ScanResult, ...]

    @property
    def counts(self) -> dict[ScanStatus, int]:
        return dict(Counter(item.status for item in self.items))

    @property
    def has_errors(self) -> bool:
        return any(item.status is ScanStatus.ERROR for item in self.items)
