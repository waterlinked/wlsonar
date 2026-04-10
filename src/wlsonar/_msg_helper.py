"""Helpers for RangeImage."""

import math
from typing import List, Tuple

from .range_image_protocol import BitmapImageGreyscale8, RangeImage


def range_image_to_distance(range_image: RangeImage) -> List[float]:
    """range_image_to_distance returns distances of RangeImage pixels in meters.

    Args:
        range_image: the RangeImage

    Returns:
        List of distances in meters corresponding to each pixel of range_image. If there is no data
        for a pixel, the distance for that pixel is 0.0.
    """
    # perform the conversion documented in RangeImage.image_pixel_scale
    return [
        pixel_value * range_image.image_pixel_scale for pixel_value in range_image.image_pixel_data
    ]


def range_image_to_xyz(range_image: RangeImage) -> List[None | Tuple[float, float, float]]:
    """range_image_to_xyz returns voxels of RangeImage as x,y,z in meters.

    Args:
        range_image: the RangeImage

    Returns:
        List of (x,y,z) tuples in meters corresponding to each pixel of range_image. If there is no
        data for a pixel, the list contains None for that pixel.
    """
    xyz: list[None | tuple[float, float, float]] = []

    max_pixel_x = range_image.width - 1
    max_pixel_y = range_image.height - 1

    fov_h = math.radians(range_image.fov_horizontal)
    fov_v = math.radians(range_image.fov_vertical)

    for pixel_idx, pixel_value in enumerate(range_image.image_pixel_data):
        pixel_x = pixel_idx % range_image.width
        pixel_y = pixel_idx // range_image.width
        if pixel_value == 0:
            # No data for this pixel
            xyz.append(None)
        else:
            distance_meters = pixel_value * range_image.image_pixel_scale
            yaw_rad = (pixel_x / max_pixel_x) * fov_h - fov_h / 2
            pitch_rad = (pixel_y / max_pixel_y) * fov_v - fov_v / 2

            x = distance_meters * math.cos(pitch_rad) * math.cos(yaw_rad)
            y = distance_meters * math.cos(pitch_rad) * math.sin(yaw_rad)
            z = -distance_meters * math.sin(pitch_rad)
            xyz.append((x, y, z))

    return xyz


def bitmap_image_to_strength_log(bitmap_image: BitmapImageGreyscale8) -> List[int]:
    """bitmap_image_to_strength_log returns log signal strength from a BitmapImageGreyscale8.

    BitmapImageGreyscale8 of type SIGNAL_STRENGTH_IMAGE contains a logarithmic mapping of signal
    strength to 8-bit values. This function returns that logarithmic signal strength.

    Args:
        bitmap_image: a BitmapImageGreyscale8 of type SIGNAL_STRENGTH_IMAGE

    Returns:
        List of ints corresponding to logarithmic 8-bit signal strength for each pixel of range
        image.
    """
    # image_pixel_data is the logarithmic signal strength
    return [int(pixel_value) for pixel_value in bitmap_image.image_pixel_data]


def bitmap_image_to_strength_linear(signal_strength_image: BitmapImageGreyscale8) -> List[int]:
    """bitmap_image_to_strength_linear returns linear signal strength from a BitmapImageGreyscale8.

    BitmapImageGreyscale8 of type SIGNAL_STRENGTH_IMAGE contains a logarithmic mapping of signal
    strength to 8-bit values. This function returns the linear 15-bit signal strength from those
    8-bit values.

    Args:
        signal_strength_image: a BitmapImageGreyscale8 of type SIGNAL_STRENGTH_IMAGE

    Returns:
        List of ints corresponding to linear 15-bit signal strength for each pixel of range image.
    """
    linear: list[int] = []

    for pixel_value in signal_strength_image.image_pixel_data:
        if pixel_value == 0:
            # No data for this pixel
            linear.append(0)
        else:
            # pixel_value has the following relation to the original linear signal strength:
            #
            #   pixel_value = 100.0 * log10(linear/30.0)
            #
            # invert to obtain strength:
            linear.append(round(30.0 * 10.0 ** (pixel_value / 100.0)))

    return linear
