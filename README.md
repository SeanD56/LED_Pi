# LED Pi

Raspberry Pi 5 LED matrix appliance for local photo and video playback.

This project targets a 64x64 HUB75 RGB LED matrix driven through the Adafruit RGB Matrix Bonnet. The first implementation milestone is intentionally small: establish the Python package, CLI surface, local media directories, and test tooling before adding hardware and media-processing behavior.

## Current Direction

- Run the low-level LED renderer directly on Raspberry Pi OS for reliable hardware bring-up.
- Keep media ingestion, playback, and renderer boundaries separate.
- Use Docker later for web upload/control and server-like integrations, not for the first hardware renderer.

Design and planning docs:

- [Design spec](docs/superpowers/specs/2026-07-23-led-pi-appliance-design.md)
- [Implementation plan](docs/superpowers/plans/2026-07-23-led-pi-appliance-implementation-plan.md)

## Development

Create a virtual environment and install test dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
```

Run tests:

```bash
python -m pytest
```

Inspect the CLI:

```bash
python -m ledpi.service --help
ledpi --help
```

## Media Folders

- `media/inbox/`: local source media copied onto the Pi.
- `media/processed/`: generated matrix-ready playback assets.

User media and generated assets are ignored by git. The `.gitkeep` files only preserve the expected directory layout.
