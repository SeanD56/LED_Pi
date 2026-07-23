"""Built-in frame generators for fallback and hardware bring-up."""

from __future__ import annotations

from ledpi.render.frame import Frame


def generate_test_pattern_frame(
    *,
    width: int,
    height: int,
    duration_seconds: float = 1.0,
) -> Frame:
    """Generate a small RGB gradient/checker test pattern."""

    pixels = bytearray()
    block_size = max(1, min(width, height) // 8)

    for y in range(height):
        for x in range(width):
            checker = ((x // block_size) + (y // block_size)) % 2
            red = round(255 * x / max(1, width - 1))
            green = round(255 * y / max(1, height - 1))
            blue = 64 if checker else 192
            pixels.extend((red, green, blue))

    return Frame(
        width=width,
        height=height,
        pixels=bytes(pixels),
        duration_seconds=duration_seconds,
    )
