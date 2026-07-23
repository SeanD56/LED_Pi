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

## Configuration

The app uses TOML configuration. Start from the example file:

```bash
cp config.example.toml config.local.toml
```

Current defaults target one 64x64 HUB75 panel with five address lines and conservative brightness:

```toml
[panel]
width = 64
height = 64
address_lines = 5
brightness = 0.25
```

Relative media paths in a config file are resolved from that config file's directory.

## Media Folders

- `media/inbox/`: local source media copied onto the Pi.
- `media/processed/`: generated matrix-ready playback assets.

User media and generated assets are ignored by git. The `.gitkeep` files only preserve the expected directory layout.

## Raspberry Pi OS Prep

Use Raspberry Pi Imager to flash the SD card:

- Device: Raspberry Pi 5
- OS: Raspberry Pi OS Lite (64-bit)
- Storage: the target microSD card

Use the customization step to configure hostname, user, password, Wi-Fi, locale, timezone, and SSH. A stable hostname such as `ledpi.local` makes later SSH access easier on networks that support mDNS.

After first boot, SSH in and update the system:

```bash
sudo apt update
sudo apt full-upgrade
```

Do not rely on the Pi header to power the LED matrix. Use the panel's 5V power path and keep wiring/power checks separate from OS bring-up.
