"""Local media scanning and preprocessing."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageOps, ImageSequence

from ledpi.config import AppConfig
from ledpi.media.models import (
    MediaType,
    ProcessedFrame,
    ScanReport,
    ScanResult,
    ScanStatus,
    SourceMedia,
)


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
GIF_EXTENSIONS = {".gif"}
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
MANIFEST_NAME = "manifest.json"
FRAME_NAME_TEMPLATE = "frame_{index:06d}.png"
MANIFEST_VERSION = 1
VIDEO_FRAME_RATE = 10


def process_inbox(config: AppConfig, *, dry_run: bool = False) -> ScanReport:
    """Scan the configured inbox and process supported media."""

    sources = discover_sources(config.media.inbox)
    results = [_process_source(source, config, dry_run=dry_run) for source in sources]
    return ScanReport(items=tuple(results))


def discover_sources(inbox: Path) -> tuple[SourceMedia, ...]:
    """Return non-hidden files in the inbox, tagged by media type."""

    if not inbox.exists():
        return ()

    paths = (
        path
        for path in inbox.rglob("*")
        if path.is_file() and not _has_hidden_part(path.relative_to(inbox))
    )
    return tuple(
        SourceMedia(path=path, media_type=media_type_for_path(path))
        for path in sorted(
            paths,
            key=lambda path: path.relative_to(inbox).as_posix().lower(),
        )
    )


def media_type_for_path(path: Path) -> MediaType:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return MediaType.IMAGE
    if suffix in GIF_EXTENSIONS:
        return MediaType.GIF
    if suffix in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    return MediaType.UNSUPPORTED


def fingerprint_source(source: SourceMedia, config: AppConfig) -> str:
    digest = hashlib.sha256()
    with source.path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    digest.update(
        json.dumps(_processing_profile(config), sort_keys=True).encode("utf-8"),
    )
    digest.update(source.media_type.value.encode("utf-8"))
    return digest.hexdigest()


def _process_source(
    source: SourceMedia,
    config: AppConfig,
    *,
    dry_run: bool,
) -> ScanResult:
    if source.media_type is MediaType.UNSUPPORTED:
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.SKIPPED,
            message=f"unsupported extension: {source.path.suffix or '<none>'}",
        )

    try:
        fingerprint = fingerprint_source(source, config)
    except OSError as exc:
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.ERROR,
            message=f"could not read source: {exc}",
        )

    output_dir = config.media.processed / fingerprint
    manifest_path = output_dir / MANIFEST_NAME

    if manifest_path.exists() and _manifest_is_valid(manifest_path, source, config):
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.CACHED,
            message="cached",
            output_dir=output_dir,
            manifest_path=manifest_path,
        )

    if dry_run:
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.WOULD_PROCESS,
            message=f"would process {source.media_type.value}",
            output_dir=output_dir,
            manifest_path=manifest_path,
        )

    if source.media_type is MediaType.VIDEO and shutil.which("ffmpeg") is None:
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.SKIPPED,
            message="ffmpeg is unavailable; video processing skipped",
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        frames = _process_frames(source, config, output_dir)
        manifest = _manifest_data(source, config, frames)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        return ScanResult(
            path=source.path,
            media_type=source.media_type,
            status=ScanStatus.ERROR,
            message=f"processing failed: {exc}",
            output_dir=output_dir,
            manifest_path=manifest_path,
        )

    return ScanResult(
        path=source.path,
        media_type=source.media_type,
        status=ScanStatus.PROCESSED,
        message=f"processed {len(frames)} frame(s)",
        output_dir=output_dir,
        manifest_path=manifest_path,
    )


def _process_frames(
    source: SourceMedia,
    config: AppConfig,
    output_dir: Path,
) -> tuple[ProcessedFrame, ...]:
    if source.media_type is MediaType.IMAGE:
        return _process_static_image(source.path, config, output_dir)
    if source.media_type is MediaType.GIF:
        return _process_gif(source.path, config, output_dir)
    if source.media_type is MediaType.VIDEO:
        return _process_video(source.path, config, output_dir)
    raise ValueError(f"Unsupported media type: {source.media_type.value}")


def _process_static_image(
    path: Path,
    config: AppConfig,
    output_dir: Path,
) -> tuple[ProcessedFrame, ...]:
    with Image.open(path) as image:
        frame_path = FRAME_NAME_TEMPLATE.format(index=0)
        normalized = _normalize_image(image, config)
        normalized.save(output_dir / frame_path)
    return (
        ProcessedFrame(
            path=frame_path,
            duration_seconds=config.playback.image_duration_seconds,
        ),
    )


def _process_gif(
    path: Path,
    config: AppConfig,
    output_dir: Path,
) -> tuple[ProcessedFrame, ...]:
    processed_frames: list[ProcessedFrame] = []
    with Image.open(path) as image:
        for index, source_frame in enumerate(ImageSequence.Iterator(image)):
            frame_path = FRAME_NAME_TEMPLATE.format(index=index)
            duration_ms = source_frame.info.get("duration", 100)
            duration_seconds = max(0.001, round(float(duration_ms) / 1000, 3))
            normalized = _normalize_image(source_frame, config)
            normalized.save(output_dir / frame_path)
            processed_frames.append(
                ProcessedFrame(path=frame_path, duration_seconds=duration_seconds),
            )

    if not processed_frames:
        raise ValueError("GIF contained no frames")
    return tuple(processed_frames)


def _process_video(
    path: Path,
    config: AppConfig,
    output_dir: Path,
) -> tuple[ProcessedFrame, ...]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValueError("ffmpeg is unavailable")

    with tempfile.TemporaryDirectory(prefix="ledpi-video-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        frame_template = temp_dir / FRAME_NAME_TEMPLATE
        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-vf",
                f"fps={VIDEO_FRAME_RATE}",
                str(frame_template),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "ffmpeg exited with an error"
            raise ValueError(detail)

        extracted = sorted(temp_dir.glob("frame_*.png"))
        if not extracted:
            raise ValueError("ffmpeg produced no frames")

        processed_frames: list[ProcessedFrame] = []
        for index, extracted_frame in enumerate(extracted):
            frame_path = FRAME_NAME_TEMPLATE.format(index=index)
            with Image.open(extracted_frame) as image:
                normalized = _normalize_image(image, config)
                normalized.save(output_dir / frame_path)
            processed_frames.append(
                ProcessedFrame(
                    path=frame_path,
                    duration_seconds=round(1 / VIDEO_FRAME_RATE, 3),
                ),
            )

    return tuple(processed_frames)


def _normalize_image(image: Image.Image, config: AppConfig) -> Image.Image:
    target_size = (config.panel.width, config.panel.height)
    image = ImageOps.exif_transpose(image)

    if image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    ):
        background = Image.new("RGBA", image.size, (0, 0, 0, 255))
        image = Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
    else:
        image = image.convert("RGB")

    resample = Image.Resampling.LANCZOS
    if config.processing.fit == "cover":
        return ImageOps.fit(image, target_size, method=resample, centering=(0.5, 0.5))

    contained = image.copy()
    contained.thumbnail(target_size, resample)
    canvas = Image.new("RGB", target_size, (0, 0, 0))
    x = (target_size[0] - contained.width) // 2
    y = (target_size[1] - contained.height) // 2
    canvas.paste(contained, (x, y))
    return canvas


def _manifest_data(
    source: SourceMedia,
    config: AppConfig,
    frames: Iterable[ProcessedFrame],
) -> dict[str, Any]:
    frames = tuple(frames)
    profile = _processing_profile(config)
    source_hash = _source_hash(source.path)
    return {
        "version": MANIFEST_VERSION,
        "source": {
            "path": str(source.path),
            "name": source.path.name,
            "sha256": source_hash,
        },
        "media_type": source.media_type.value,
        "processing": profile,
        "dimensions": {
            "width": config.panel.width,
            "height": config.panel.height,
        },
        "duration_seconds": round(sum(frame.duration_seconds for frame in frames), 3),
        "frame_count": len(frames),
        "frames": [
            {
                "path": frame.path,
                "duration_seconds": frame.duration_seconds,
            }
            for frame in frames
        ],
    }


def _manifest_is_valid(
    manifest_path: Path,
    source: SourceMedia,
    config: AppConfig,
) -> bool:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    if manifest.get("version") != MANIFEST_VERSION:
        return False
    if manifest.get("media_type") != source.media_type.value:
        return False
    if manifest.get("processing") != _processing_profile(config):
        return False

    source_data = manifest.get("source")
    if not isinstance(source_data, dict):
        return False
    if source_data.get("sha256") != _source_hash(source.path):
        return False

    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames:
        return False
    for frame in frames:
        if not isinstance(frame, dict):
            return False
        path = frame.get("path")
        duration = frame.get("duration_seconds")
        if not isinstance(path, str):
            return False
        if not isinstance(duration, int | float) or duration <= 0:
            return False
        if not (manifest_path.parent / path).exists():
            return False

    return True


def _processing_profile(config: AppConfig) -> dict[str, Any]:
    return {
        "width": config.panel.width,
        "height": config.panel.height,
        "fit": config.processing.fit,
        "image_duration_seconds": config.playback.image_duration_seconds,
        "video_frame_rate": VIDEO_FRAME_RATE,
        "pipeline_version": MANIFEST_VERSION,
    }


def _source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
