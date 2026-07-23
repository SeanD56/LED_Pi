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
from ledpi.media import ScanStatus, process_inbox


def make_config(tmp_path: Path, *, fit: str = "cover") -> AppConfig:
    return AppConfig(
        panel=PanelConfig(width=4, height=4, address_lines=5, brightness=0.25),
        media=MediaConfig(
            inbox=tmp_path / "inbox",
            processed=tmp_path / "processed",
        ),
        playback=PlaybackConfig(image_duration_seconds=2.5, order="deterministic"),
        processing=ProcessingConfig(fit=fit),
    )


def save_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_scan_dry_run_reports_supported_and_unsupported_files(tmp_path):
    config = make_config(tmp_path)
    config.media.inbox.mkdir()
    save_image(config.media.inbox / "photo.png", (8, 8), (255, 0, 0))
    (config.media.inbox / "notes.txt").write_text("ignore me", encoding="utf-8")

    report = process_inbox(config, dry_run=True)

    assert report.counts == {
        ScanStatus.WOULD_PROCESS: 1,
        ScanStatus.SKIPPED: 1,
    }
    assert report.items[0].path.name == "notes.txt"
    assert report.items[0].status is ScanStatus.SKIPPED
    assert report.items[1].path.name == "photo.png"
    assert report.items[1].status is ScanStatus.WOULD_PROCESS
    assert not config.media.processed.exists()


def test_processes_static_image_and_writes_manifest(tmp_path):
    config = make_config(tmp_path)
    save_image(config.media.inbox / "photo.png", (8, 8), (255, 0, 0))

    report = process_inbox(config)

    assert report.counts == {ScanStatus.PROCESSED: 1}
    result = report.items[0]
    assert result.output_dir is not None
    assert result.manifest_path is not None
    assert result.manifest_path.exists()

    frame_path = result.output_dir / "frame_000000.png"
    assert frame_path.exists()
    with Image.open(frame_path) as image:
        assert image.size == (4, 4)
        assert image.mode == "RGB"

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert manifest["media_type"] == "image"
    assert manifest["source"]["name"] == "photo.png"
    assert manifest["dimensions"] == {"width": 4, "height": 4}
    assert manifest["frames"] == [
        {"path": "frame_000000.png", "duration_seconds": 2.5},
    ]


def test_reuses_cached_processed_item(tmp_path):
    config = make_config(tmp_path)
    save_image(config.media.inbox / "photo.png", (8, 8), (255, 0, 0))

    first = process_inbox(config)
    second = process_inbox(config)

    assert first.counts == {ScanStatus.PROCESSED: 1}
    assert second.counts == {ScanStatus.CACHED: 1}
    assert first.items[0].output_dir == second.items[0].output_dir


def test_rebuilds_corrupt_manifest(tmp_path):
    config = make_config(tmp_path)
    save_image(config.media.inbox / "photo.png", (8, 8), (255, 0, 0))
    first = process_inbox(config)
    manifest_path = first.items[0].manifest_path
    assert manifest_path is not None
    manifest_path.write_text("{not json", encoding="utf-8")

    second = process_inbox(config)

    assert second.counts == {ScanStatus.PROCESSED: 1}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source"]["name"] == "photo.png"


def test_contain_fit_preserves_aspect_ratio_with_letterbox(tmp_path):
    config = make_config(tmp_path, fit="contain")
    save_image(config.media.inbox / "wide.png", (8, 4), (255, 0, 0))

    report = process_inbox(config)

    frame_path = report.items[0].output_dir / "frame_000000.png"
    with Image.open(frame_path) as image:
        assert image.getpixel((0, 0)) == (0, 0, 0)
        assert image.getpixel((2, 2)) == (255, 0, 0)


def test_processes_gif_frames_with_timing(tmp_path):
    config = make_config(tmp_path)
    config.media.inbox.mkdir(parents=True)
    frames = [
        Image.new("RGB", (4, 4), (255, 0, 0)),
        Image.new("RGB", (4, 4), (0, 255, 0)),
    ]
    frames[0].save(
        config.media.inbox / "animation.gif",
        save_all=True,
        append_images=[frames[1]],
        duration=[100, 200],
        loop=0,
    )

    report = process_inbox(config)

    assert report.counts == {ScanStatus.PROCESSED: 1}
    manifest_path = report.items[0].manifest_path
    assert manifest_path is not None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["media_type"] == "gif"
    assert manifest["frames"] == [
        {"path": "frame_000000.png", "duration_seconds": 0.1},
        {"path": "frame_000001.png", "duration_seconds": 0.2},
    ]


def test_video_is_skipped_when_ffmpeg_is_unavailable(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    config.media.inbox.mkdir()
    (config.media.inbox / "clip.mp4").write_bytes(b"not a real video")
    monkeypatch.setattr("ledpi.media.pipeline.shutil.which", lambda name: None)

    report = process_inbox(config)

    assert report.counts == {ScanStatus.SKIPPED: 1}
    assert report.items[0].path.name == "clip.mp4"
    assert "ffmpeg" in report.items[0].message
