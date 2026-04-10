import wlsonar.range_image_protocol as rip
from wlsonar import (
    bitmap_image_to_strength_linear,
    bitmap_image_to_strength_log,
    range_image_to_distance,
    range_image_to_xyz,
)
from wlsonar.range_image_protocol import BitmapImageGreyscale8, BitmapImageType, RangeImage


def test_range_image_helpers() -> None:
    # basic sanity checks of the helper functions with the example data file

    # find first range image in example data file
    with open("tests/data/ship_short.sonar", "rb") as f:
        while True:
            try:
                msg = rip.unpack(f)
            except rip.UnknownProtobufTypeError:
                # silently skip unknown packet types
                continue
            except EOFError:
                raise AssertionError("Expected at least one RangeImage in example data")

            if isinstance(msg, RangeImage):
                example_range_image = msg
                break

    distances = range_image_to_distance(example_range_image)
    xyz = range_image_to_xyz(example_range_image)
    expected_len = example_range_image.width * example_range_image.height

    assert len(example_range_image.image_pixel_data) == expected_len, (
        "Unexpected number of pixels in example range image"
    )
    assert len(distances) == expected_len
    assert len(xyz) == expected_len

    # check types
    assert all(isinstance(distance, float) for distance in distances)
    assert all(
        voxel is None
        or (
            isinstance(voxel, tuple)
            and len(voxel) == 3
            and all(isinstance(coord, float) for coord in voxel)
        )
        for voxel in xyz
    )

    # smoke test data
    assert any(distance > 0.0 for distance in distances), (
        "Expected at least one valid distance in example range image"
    )
    assert any(voxel is None for voxel in xyz), (
        "Expected at least one pixel with no data in example range image"
    )
    assert any(voxel is not None for voxel in xyz), (
        "Expected at least one valid voxel in example range image"
    )


def test_bitmap_image_helpers() -> None:
    # basic sanity checks of the helper functions with the example data file

    # find first bitmap image in example data file
    with open("tests/data/ship_short.sonar", "rb") as f:
        while True:
            try:
                msg = rip.unpack(f)
            except rip.UnknownProtobufTypeError:
                # silently skip unknown packet types
                continue
            except EOFError:
                raise AssertionError("Expected at least one BitmapImage in example data")

            if (
                isinstance(msg, BitmapImageGreyscale8)
                and msg.type == BitmapImageType.SIGNAL_STRENGTH_IMAGE
            ):
                example_bitmap_image = msg
                break

    strength_log = bitmap_image_to_strength_log(example_bitmap_image)
    strength_linear = bitmap_image_to_strength_linear(example_bitmap_image)
    expected_len = example_bitmap_image.width * example_bitmap_image.height

    assert len(example_bitmap_image.image_pixel_data) == expected_len, (
        "Unexpected number of pixels in example bitmap image"
    )
    assert len(strength_log) == expected_len
    assert len(strength_linear) == expected_len

    # check types
    assert all(isinstance(strength, int) for strength in strength_log)
    assert all(isinstance(strength, int) for strength in strength_linear)

    # smoke test data
    assert any(strength > 0.0 for strength in strength_log), (
        "Expected at least one positive strength value in example bitmap image"
    )
    assert any(strength == 0.0 for strength in strength_log), (
        "Expected at least one zero strength value in example bitmap image"
    )
    assert any(strength > 0.0 for strength in strength_linear), (
        "Expected at least one positive strength value in example bitmap image"
    )
    assert any(strength == 0.0 for strength in strength_linear), (
        "Expected at least one zero strength value in example bitmap image"
    )


def test_bitmap_image_to_strength_linear__output() -> None:
    # construct bitmap image with minimal fields only
    image_pixel_data = [0 for _ in range(256 * 64)]
    image_pixel_data[1] = 100
    image_pixel_data[2] = 255
    bitmap_image = rip.BitmapImageGreyscale8(
        type=BitmapImageType.SIGNAL_STRENGTH_IMAGE,
        image_pixel_data=bytes(image_pixel_data),
    )
    strength_linear = bitmap_image_to_strength_linear(bitmap_image)

    assert len(strength_linear) == 256 * 64, (
        "Unexpected output length from bitmap_image_to_strength_linear"
    )
    assert all(isinstance(strength, int) for strength in strength_linear), (
        "Expected strength_linear to be ints"
    )

    # smoke tests:

    assert strength_linear[0] == 0, "Expected input of 0 to produce output of 0"

    assert strength_linear[1] > 0, "Expected input of 100 to produce positive output"
    assert strength_linear[1] < 2**15 - 1, (
        "Expected input of 100 to produce output of less than 2**15-1"
    )

    assert strength_linear[2] > strength_linear[1], (
        "Expected input of 255 to produce stronger output than input of 100"
    )
    assert strength_linear[2] <= 2**15 - 1, (
        "Expected input of 255 to produce output of at most 2**15-1"
    )
