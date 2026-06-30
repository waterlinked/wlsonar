# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "wlsonar>=0.5.3,<0.6",
# ]
# ///
"""Example use of wlsonar module: Receive IMU data and print it."""

import argparse
import time
from importlib.metadata import version
from typing import Set

import wlsonar.range_image_protocol as rip
from wlsonar import UDP_MAX_DATAGRAM_SIZE, Sonar3D, open_sonar_udp_multicast_socket


def human_readable_size(size: int) -> str:
    """Human readable size."""
    x = float(size)
    for unit in ["bytes", "KB", "MB", "GB", "TB"]:
        if x < 1024.0:
            return f"{x:.2f} {unit}"
        x /= 1024.0
    return f"{x:.2f} PB"


if __name__ == "__main__":
    print(f"wlsonar version: {version('wlsonar')}")

    parser = argparse.ArgumentParser(
        description=(
            "Example use of wlsonar module: Receive IMU data and visualize a simple orientation"
            "estimate."
        ),
    )
    parser.add_argument(
        "--ip",
        type=str,
        help="If given, only record packets from this Sonar "
        + "IP address. Otherwise, record from any Sonar.",
    )
    parser.add_argument(
        "--iface_ip",
        type=str,
        default=None,
        help="Local interface IP address to listen on (default: choose automatically)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=None,
        help="UDP multicast port to listen on (default: choose automatically)",
    )
    parser.add_argument(
        "--cfg", action="store_true", help="Requires --ip setting. Configure sonar for this script."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Requires --ip setting. Verify configuration of sonar before starting to record.",
    )
    args = parser.parse_args()

    if args.iface_ip is not None:
        print(f"Listening on interface with IP: {args.iface_ip}")
    if args.udp_port is not None:
        print(f"Listening on UDP port: {args.udp_port}")
    if args.ip is not None:
        print(f"Filtering packets from Sonar IP: {args.ip}")

    sonar: Sonar3D | None = None
    if args.ip:
        sonar = Sonar3D(ip=args.ip)

    if args.cfg:
        if args.ip is None or sonar is None:
            raise ValueError("--cfg requires --ip")

        # configure multicast
        sonar.set_udp_multicast()
        print("Configured for multicast: OK")
        # configure acoustics enabled
        sonar.set_acoustics_enabled(True)
        print("Configured for acoustics enabled: OK")
        # configure imu output enabled
        sonar.set_output_imu_batch_enabled(True)
        print("Configured for imu output enabled: OK")

    if args.verify:
        if args.ip is None or sonar is None:
            raise ValueError("--verify requires --ip")

        # verify multicast
        udp_config = sonar.get_udp_config()
        if udp_config.mode != "multicast":
            raise RuntimeError("Sonar is not configured for multicast. Hint: use --cfg")
        print("Verified multicast configuration: OK")
        # verify acoustics enabled
        if not sonar.get_acoustics_enabled():
            raise RuntimeError("Sonar has acoustics disabled. Hint: use --cfg")
        print("Verified acoustics enabled: OK")
        # verify imu output enabled
        if not sonar.get_output_imu_batch_enabled():
            raise RuntimeError("Sonar has imu output disabled. Hint: use --cfg")
        print("Verified imu output enabled: OK")

    print()

    # stats
    recv_from_ips: Set[int] = set()

    # print header
    print(
        f"{'batch':>8} {'ms':>10} "
        f"{'sforce_x':>9} {'sforce_y':>9} {'sforce_z':>9} "
        f"{'gyro_x':>9} {'gyro_y':>9} {'gyro_z':>9}"
    )

    # setup sock, with specific iface IP if given
    kwargs = {}
    if args.iface_ip is not None:
        kwargs["iface_ip"] = args.iface_ip
    if args.udp_port is not None:
        kwargs["udp_port"] = args.udp_port
    sock = open_sonar_udp_multicast_socket(**kwargs)
    sock.settimeout(1.0)
    try:
        # receive packets and write to open file
        start = time.monotonic()
        prev_imu_batch_seqno: int | None = None
        first_timestamp_ms: int | None = None
        while True:
            try:
                packet, addr = sock.recvfrom(UDP_MAX_DATAGRAM_SIZE)
            except TimeoutError:
                continue
            source_ip = addr[0]

            if args.ip is not None and source_ip != args.ip:
                # skip packets from other IPs
                continue

            if source_ip not in recv_from_ips:
                # this can be surprising, so warn
                recv_from_ips.add(source_ip)
                if len(recv_from_ips) > 1:
                    print()
                    print(
                        "WARNING: receiving packets from multiple " + f"Sonar IPs: {recv_from_ips}"
                    )
                    print()

            try:
                msg = rip.unpackb(packet)
            except rip.UnknownProtobufTypeError:
                # silently skip unknown packet types
                continue

            if not isinstance(msg, rip.ImuBatch):
                continue

            # simplified handling of out-of-order and dropped packets
            if prev_imu_batch_seqno is not None:
                expect_imu_batch_seqno = prev_imu_batch_seqno + 1
                if msg.batch_sequence_id < expect_imu_batch_seqno:
                    print(f"WARNING: received ImuBatch out of order: {msg.batch_sequence_id}")
                    continue
                skipped = msg.batch_sequence_id - expect_imu_batch_seqno
                if skipped > 0:
                    print(f"WARNING: skipped {skipped} ImuBatch")
            prev_imu_batch_seqno = msg.batch_sequence_id

            if len(msg.timestamp) != msg.samples:
                raise ValueError("invalid .timestamp")
            if len(msg.specific_force) != msg.samples * 3:
                raise ValueError("invalid .specific_force")
            if len(msg.rate_of_turn) != msg.samples * 3:
                raise ValueError("invalid .rate_of_turn")

            # convert to more Python-friendly data types
            timestamp_ms = [ts.ToMilliseconds() for ts in msg.timestamp]
            sforce = []
            for i in range(msg.samples):
                idx = i * 3
                sforce.append(msg.specific_force[idx : idx + 3])
            gyro = []
            for i in range(msg.samples):
                idx = i * 3
                gyro.append(msg.rate_of_turn[idx : idx + 3])

            if first_timestamp_ms is None:
                first_timestamp_ms = timestamp_ms[0]

            for i in range(msg.samples):
                fx, fy, fz = sforce[i]
                gx, gy, gz = gyro[i]

                print(
                    f"{msg.batch_sequence_id:>8} "
                    f"{timestamp_ms[i] - first_timestamp_ms:>10} "
                    f"{fx:>9.2f} {fy:>9.2f} {fz:>9.2f} "
                    f"{gx:>9.2f} {gy:>9.2f} {gz:>9.2f}"
                )

    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.close()
        except OSError:
            # silently ignore
            pass
