import io

import pytest
from PIL import Image

from muntin import encode


def frames(n, size=(64, 32)):
    return [Image.new("RGB", size, (i * 7 % 256, 0, 0)) for i in range(n)]


def test_budget_keeps_everything_when_it_fits():
    b = encode.budget(10, 100)
    assert (b.kept, b.dropped, b.fits) == (10, 0, True)
    assert b.duration_ms == 1000
    assert b.message() is None


def test_budget_clamps_at_the_device_ceiling():
    b = encode.budget(1000, 100)
    assert b.kept == 145            # 14500 / 100
    assert b.dropped == 855
    assert b.fits is False


def test_clamp_message_names_the_drop_and_the_fix():
    msg = encode.budget(1000, 100).message()
    assert "855" in msg and "145" in msg and "14500" in msg
    assert "frame_ms" in msg


def test_max_frames_scales_with_frame_duration():
    assert encode.max_frames(100) == 145
    assert encode.max_frames(50) == 290


def test_a_single_frame_always_fits():
    assert encode.budget(1, 100).fits is True


def test_to_webp_produces_a_riff_webp():
    data, _ = encode.to_webp(frames(3))
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def test_to_webp_roundtrips_the_frame_count():
    data, budget = encode.to_webp(frames(5))
    assert budget.kept == 5
    assert Image.open(io.BytesIO(data)).n_frames == 5


def test_to_webp_truncates_and_reports_when_over_budget():
    data, budget = encode.to_webp(frames(200), frame_ms=100)
    assert budget.kept == 145 and budget.dropped == 55
    assert Image.open(io.BytesIO(data)).n_frames == 145


def test_empty_frames_is_a_loud_error():
    with pytest.raises(encode.EncodeError, match="no frames"):
        encode.to_webp([])


def test_wrong_size_frame_names_the_offender_and_the_expected_size():
    with pytest.raises(encode.EncodeError) as e:
        encode.to_webp([Image.new("RGB", (64, 32)), Image.new("RGB", (32, 16))])
    msg = str(e.value)
    assert "frame 1" in msg and "32x16" in msg and "64x32" in msg


def test_nonpositive_frame_ms_is_a_loud_error():
    with pytest.raises(encode.EncodeError, match="frame_ms"):
        encode.to_webp(frames(2), frame_ms=0)


def test_nonpositive_frame_ms_message_names_the_fix():
    with pytest.raises(encode.EncodeError) as e:
        encode.to_webp(frames(2), frame_ms=0)
    msg = str(e.value)
    assert "frame_ms" in msg and "0" in msg
    # constraint + violation alone isn't enough; must also say the fix
    assert "positive" in msg.lower()


def test_dropped_frames_message_wording_is_unchanged():
    msg = encode.budget(1000, 100).message()
    assert msg == (
        "Animation is 1000 frames x 100ms = "
        "100000ms, over the 14500ms device "
        "ceiling. Kept the first 145 frames and dropped "
        "855. Shorten the animation or lower frame_ms."
    )


def test_frame_ms_over_ceiling_fails_even_with_nothing_dropped():
    b = encode.budget(1, 15000)
    assert b.kept == 1
    assert b.dropped == 0
    assert b.duration_ms == 15000
    assert b.fits is False
    msg = b.message()
    assert msg is not None
    assert "15000" in msg
    assert "14500" in msg
    assert "frame_ms" in msg
    # must be distinguishable from the dropped-frames message
    assert "Kept the first" not in msg


def test_budget_rejects_zero_frame_ms():
    with pytest.raises(encode.EncodeError, match="frame_ms"):
        encode.budget(5, 0)


def test_budget_rejects_negative_frame_ms():
    with pytest.raises(encode.EncodeError, match="frame_ms"):
        encode.budget(5, -100)


def test_max_frames_rejects_zero_frame_ms():
    with pytest.raises(encode.EncodeError, match="frame_ms"):
        encode.max_frames(0)


def test_max_frames_rejects_negative_frame_ms():
    with pytest.raises(encode.EncodeError, match="frame_ms"):
        encode.max_frames(-1)


def test_take_rejects_a_producer_that_returns_the_wrong_frame_count():
    """take() is the one place a frame count gets clamped; if a producer
    ignores the n it's handed, the Budget it built (kept=145) silently
    lies about what actually came back (5) -- exactly the bug class take()
    exists to close."""
    with pytest.raises(encode.EncodeError) as e:
        encode.take(lambda n: [0] * 5, 300)
    msg = str(e.value)
    assert "5" in msg and "145" in msg
