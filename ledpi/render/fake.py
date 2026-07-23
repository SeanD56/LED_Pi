"""In-memory renderer for tests and dry-run development."""

from __future__ import annotations

from dataclasses import dataclass, field

from ledpi.render.base import RendererError
from ledpi.render.frame import Frame


@dataclass
class FakeRenderer:
    """Renderer that records frames without touching hardware."""

    started: bool = False
    stopped: bool = False
    shown_frames: list[Frame] = field(default_factory=list)

    def start(self) -> None:
        self.started = True
        self.stopped = False

    def show_frame(self, frame: Frame) -> None:
        if not self.started or self.stopped:
            raise RendererError("Renderer must be started before showing frames")
        self.shown_frames.append(frame)

    def stop(self) -> None:
        self.stopped = True
