import pytest

from ledpi.render import FakeRenderer, Frame, RendererError, generate_test_pattern_frame


def test_frame_accepts_valid_rgb_bytes():
    frame = Frame(width=2, height=2, pixels=b"\x00\x10\x20" * 4, duration_seconds=0.5)

    assert frame.width == 2
    assert frame.height == 2
    assert frame.pixels == b"\x00\x10\x20" * 4
    assert frame.duration_seconds == 0.5


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"width": 0, "height": 2, "pixels": b"\x00" * 12},
            "width",
        ),
        (
            {"width": 2, "height": 0, "pixels": b"\x00" * 12},
            "height",
        ),
        (
            {"width": 2, "height": 2, "pixels": b"\x00" * 11},
            "expected 12 RGB bytes",
        ),
        (
            {"width": 2, "height": 2, "pixels": b"\x00" * 12, "duration_seconds": 0},
            "duration_seconds",
        ),
    ],
)
def test_frame_rejects_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Frame(**kwargs)


def test_fake_renderer_records_frames():
    frame = Frame(width=1, height=1, pixels=b"\xff\x00\x00", duration_seconds=1.0)
    renderer = FakeRenderer()

    renderer.start()
    renderer.show_frame(frame)
    renderer.stop()

    assert renderer.started is True
    assert renderer.stopped is True
    assert renderer.shown_frames == [frame]


def test_fake_renderer_requires_start_before_showing_frame():
    frame = Frame(width=1, height=1, pixels=b"\x00\x00\x00", duration_seconds=1.0)
    renderer = FakeRenderer()

    with pytest.raises(RendererError, match="started"):
        renderer.show_frame(frame)


def test_test_pattern_frame_has_expected_shape():
    frame = generate_test_pattern_frame(width=8, height=8, duration_seconds=0.25)

    assert frame.width == 8
    assert frame.height == 8
    assert frame.duration_seconds == 0.25
    assert len(frame.pixels) == 8 * 8 * 3
    assert len(set(frame.pixels)) > 1
