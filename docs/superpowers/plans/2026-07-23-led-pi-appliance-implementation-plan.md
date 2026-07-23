# LED Pi Appliance Implementation Plan

Date: 2026-07-23

Design spec: `docs/superpowers/specs/2026-07-23-led-pi-appliance-design.md`

## Goal

Create the first buildable version of the LED Pi appliance:

- A Python package with clear config, media, render, playback, and CLI boundaries.
- A local media pipeline that converts source images, GIFs, and videos into 64x64 playback assets.
- A dry-run playback path that can be tested without Raspberry Pi hardware.
- A Piomatter renderer adapter that is isolated from the rest of the app.
- Setup documentation for Raspberry Pi OS, first-light testing, and systemd appliance mode.

## Milestone 1: Project Skeleton And Tooling

Create the baseline Python project structure:

- `pyproject.toml` with package metadata, CLI entrypoint, runtime dependencies, and test dependencies.
- `ledpi/` package with subpackages for `config`, `media`, `render`, `playback`, and `service`.
- `tests/` package mirroring the core boundaries.
- `media/inbox/.gitkeep` and `media/processed/.gitkeep` so the expected local folders exist without committing user media.
- `.gitignore` entries for processed frames, local config overrides, caches, virtualenvs, and Python build output.
- `README.md` rewritten with the project purpose, current milestone, and basic commands.

Use standard library modules where practical. Prefer `argparse`, `dataclasses`, `pathlib`, `json`, and `tomllib` before adding framework dependencies. Use `pytest` for tests, Pillow for image processing, and NumPy only where it simplifies frame handling.

Verification:

- `python -m pytest`
- `python -m ledpi.service --help`

## Milestone 2: Configuration

Implement typed configuration loading:

- Default config values for a single 64x64 panel.
- Media inbox and processed paths.
- Brightness default with a conservative value.
- Default image duration.
- Playlist ordering mode.
- Image fit mode.
- Dry-run flag.

Use TOML for user-facing config because Python 3.11+ can read it with `tomllib`.

Add tests for:

- Default config creation.
- Loading an explicit config file.
- Rejecting invalid dimensions, brightness, duration, and unsupported fit/order modes.

Verification:

- `python -m pytest tests/test_config.py`

## Milestone 3: Frame And Renderer Contracts

Define the hardware-independent rendering boundary:

- `Frame`: width, height, RGB bytes or array, duration metadata.
- `Renderer` protocol/interface with lifecycle and frame display methods.
- `FakeRenderer` for dry-run tests.
- `TestPatternRenderer` or pattern generator for fallback and bring-up.

Keep Piomatter out of imports used by normal unit tests. The real Piomatter adapter should import hardware dependencies lazily inside the Pi-specific class.

Add tests for:

- Frame validation.
- Fake renderer call recording.
- Test pattern frame dimensions and byte shape.

Verification:

- `python -m pytest tests/test_render.py`

## Milestone 4: Media Pipeline

Implement local source media ingestion:

- Scan `media/inbox` for supported image, GIF, and video extensions.
- Fingerprint sources using content hash and preprocessing options.
- Write processed output to `media/processed/<fingerprint>/`.
- Write a `manifest.json` per processed item.
- Rebuild stale or corrupt processed items.

Initial processed output should favor inspectability over maximum performance:

- Static images become `frame_000000.png` plus manifest metadata.
- GIFs become a directory of frame PNGs plus timing metadata.
- Videos use the `ffmpeg` CLI if present, then the same frame normalization path.

If `ffmpeg` is unavailable, video files should be skipped with a clear scan result. The app should still process images and GIFs.

Add tests for:

- Supported and unsupported file discovery.
- Hash-based cache behavior.
- Image resizing and fit modes.
- Manifest writing and stale rebuild detection.
- Video skip behavior when `ffmpeg` is unavailable.

Verification:

- `python -m pytest tests/test_media.py`
- `python -m ledpi.service scan --dry-run`

## Milestone 5: Playlist And Playback

Implement playlist loading and dry-run playback:

- Load processed manifests into playable items.
- Support deterministic and shuffled order.
- Convert manifests into timed frames.
- Loop continuously in normal mode.
- Exit after one pass in `--once` mode for tests and manual validation.
- Show a generated fallback pattern when no processed media exists.

Add tests for:

- Empty playlist fallback.
- Deterministic ordering.
- Shuffle behavior with a seeded random source.
- One-pass playback termination.
- Renderer receives expected frames and durations.

Verification:

- `python -m pytest tests/test_playback.py`
- `python -m ledpi.service run --dry-run --once`

## Milestone 6: CLI

Expose practical command-line workflows:

- `ledpi scan`: preprocess inbox media.
- `ledpi run`: start playlist playback.
- `ledpi test-pattern`: show or dry-run a known pattern.
- `ledpi doctor`: check config, paths, Python version, optional ffmpeg, and optional Piomatter availability.

The CLI should return non-zero exit codes for invalid config and unrecoverable startup errors. Per-file media failures should be reported but should not fail the entire scan if at least one file can still be processed.

Add tests for:

- CLI help.
- Invalid config handling.
- Scan dry-run.
- Run dry-run once.
- Doctor output shape.

Verification:

- `python -m pytest tests/test_cli.py`

## Milestone 7: Piomatter Adapter And Hardware Bring-Up

Add the real hardware renderer:

- Lazy import Piomatter only inside the adapter.
- Map config values to Piomatter initialization.
- Convert internal RGB frames into the format Piomatter expects.
- Log renderer startup, frame display, and shutdown errors clearly.
- Keep dry-run and fake renderer paths usable on non-Pi machines.

Create manual validation docs:

- Raspberry Pi OS Lite setup notes.
- Piomatter installation notes.
- udev rule notes from the Adafruit Pi 5 matrix guide.
- Wiring and power checklist.
- First-light test-pattern command.

Hardware verification:

- Run `ledpi doctor` on the Pi.
- Run `ledpi test-pattern`.
- Run `ledpi scan` with a known image.
- Run `ledpi run --once`.

## Milestone 8: Appliance Mode

Add operating-system integration:

- systemd service template for `ledpi run`.
- Script to install or print the service file.
- README section for enabling, starting, stopping, and viewing logs.
- Safe defaults for restart behavior.

Verification on Pi:

- Enable the service.
- Reboot.
- Confirm playback starts automatically.
- Confirm logs are visible with `journalctl`.

## Deferred Work

These are explicitly out of the first implementation pass:

- Dockerized web upload/control service.
- Database-backed media catalog.
- Audio playback.
- IoT integrations.
- Interactive games and physical input.
- Remote update flow.
- Performance-optimized packed frame storage.

## Execution Order

Implement milestones in order. Each milestone should leave the repo in a passing state before moving to the next. Prefer tests first for config, media, render, playback, and CLI behavior. Hardware-specific behavior should be isolated so most development can happen away from the Raspberry Pi.
