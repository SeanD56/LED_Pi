"""Renderer contracts."""

from __future__ import annotations

from typing import Protocol

from ledpi.render.frame import Frame


class RendererError(RuntimeError):
    """Raised when a renderer cannot complete an operation."""


class Renderer(Protocol):
    """Minimal renderer lifecycle used by playback."""

    def start(self) -> None:
        """Initialize renderer resources."""

    def show_frame(self, frame: Frame) -> None:
        """Display one frame."""

    def stop(self) -> None:
        """Release renderer resources."""
