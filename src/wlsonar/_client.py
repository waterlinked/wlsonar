"""Client for the HTTP API of the Sonar 3D-15."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Union, cast

import requests

from ._semver import _semver_is_less_than

UDP_MAX_DATAGRAM_SIZE = 65507
FALLBACK_IP = "192.168.194.96"

# Json type alias for Python types that map to JSON.
Json = Union[Dict[str, "Json"], List["Json"], str, int, float, bool, None]


@dataclass
class UdpConfig:
    """UdpConfig represents the UDP output configuration of the Sonar 3D-15.

    See https://docs.waterlinked.com/sonar-3d/sonar-3d-15-api-swagger/swagger.json for details.
    """

    mode: Literal["multicast", "unicast", "disabled"]
    unicast_destination_ip: str = ""  # ignored unless mode is "unicast"
    unicast_destination_port: int = 0  # ignored unless mode is "unicast"

    @classmethod
    def from_json(cls, data: dict) -> UdpConfig:
        """from_json creates UdpConfig from JSON dict from HTTP API."""
        return cls(
            mode=data["mode"],
            unicast_destination_ip=data["unicast_destination_ip"],
            unicast_destination_port=data["unicast_destination_port"],
        )

    def to_json(self) -> dict:
        """to_json converts UdpConfig to JSON dict for HTTP API."""
        return {
            "mode": self.mode,
            "unicast_destination_ip": self.unicast_destination_ip,
            "unicast_destination_port": self.unicast_destination_port,
        }


@dataclass
class About:
    """Information about sonar."""

    chipid: str  # example: "0x12345678"
    hardware_revision: int  # example: 6
    is_ready: bool
    product_id: int  # example: 21045
    product_name: str  # example: "Sonar 3D-15"
    variant: str
    version: str  # example: "1.5.1 (v1.3.0-26-gedccab6.2025-07-11T06:14:03.837365)""
    version_short: str  # example: "1.5.1"


@dataclass
class StatusEntry:
    """Entry in Sonar status information."""

    # Unique ID for the status message
    # example: "api-normal"
    id: str
    # Message is a human readable message describing the status
    # example: "Integration API is operational."
    message: str
    # Operational is true if the system is functional, false if it is not
    operational: bool
    # Status is "ok", "warning", or "error"
    status: str


@dataclass
class Status:
    """Sonar status information."""

    # IntegrationAPI is the status of the UDP IntegrationAPI for external communication
    api: StatusEntry
    # Temperature is the status of the Sonar temperature
    temperature: StatusEntry
    # SystemsCheck is the status of internal processing of the Sonar
    systems_check: StatusEntry


class VersionException(Exception):
    def __init__(self, what: str, min_version: str, sonar_version: str) -> None:
        super().__init__(
            f"{what} requires Sonar 3D-15 release {min_version} or newer. "
            f"Detected version: {sonar_version}"
        )


class Sonar3D:
    """Sonar3D is a client for the Water Linked Sonar 3D-15. It provides access to the HTTP API.

    The class implements the API described here:
    https://docs.waterlinked.com/sonar-3d/sonar-3d-15-api/
    """

    def __init__(self, ip: str, port: int = 80, timeout: float = 5.0) -> None:
        """Initialize the Sonar3D client.

        Gets sonar release version in order to verify connectivity and check compatibility in later
        requests.

        Requires:
            Sonar 3D-15 release 1.5.1 or higher. Some API methods require later versions.

        Args:
            ip: IP address or hostname of the Sonar device.
            port: Port number of the Sonar device HTTP API. You should not have to change this from
                the default.
            timeout: Timeout in seconds for HTTP requests.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support the Sonar3D client
        """
        self.ip = ip
        self.base_url = f"http://{ip}:{port}"
        self.timeout = timeout

        try:
            about = self.about()
        except requests.RequestException as e:
            raise RuntimeError(f"Could not connect to Sonar 3D-15 at {ip}:{port}") from e
        self.sonar_version = about.version_short

        min_version = "1.5.1"
        if _semver_is_less_than(self.sonar_version, min_version):
            raise VersionException("Sonar3D client", min_version, self.sonar_version)

    ############################################################################
    # HTTP helpers
    ############################################################################
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get_json(self, path: str) -> Json:
        """GET JSON.

        Get JSON does a GET and raises exception on non-2xx status code. If response contains no
        content, it returns None. If response contains content, it is returned.
        """
        r = requests.get(self._url(path), timeout=self.timeout)
        r.raise_for_status()
        # Some endpoints return 204 No Content
        if r.status_code == 204 or not r.content:
            return None
        return cast(Json, r.json())

    def _post_json(self, path: str, json_payload: Json) -> Json:
        """POST JSON.

        _post_json posts the given JSON payload to path and raises exception on non-2xx status code.
        If response contains no content, it returns None. If response contains content, it is
        returned.
        """
        r = requests.post(self._url(path), json=json_payload, timeout=self.timeout)
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return None
        return cast(Json, r.json())

    ############################################################################
    # HTTP API
    ############################################################################

    def about(self) -> About:
        """Get system version/info.

        Returns:
            About: about information.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/about")
        if not isinstance(resp, dict):
            raise ValueError("about endpoint gave unexpected response")
        try:
            # check presence and type of expected fields
            if not (
                isinstance(resp["version"], str)
                and isinstance(resp["version_short"], str)
                and isinstance(resp["chipid"], str)
                and isinstance(resp["product_name"], str)
                and isinstance(resp["hardware_revision"], int)
                and isinstance(resp["product_id"], int)
                and isinstance(resp["variant"], str)
                and isinstance(resp["is_ready"], bool)
            ):
                raise RuntimeError("about endpoint gave unexpected response")
            about = About(
                chipid=resp["chipid"],
                hardware_revision=resp["hardware_revision"],
                is_ready=resp["is_ready"],
                product_id=resp["product_id"],
                product_name=resp["product_name"],
                variant=resp["variant"],
                version=resp["version"],
                version_short=resp["version_short"],
            )
        except KeyError as e:
            raise ValueError(f"about endpoint missing expected field: {e}") from e
        return about

    def get_status(self) -> Status:
        """Get system status.

        Requires:
            Sonar 3D-15 release 1.7.0 or higher.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support this method.
        """
        min_version = "1.7.0"
        if _semver_is_less_than(self.sonar_version, min_version):
            # see release notes of sonar release 1.7.0 for context
            raise VersionException("Sonar3D client .get_status", min_version, self.sonar_version)

        resp = self._get_json("/api/v1/integration/status")
        if not isinstance(resp, dict):
            raise ValueError("status endpoint gave unexpected response")
        try:
            # check presence and type of expected fields
            if not (
                isinstance(resp["api"], dict)
                and isinstance(resp["api"]["id"], str)
                and isinstance(resp["api"]["message"], str)
                and isinstance(resp["api"]["operational"], bool)
                and isinstance(resp["api"]["status"], str)
                and isinstance(resp["temperature"], dict)
                and isinstance(resp["temperature"]["id"], str)
                and isinstance(resp["temperature"]["message"], str)
                and isinstance(resp["temperature"]["operational"], bool)
                and isinstance(resp["temperature"]["status"], str)
                and isinstance(resp["systems_check"], dict)
                and isinstance(resp["systems_check"]["id"], str)
                and isinstance(resp["systems_check"]["message"], str)
                and isinstance(resp["systems_check"]["operational"], bool)
                and isinstance(resp["systems_check"]["status"], str)
            ):
                raise RuntimeError("status endpoint gave unexpected response")
            status = Status(
                api=StatusEntry(
                    id=resp["api"]["id"],
                    message=resp["api"]["message"],
                    operational=resp["api"]["operational"],
                    status=resp["api"]["status"],
                ),
                temperature=StatusEntry(
                    id=resp["temperature"]["id"],
                    message=resp["temperature"]["message"],
                    operational=resp["temperature"]["operational"],
                    status=resp["temperature"]["status"],
                ),
                systems_check=StatusEntry(
                    id=resp["systems_check"]["id"],
                    message=resp["systems_check"]["message"],
                    operational=resp["systems_check"]["operational"],
                    status=resp["systems_check"]["status"],
                ),
            )
        except KeyError as e:
            raise ValueError(f"status endpoint missing expected field: {e}") from e
        return status

    def get_temperature(self) -> float:
        """Get internal temperature (°C).

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/temperature")
        if not isinstance(resp, float):
            raise ValueError("temperature endpoint gave unexpected response")
        return resp

    def get_acoustics_enabled(self) -> bool:
        """Get whether acoustics is enabled.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/acoustics/enabled")
        if not isinstance(resp, bool):
            raise ValueError("get_acoustics_enabled endpoint gave unexpected response")
        return resp

    def set_acoustics_enabled(self, enabled: bool) -> None:
        """Enable/disable acoustic imaging.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self._post_json("/api/v1/integration/acoustics/enabled", enabled)

    def get_range(self) -> tuple[float, float]:
        """Get range payload (min, max) in meters.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/acoustics/range")
        if not isinstance(resp, dict):
            raise ValueError("get_range endpoint gave unexpected response")
        if not (isinstance(resp["min"], (int, float)) and isinstance(resp["max"], (int, float))):
            raise ValueError("get_range endpoint gave unexpected response")
        range_min, range_max = resp["min"], resp["max"]
        return float(range_min), float(range_max)

    def set_range(self, range_min: float, range_max: float) -> None:
        """Set range.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self._post_json(
            "/api/v1/integration/acoustics/range",
            {"min": float(range_min), "max": float(range_max)},
        )

    def get_speed_of_sound(self) -> float:
        """Get configured speed of sound (m/s).

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/acoustics/speed_of_sound")
        if not isinstance(resp, (int, float)):
            raise ValueError("get_speed_of_sound endpoint gave unexpected response")
        return float(resp)

    def set_speed_of_sound(self, speed: float) -> None:
        """Set speed of sound (m/s).

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self._post_json("/api/v1/integration/acoustics/speed_of_sound", float(speed))

    def get_udp_config(self) -> UdpConfig:
        """Get UDP output configuration.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        resp = self._get_json("/api/v1/integration/udp")
        if not isinstance(resp, dict):
            raise ValueError("get_udp_config endpoint gave unexpected response")
        return UdpConfig.from_json(resp)

    def set_udp_config(self, cfg: UdpConfig) -> None:
        """Set UDP output configuration.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self._post_json("/api/v1/integration/udp", cfg.to_json())

    def get_mode(self) -> Literal["low-frequency", "high-frequency"]:
        """Get sonar mode.

        Requires:
            Sonar 3D-15 release 1.7.0 or higher.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support this method.
        """
        min_version = "1.7.0"
        if _semver_is_less_than(self.sonar_version, min_version):
            raise VersionException("Sonar3D client .get_mode", min_version, self.sonar_version)
        resp = self._get_json("/api/v1/integration/acoustics/mode")
        if not isinstance(resp, str):
            raise ValueError("get_mode endpoint gave unexpected response")
        if resp == "low-frequency":
            return "low-frequency"
        if resp == "high-frequency":
            return "high-frequency"
        raise ValueError("get_mode endpoint gave unexpected string")

    def set_mode(self, mode: Literal["low-frequency", "high-frequency"]) -> None:
        """Set sonar mode.

        Requires:
            Sonar 3D-15 release 1.7.0 or higher.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support this method.
        """
        min_version = "1.7.0"
        if _semver_is_less_than(self.sonar_version, min_version):
            raise VersionException("Sonar3D client .set_mode", min_version, self.sonar_version)
        if mode == "low-frequency":
            self._post_json("/api/v1/integration/acoustics/mode", "low-frequency")
        elif mode == "high-frequency":
            self._post_json("/api/v1/integration/acoustics/mode", "high-frequency")
        else:
            raise ValueError(f"set_mode got invalid mode: {mode}")

    def get_salinity(self) -> Literal["salt", "fresh"]:
        """Get configured salinity for automatic speed of sound calculation.

        Requires:
            Sonar 3D-15 release 1.7.0 or higher.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support this method.
        """
        min_version = "1.7.0"
        if _semver_is_less_than(self.sonar_version, min_version):
            raise VersionException("Sonar3D client .get_salinity", min_version, self.sonar_version)
        resp = self._get_json("/api/v1/integration/acoustics/salinity")
        if not isinstance(resp, str):
            raise ValueError("get_salinity endpoint gave unexpected response")
        if resp == "salt":
            return "salt"
        if resp == "fresh":
            return "fresh"
        raise ValueError("get_salinity endpoint gave unexpected string")

    def set_salinity(self, mode: Literal["salt", "fresh"]) -> None:
        """Set salinity for automatic speed of sound calculation.

        Requires:
            Sonar 3D-15 release 1.7.0 or higher.

        Raises:
            requests.RequestException: on HTTP or connection error.
            VersionException: if sonar version is too old to support this method.
        """
        min_version = "1.7.0"
        if _semver_is_less_than(self.sonar_version, min_version):
            raise VersionException("Sonar3D client .set_salinity", min_version, self.sonar_version)
        if mode == "salt":
            self._post_json("/api/v1/integration/acoustics/salinity", "salt")
        elif mode == "fresh":
            self._post_json("/api/v1/integration/acoustics/salinity", "fresh")
        else:
            raise ValueError(f"set_salinity got invalid mode: {mode}")

    ################################################################################################
    # Convenience methods
    ################################################################################################

    def set_udp_multicast(self) -> None:
        """Convenience: set UDP output to multicast.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self.set_udp_config(UdpConfig(mode="multicast"))

    def set_udp_disabled(self) -> None:
        """Convenience: disable UDP output.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self.set_udp_config(UdpConfig(mode="disabled"))

    def set_udp_unicast(self, ip: str, port: int) -> None:
        """Convenience: set UDP output to unicast destination.

        Raises:
            requests.RequestException: on HTTP or connection error.
        """
        self.set_udp_config(
            UdpConfig(mode="unicast", unicast_destination_ip=ip, unicast_destination_port=int(port))
        )
