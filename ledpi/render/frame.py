"""Frame primitives shared by playback and renderers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    """One RGB frame destined for a matrix renderer."""

    width: int
    height: int
    pixels: bytes
    duration_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.width, int) or isinstance(self.width, bool):
            raise ValueError("width must be an integer")
        if not isinstance(self.height, int) or isinstance(self.height, bool):
            raise ValueError("height must be an integer")
        if self.width <= 0:
            raise ValueError("width must be greater than 0")
        if self.height <= 0:
            raise ValueError("height must be greater than 0")
        if not isinstance(self.pixels, bytes):
            raise ValueError("pixels must be bytes")
        if not isinstance(self.duration_seconds, int | float) or isinstance(
            self.duration_seconds,
            bool,
        ):
            raise ValueError("duration_seconds must be a number")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")

        expected_size = self.width * self.height * 3
        if len(self.pixels) != expected_size:
            raise ValueError(
                f"pixels length must match frame size: expected {expected_size} RGB bytes",
            )

    @property
    def pixel_count(self) -> int:
        return self.width * self.height
