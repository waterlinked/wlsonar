# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "wlsonar>=0.5.4,<0.6",
# ]
# ///
"""Example use of wlsonar module: Record UDP packets from Sonar 3D-15 to a .sonar file."""

import argparse
import time
from collections import defaultdict
from importlib.metadata import version
from typing import DefaultDict, Set

import wlsonar.range_image_protocol as rip
from wlsonar import (
    DEFAULT_MCAST_PORT,
    UDP_MAX_DATAGRAM_SIZE,
    Sonar3D,
    open_sonar_udp_multicast_socket,
    open_sonar_udp_unicast_socket,
)


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
            "Example use of wlsonar module: Record UDP multicast packets from Sonar 3D-15 to a "
            + ".sonar file, which can be opened in https://sonar.replay.waterlinked.com/"
        ),
    )
    parser.add_argument("--output", required=True, type=str, help="Output .sonar filename")
    parser.add_argument(
        "--ip",
        type=str,
        help="If given, only record packets from this Sonar "
        + "IP address. Otherwise, record from any Sonar.",
    )
    parser.add_argument(
        "--computer-ip",
        type=str,
        default=None,
        help="Local interface IP address to listen on (default: choose automatically)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=DEFAULT_MCAST_PORT,
        help="UDP port to listen on. Default is multicast port",
    )
    parser.add_argument(
        "--udp-mode",
        choices=("multicast", "unicast"),
        default=None,
        help=(
            "UDP delivery mode. Defaults to multicast socket, and requires active choice for "
            "--verify"
        ),
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=None,
        help="Record for this many seconds and then exit (default: run until interrupted)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Requires --ip setting. Verify configuration of sonar before starting to record.",
    )
    parser.add_argument(
        "--log-every-ms",
        type=float,
        default=1000.0,
        help="How often to log " + "stats (default: every second)",
    )
    args = parser.parse_args()

    output_filename = args.output
    print(f"Recording UDP packets from Sonar 3D-15 to {output_filename}")

    if args.udp_mode is None:
        # default to multicast if not specified
        print("UDP mode: multicast")
    else:
        print(f"UDP mode: {args.udp_mode}")

    if args.computer_ip is not None:
        print(f"Listening on interface with IP: {args.computer_ip}")
    print(f"Listening on UDP port: {args.udp_port}")

    if args.ip is not None:
        print(f"Filtering packets from Sonar IP: {args.ip}")

    if args.seconds is not None:
        print(f"Will record for {args.seconds} seconds.")

    if args.verify:
        if args.ip is None:
            raise ValueError("--verify requires --ip")
        sonar = Sonar3D(ip=args.ip)
        if args.udp_mode is None:
            raise ValueError("--verify requires --udp-mode")

        # verify sonar is configured to send us data
        udp_config = sonar.get_udp_config()
        if udp_config.mode == "multicast" and args.udp_mode == "multicast":
            print("Verified sonar is configured for multicast: OK")
        elif udp_config.mode == "unicast" and args.udp_mode == "unicast":
            if args.computer_ip is None:
                raise ValueError(
                    "--verify found configuration issue: Sonar is in unicast mode, and --verify "
                    "for unicast mode requires --computer-ip to check that unicast is directed at "
                    "this computer"
                )
            if (
                udp_config.unicast_destination_ip != args.computer_ip
                or udp_config.unicast_destination_port != args.udp_port
            ):
                raise ValueError(
                    "--verify found configuration issue: Sonar is configured for unicast but not "
                    "directed at --computer-ip and --udp-port. It is directed at "
                    f"{udp_config.unicast_destination_ip}:{udp_config.unicast_destination_port} "
                    "instead"
                )
            print(
                "Verified sonar is configured for unicast directed at --computer-ip and "
                "--udp-port: OK"
            )
        elif udp_config.mode != args.udp_mode:
            raise ValueError(
                f"--verify found configuration issue: Sonar UDP mode is {udp_config.mode} and "
                f"--udp-mode is {args.udp_mode}"
            )
        else:
            raise ValueError(
                f"--verify found configuration issue: Sonar UDP mode is {udp_config.mode}, "
                "expected multicast, or unicast directed at --computer-ip and --udp-port"
            )

        # verify acoustics enabled
        if not sonar.get_acoustics_enabled():
            raise ValueError("--verify found configuration issue: Sonar has acoustics disabled")
        print("Verified sonar has acoustics enabled: OK")

    print()

    # stats
    recv_from_ips: Set[int] = set()
    total_msg_counts: DefaultDict[str, int] = defaultdict(int)
    total_msg_sizes: DefaultDict[str, int] = defaultdict(int)

    # setup sock, with specific iface IP if given
    kwargs = {}
    if args.computer_ip is not None:
        kwargs["iface_ip"] = args.computer_ip
    kwargs["udp_port"] = args.udp_port

    if args.udp_mode == "unicast":
        sock = open_sonar_udp_unicast_socket(**kwargs)
    elif (
        args.udp_mode == "multicast"
        or args.udp_mode is None  # default to multicast if not specified
    ):
        sock = open_sonar_udp_multicast_socket(**kwargs)
    else:
        raise ValueError(f"Invalid --udp-mode: {args.udp_mode}")
    sock.settimeout(1.0)
    try:
        # receive packets and write to open file
        with open(output_filename, "wb") as f:
            last_log_time = 0.0
            start = time.monotonic()
            while True:
                if args.seconds is not None and (time.monotonic() - start) >= args.seconds:
                    print(f"Recorded for {args.seconds} seconds, exiting")
                    break

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
                            "WARNING: receiving packets from multiple "
                            + f"Sonar IPs: {recv_from_ips}"
                        )
                        print()

                try:
                    msg = rip.unpackb(packet)
                except rip.UnknownProtobufTypeError:
                    # silently skip unknown packet types
                    continue

                f.write(packet)

                total_msg_counts[msg.DESCRIPTOR.name] += 1
                total_msg_sizes[msg.DESCRIPTOR.name] += len(packet)

                if (time.monotonic() - last_log_time) >= args.log_every_ms / 1000:
                    last_log_time = time.monotonic()
                    current_size = f.tell()
                    elapsed = time.monotonic() - start
                    print(
                        f"elapsed={elapsed:.2f} s | "
                        + f"size={human_readable_size(current_size)} | "
                        + f"total_msg_sizes={ {name: human_readable_size(size) for name, size in total_msg_sizes.items()} } | "  # noqa: E501
                        + f"total_msg_counts={total_msg_counts.items()} | "
                        + f"from={recv_from_ips}"
                    )
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.close()
        except OSError:
            # silently ignore
            pass
