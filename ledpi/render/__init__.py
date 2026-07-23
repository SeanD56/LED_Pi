"""Renderer abstractions and hardware adapters for LED matrix output."""

from ledpi.render.base import Renderer, RendererError
from ledpi.render.fake import FakeRenderer
from ledpi.render.frame import Frame
from ledpi.render.patterns import generate_test_pattern_frame

__all__ = [
    "FakeRenderer",
    "Frame",
    "generate_test_pattern_frame",
    "Renderer",
    "RendererError",
]
