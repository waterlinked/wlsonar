"""Package wlsonar.

Package wlsonar provides a python client and Range Image Protocol utilities for Water Linked
Sonar 3D-15.
"""

from ._client import (
    FALLBACK_IP,
    UDP_MAX_DATAGRAM_SIZE,
    Sonar3D,
    UdpConfig,
    VersionException,
)
from ._msg_helper import (
    bitmap_image_to_strength_linear,
    bitmap_image_to_strength_log,
    range_image_to_distance,
    range_image_to_xyz,
)
from ._udp_helper import (
    DEFAULT_MCAST_GRP,
    DEFAULT_MCAST_PORT,
    open_sonar_udp_multicast_socket,
    open_sonar_udp_unicast_socket,
)

__all__ = [
    "DEFAULT_MCAST_GRP",
    "DEFAULT_MCAST_PORT",
    "FALLBACK_IP",
    "UDP_MAX_DATAGRAM_SIZE",
    "Sonar3D",
    "UdpConfig",
    "VersionException",
    "bitmap_image_to_strength_linear",
    "bitmap_image_to_strength_log",
    "open_sonar_udp_multicast_socket",
    "open_sonar_udp_unicast_socket",
    "range_image_to_distance",
    "range_image_to_xyz",
]
