"""Playback loop that sends playlist frames to a renderer."""

from __future__ import annotations

from collections.abc import Callable
import time

from PIL import Image

from ledpi.config import AppConfig
from ledpi.playback.models import PlaybackSummary, PlaylistFrame
from ledpi.playback.playlist import ShuffleSource, load_playlist
from ledpi.render import Frame, Renderer, generate_test_pattern_frame


SleepFn = Callable[[float], None]


def play_playlist(
    config: AppConfig,
    renderer: Renderer,
    *,
    once: bool = False,
    sleep: SleepFn = time.sleep,
    random_source: ShuffleSource | None = None,
) -> PlaybackSummary:
    """Play processed media through a renderer."""

    playlist = load_playlist(config, random_source=random_source)
    frames_shown = 0
    items_played = 0
    used_fallback = playlist.is_empty

    renderer.start()
    try:
        if playlist.is_empty:
            while True:
                fallback = generate_test_pattern_frame(
                    width=config.panel.width,
                    height=config.panel.height,
                    duration_seconds=1.0,
                )
                renderer.show_frame(fallback)
                sleep(fallback.duration_seconds)
                frames_shown += 1
                if once:
                    break
            return PlaybackSummary(
                items_played=0,
                frames_shown=frames_shown,
                used_fallback=True,
            )

        while True:
            for item in playlist.items:
                for frame_ref in item.frames:
                    frame = load_frame(frame_ref)
                    renderer.show_frame(frame)
                    sleep(frame.duration_seconds)
                    frames_shown += 1
                items_played += 1

            if once:
                break
    finally:
        renderer.stop()

    return PlaybackSummary(
        items_played=items_played,
        frames_shown=frames_shown,
        used_fallback=used_fallback,
    )


def load_frame(frame_ref: PlaylistFrame) -> Frame:
    """Load a processed PNG frame into the renderer frame format."""

    with Image.open(frame_ref.path) as image:
        image = image.convert("RGB")
        pixels = image.tobytes()
        width, height = image.size

    return Frame(
        width=width,
        height=height,
        pixels=pixels,
        duration_seconds=frame_ref.duration_seconds,
    )
