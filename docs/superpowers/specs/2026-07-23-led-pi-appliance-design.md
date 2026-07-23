# LED Pi Appliance Design

Date: 2026-07-23

## Context

This repository is a fresh rebuild for a Raspberry Pi 5 project driving a 64x64 HUB75 RGB LED matrix through the Adafruit RGB Matrix Bonnet. The first phase is a dedicated LED appliance for fun, non-critical photo and video displays. A later phase should add web control, uploads, automation, and IoT-style integrations.

The hardware-facing path should prioritize reliable bring-up and debuggability. Docker is useful for future server-like services, but the initial LED renderer should run directly on Raspberry Pi OS so hardware access through Piomatter can be debugged without container permissions in the way.

Relevant hardware references:

- Panel: https://www.adafruit.com/product/3649
- Bonnet: https://www.adafruit.com/product/3211
- Pi 5 matrix guide: https://learn.adafruit.com/rgb-matrix-panels-with-raspberry-pi-5/overview

## Objectives

Build a Raspberry Pi 5 LED matrix appliance that boots into a local photo and video playlist, preprocesses uploaded media into matrix-ready frames, and drives a single 64x64 HUB75 panel through the Adafruit RGB Matrix Bonnet using Piomatter.

Keep the hardware renderer separate from media ingestion and control concerns so a later web upload/control layer can be added without rewriting display code.

## Architecture

Use a hybrid service boundary:

1. Host-native LED renderer
   - Runs directly on Raspberry Pi OS.
   - Owns Piomatter setup, panel geometry, brightness, framebuffer writes, playback timing, and hardware errors.
   - Can be launched manually during bring-up and installed as a systemd service for appliance mode.

2. Media pipeline
   - Scans a local inbox directory for source media.
   - Validates supported image, GIF, and video files.
   - Converts source media into normalized 64x64 RGB playback assets.
   - Writes processed assets and metadata to a cache directory.
   - Is callable from the CLI now and from a future web uploader later.

3. Control boundary
   - Version 1 uses file/config based control: copy files into an inbox, run or trigger a scan, and start/reload playback.
   - Future web/API services can upload into the same inbox, call the same media pipeline, and ask the renderer to reload or switch modes.
   - Docker should initially be reserved for these higher-level services, not the low-level hardware renderer.

## Components

The initial repo should be organized around clear boundaries:

- `ledpi/config/`: typed config loading for panel geometry, brightness, media paths, playback timing, and preprocessing options.
- `ledpi/media/`: media discovery, validation, fingerprinting, preprocessing, cache invalidation, and manifest writing.
- `ledpi/render/`: frame abstractions, renderer interface, fake renderer for tests, and Piomatter renderer implementation.
- `ledpi/playback/`: playlist loading, ordering, image duration, video frame timing, looping, and empty-playlist fallback.
- `ledpi/service/`: CLI entrypoints such as `run`, `scan`, `test-pattern`, and `doctor`.
- `scripts/`: Raspberry Pi setup helpers, systemd install helpers, and future Docker compose helpers.
- `docs/`: hardware notes, setup instructions, operating instructions, and design specs.

Python should be the primary language. Pillow and NumPy are suitable for image/frame work. Video extraction should use the simplest dependable Raspberry Pi OS-compatible tool, likely ffmpeg or OpenCV after a dependency check during implementation planning.

Piomatter should be isolated behind a renderer interface. Non-hardware tests should use a fake in-memory renderer.

## Data Flow

Version 1 uses a local folder lifecycle:

1. Source media is copied onto the Pi into `media/inbox/`.
2. `ledpi scan` finds new or changed files.
3. The scanner validates type and readability.
4. Supported media is transformed into 64x64 RGB playback assets under `media/processed/`.
5. Images become normalized frame assets with display duration metadata.
6. GIFs and videos become frame sequences or frame bundles with timing metadata.
7. `ledpi run` loads the processed playlist and streams frames through the renderer.
8. If no processed media is available, playback shows a built-in test/status pattern instead of exiting silently.
9. A future web uploader follows the same path: upload to inbox, call scan, request reload.

Version 1 should avoid a database. A manifest per processed item is enough. Each manifest should include source path, source content hash, media type, preprocessing options, output frame count, frame timing, duration, and dimensions.

## Configuration

Configuration should support:

- Panel width and height, defaulting to 64x64.
- Panel addressing options required by the Adafruit Bonnet and Piomatter.
- Brightness with a conservative default.
- Media inbox, processed cache, and log paths.
- Image fit mode, such as cover or contain.
- Default image display duration.
- Playlist order, initially deterministic or shuffled by config.
- Development mode or dry-run behavior that does not require Piomatter.

Configuration should be simple enough to edit over SSH. A single TOML or YAML file is preferred over environment variables for user-facing appliance behavior.

## Error Handling And Operations

The appliance should fail visibly and recoverably:

- Bad source media is skipped with a clear scan report.
- A preprocessing failure for one file does not prevent other files from being processed.
- Stale or corrupt processed manifests are rebuilt from source media when possible.
- Missing or empty playlists fall back to a test/status pattern.
- Renderer startup errors are logged clearly and should cause the service to exit rather than pretend playback is running.
- Runtime logs should go to stdout so systemd journal captures them.
- Brightness should default conservatively to reduce power and thermal risk during bring-up.

Add a `doctor` command once the core package exists. It should check the platform, Python version, media directories, configuration readability, optional media tooling, and Piomatter availability.

## Testing

Automated tests should cover the code that does not require the physical panel:

- Config parsing and default values.
- Media scanning for supported, unsupported, changed, and missing files.
- Manifest generation and cache invalidation.
- Image preprocessing behavior.
- Video and GIF preprocessing where practical, with optional tooling checks.
- Playlist ordering and empty-playlist fallback.
- Renderer contract using a fake renderer.
- CLI smoke tests for `scan`, `run --dry-run`, `test-pattern --dry-run`, and `doctor`.

Hardware validation remains manual in version 1:

1. Show a built-in test pattern.
2. Show a known static image.
3. Show a short animation or video.
4. Install and verify the systemd service boot path.

## Docker Position

Docker should be part of the long-term architecture, but not the first thing that touches the LED panel.

Recommended sequence:

1. Bring up panel hardware with a host-native Python test pattern.
2. Build and test the host-native renderer and media pipeline.
3. Install the renderer as a systemd appliance service.
4. Add a Dockerized web/API upload service later.
5. Keep the web service talking to the same media pipeline and renderer boundary.

This keeps the low-level Piomatter path stable while still leaving room for Dockerized server-like behavior.

## Non-Goals For Version 1

- No full web control panel.
- No database.
- No Dockerized hardware renderer.
- No external IoT integrations.
- No multiplayer or input-driven games.
- No advanced scheduling beyond playlist looping.
- No audio playback until speaker hardware and desired behavior are defined.

## Old System Reference

An older implementation exists and may be useful as reference material. It should not be ported directly. Use it only to identify lessons learned, feature ideas, edge cases, and coupling/cohesion problems to avoid.
