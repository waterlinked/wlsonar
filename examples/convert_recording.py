# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=12.1.0,<13",
#     "wlsonar>=0.3.1,<0.5",
# ]
# ///
"""Example use of wlsonar module to convert .sonar recordings to .xyz and .png files."""

import argparse
import os
from importlib.metadata import version

from PIL import Image

import wlsonar
import wlsonar.range_image_protocol as rip


def human_readable_size(size: int) -> str:
    """Human readable size."""
    x = float(size)
    for unit in ["bytes", "KB", "MB", "GB", "TB"]:
        if x < 1024.0:
            return f"{x:.2f} {unit}"
        x /= 1024.0
    return f"{x:.2f} PB"


def make_filename(header: rip.Header, extension: str) -> str:
    """make_filename creates a filename based on the timestamp and sequence ID in the header."""
    # trim microseconds to milliseconds
    timestamp_str = header.timestamp.ToDatetime().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    seqno = header.sequence_id
    filename = f"{timestamp_str}_seq{seqno}.{extension}"
    return filename


if __name__ == "__main__":
    print(f"wlsonar version: {version('wlsonar')}")

    parser = argparse.ArgumentParser(
        description=(
            "Example use of wlsonar module: Convert the first -n packets to .xyz and "
            ".png files. .xyz is a simple file format for point clouds, which can be opened in "
            " for example Meshlab"
        ),
    )
    parser.add_argument("--file", required=True, type=str, help="Input .sonar file")
    parser.add_argument(
        "-n", type=int, default=2, help="Number of Sonar packets to convert (default: 2)"
    )
    parser.add_argument(
        "--output-folder",
        required=True,
        type=str,
        help="Output folder for .xyz and .png files",
    )
    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)

    n_packets = 0

    with open(args.file, "rb") as f_sonar:
        while n_packets < args.n:
            try:
                msg = rip.unpack(
                    f_sonar, known_message_types=(rip.RangeImage, rip.BitmapImageGreyscale8)
                )
            except rip.UnknownProtobufTypeError:
                # silently skip unknown packet types
                continue
            except EOFError:
                # end of file
                break

            n_packets += 1

            if isinstance(msg, rip.RangeImage):
                filename = make_filename(msg.header, "xyz")
                path = os.path.join(args.output_folder, filename)
                wrote = 0
                with open(path, "w", encoding="ascii") as f_xyz:
                    voxels = wlsonar.range_image_to_xyz(msg)
                    for voxel in voxels:
                        if voxel is not None:
                            x, y, z = voxel
                            f_xyz.write(f"{x} {y} {z}\n")
                            wrote += 1
                print(f"Wrote {filename} with {wrote} voxels")
            elif isinstance(msg, rip.BitmapImageGreyscale8):
                if msg.type != rip.BitmapImageType.SIGNAL_STRENGTH_IMAGE:
                    print(
                        "WARNING: Skipping BitmapImageGreyscale8 message of "
                        + "type other than SIGNAL_STRENGTH_IMAGE"
                    )
                    continue
                filename = make_filename(msg.header, "png")
                img = Image.frombytes(
                    "L",
                    (msg.width, msg.height),
                    msg.image_pixel_data,
                ).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                img.save(os.path.join(args.output_folder, filename))
                print(f"Wrote {filename} with size {msg.width}x{msg.height}")
                continue
            else:
                raise RuntimeError(f"Unhandled message type: {type(msg)}")
