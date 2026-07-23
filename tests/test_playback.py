import json
from pathlib import Path

from PIL import Image

from ledpi.config import (
    AppConfig,
    MediaConfig,
    PanelConfig,
    PlaybackConfig,
    ProcessingConfig,
)
from ledpi.playback import load_playlist, play_playlist
from ledpi.render import FakeRenderer


def make_config(
    tmp_path: Path,
    *,
    order: str = "deterministic",
) -> AppConfig:
    return AppConfig(
        panel=PanelConfig(width=2, height=2, address_lines=5, brightness=0.25),
        media=MediaConfig(
            inbox=tmp_path / "inbox",
            processed=tmp_path / "processed",
        ),
        playback=PlaybackConfig(image_duration_seconds=1.0, order=order),
        processing=ProcessingConfig(fit="cover"),
    )


def write_processed_item(
    processed_dir: Path,
    item_dir_name: str,
    source_name: str,
    frame_specs: list[tuple[str, tuple[int, int, int], float]],
) -> Path:
    item_dir = processed_dir / item_dir_name
    item_dir.mkdir(parents=True)
    manifest_frames = []

    for frame_name, color, duration_seconds in frame_specs:
        Image.new("RGB", (2, 2), color).save(item_dir / frame_name)
        manifest_frames.append(
            {
                "path": frame_name,
                "duration_seconds": duration_seconds,
            },
        )

    manifest = {
        "version": 1,
        "source": {
            "path": f"media/inbox/{source_name}",
            "name": source_name,
            "sha256": item_dir_name,
        },
        "media_type": "image",
        "processing": {
            "width": 2,
            "height": 2,
            "fit": "cover",
            "image_duration_seconds": 1.0,
            "video_frame_rate": 10,
            "pipeline_version": 1,
        },
        "dimensions": {"width": 2, "height": 2},
        "duration_seconds": sum(frame[2] for frame in frame_specs),
        "frame_count": len(frame_specs),
        "frames": manifest_frames,
    }
    manifest_path = item_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


class ReversingRandom:
    def shuffle(self, items):
        items.reverse()


def test_load_playlist_returns_empty_when_processed_dir_is_missing(tmp_path):
    config = make_config(tmp_path)

    playlist = load_playlist(config)

    assert playlist.items == ()


def test_load_playlist_orders_items_deterministically_by_source_name(tmp_path):
    config = make_config(tmp_path)
    write_processed_item(
        config.media.processed,
        "bbbb",
        "zebra.png",
        [("frame_000000.png", (0, 0, 255), 1.0)],
    )
    write_processed_item(
        config.media.processed,
        "aaaa",
        "apple.png",
        [("frame_000000.png", (255, 0, 0), 1.0)],
    )

    playlist = load_playlist(config)

    assert [item.source_name for item in playlist.items] == ["apple.png", "zebra.png"]


def test_load_playlist_can_shuffle_with_injected_random_source(tmp_path):
    config = make_config(tmp_path, order="shuffle")
    write_processed_item(
        config.media.processed,
        "aaaa",
        "apple.png",
        [("frame_000000.png", (255, 0, 0), 1.0)],
    )
    write_processed_item(
        config.media.processed,
        "bbbb",
        "banana.png",
        [("frame_000000.png", (0, 255, 0), 1.0)],
    )
    write_processed_item(
        config.media.processed,
        "cccc",
        "cherry.png",
        [("frame_000000.png", (0, 0, 255), 1.0)],
    )

    playlist = load_playlist(config, random_source=ReversingRandom())

    assert [item.source_name for item in playlist.items] == [
        "cherry.png",
        "banana.png",
        "apple.png",
    ]


def test_playback_uses_fallback_when_playlist_is_empty(tmp_path):
    config = make_config(tmp_path)
    renderer = FakeRenderer()
    slept: list[float] = []

    summary = play_playlist(config, renderer, once=True, sleep=slept.append)

    assert summary.items_played == 0
    assert summary.frames_shown == 1
    assert summary.used_fallback is True
    assert renderer.started is True
    assert renderer.stopped is True
    assert len(renderer.shown_frames) == 1
    assert renderer.shown_frames[0].width == 2
    assert renderer.shown_frames[0].height == 2
    assert slept == [1.0]


def test_playback_shows_processed_frames_once(tmp_path):
    config = make_config(tmp_path)
    write_processed_item(
        config.media.processed,
        "aaaa",
        "animation.gif",
        [
            ("frame_000000.png", (255, 0, 0), 0.1),
            ("frame_000001.png", (0, 255, 0), 0.2),
        ],
    )
    renderer = FakeRenderer()
    slept: list[float] = []

    summary = play_playlist(config, renderer, once=True, sleep=slept.append)

    assert summary.items_played == 1
    assert summary.frames_shown == 2
    assert summary.used_fallback is False
    assert len(renderer.shown_frames) == 2
    assert renderer.shown_frames[0].pixels == b"\xff\x00\x00" * 4
    assert renderer.shown_frames[1].pixels == b"\x00\xff\x00" * 4
    assert slept == [0.1, 0.2]
