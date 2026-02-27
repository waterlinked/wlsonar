from typing import Literal, cast

import pytest

from wlsonar import Sonar3D, UdpConfig, VersionException
from wlsonar._semver import _semver_is_less_than


@pytest.mark.e2e
def test_e2e_Sonar3D_client_against_real_sonar(request: pytest.FixtureRequest) -> None:
    """
    Test the Sonar3D client against a real Sonar 3D-15.

    Requirements:
    - The test requires the --sonar-ip command line argument to be set to the IP of a real sonar.

    In the event of test failure, the Sonar may be left in an unknown state. Consider factory
    resetting on failure (through the GUI).

    The goal of the test is only to verify that the client can communicate successfully with a real
    sonar through its HTTP API. It does not test the sonar itself. For example, it tests that we can
    enable acoustics, but does not test that this causes the sonar to actually start producing sonar
    images.

    Example use:
        uv run pytest -s -m e2e --sonar-ip 10.1.2.156
    """
    sonar_ip = request.config.getoption("--sonar-ip")
    assert sonar_ip is not None and isinstance(sonar_ip, str), (
        "This test requires --sonar-ip to be set."
    )
    print(f"Testing wlsonar package against real sonar with IP address: '{sonar_ip}'")

    ################################################################################################
    # setup sonar
    ################################################################################################
    sonar = Sonar3D(sonar_ip)

    print(f"Sonar under test is release version: {sonar.sonar_version}")

    ################################################################################################
    # about, status, temperature
    ################################################################################################

    about = sonar.about()
    print("Sonar about:", about)

    if _semver_is_less_than(about.version_short, "1.7.0"):
        with pytest.raises(VersionException):
            sonar.get_status()
        print(
            f"Sonar release {sonar.sonar_version} does not support .get_status. "
            "Got expected VersionException."
        )
    else:
        status = sonar.get_status()
        print("Sonar status:", status)

    temperature = sonar.get_temperature()
    print(f"Sonar temperature: {temperature:.2f} °C")

    ################################################################################################
    # acoustics enabled toggle test
    ################################################################################################

    had_acoustics_enabled = sonar.get_acoustics_enabled()
    print(f"Sonar acoustics enabled: {had_acoustics_enabled}")

    # try toggling acoustics
    sonar.set_acoustics_enabled(not had_acoustics_enabled)
    assert sonar.get_acoustics_enabled() == (not had_acoustics_enabled), (
        "Failed to toggle acoustics enabled state"
    )
    acoustics_after_toggle = sonar.get_acoustics_enabled()
    print(f"Toggled sonar acoustics enabled to: {acoustics_after_toggle}")
    sonar.set_acoustics_enabled(had_acoustics_enabled)
    assert sonar.get_acoustics_enabled() == had_acoustics_enabled, (
        "Failed to toggle acoustics enabled state back"
    )
    acoustics_after_toggle_back = sonar.get_acoustics_enabled()
    print(f"Toggled sonar acoustics enabled back to: {acoustics_after_toggle_back}")

    ################################################################################################
    # range
    ################################################################################################

    had_range_min, had_range_max = sonar.get_range()
    print(f"Sonar range: {had_range_min} to {had_range_max} meters")

    # try changing range
    new_range_min = 2.0
    new_range_max = 3.0
    sonar.set_range(new_range_min, new_range_max)
    set_range_min, set_range_max = sonar.get_range()
    print(f"Sonar range after change: {set_range_min} to {set_range_max} meters")
    assert set_range_min == new_range_min and set_range_max == new_range_max, (
        "Failed to set sonar range"
    )

    # set range back
    sonar.set_range(had_range_min, had_range_max)
    reset_range_min, reset_range_max = sonar.get_range()
    print(f"Sonar range after resetting: {reset_range_min} to {reset_range_max} meters")
    assert reset_range_min == had_range_min and reset_range_max == had_range_max, (
        "Failed to reset sonar range",
    )

    ####################################################################################################
    # speed of sound
    ####################################################################################################

    speed_of_sound = sonar.get_speed_of_sound()
    print(f"Sonar speed of sound: {speed_of_sound} m/s")

    # try changing speed of sound
    new_speed_of_sound = 1442.0
    sonar.set_speed_of_sound(new_speed_of_sound)
    set_speed_of_sound = sonar.get_speed_of_sound()
    print(f"Sonar speed of sound after change: {set_speed_of_sound} m/s")
    assert set_speed_of_sound == new_speed_of_sound, "Failed to set sonar speed of sound"

    # set speed of sound back
    sonar.set_speed_of_sound(speed_of_sound)
    reset_speed_of_sound = sonar.get_speed_of_sound()
    print(f"Sonar speed of sound after resetting: {reset_speed_of_sound} m/s")
    assert reset_speed_of_sound == speed_of_sound, "Failed to reset sonar speed of sound"

    ####################################################################################################
    # UDP config
    ####################################################################################################

    existing_udp_config = sonar.get_udp_config()
    print("Existing Sonar UDP config:", existing_udp_config)

    # try changing UDP config using the different methods that are provided

    # with set_udp_config
    req = UdpConfig(
        mode="unicast",
        unicast_destination_ip="192.168.99.42",
        unicast_destination_port=4748,
    )
    sonar.set_udp_config(req)
    udp_config_after_set = sonar.get_udp_config()
    print("Sonar UDP config after set_udp_config:", udp_config_after_set)
    assert udp_config_after_set == req, "Failed to set UDP config with set_udp_config"

    # with set_udp_multicast
    sonar.set_udp_multicast()
    udp_config_after_multicast = sonar.get_udp_config()
    print("Sonar UDP config after set_udp_multicast:", udp_config_after_multicast)
    assert udp_config_after_multicast.mode == "multicast", (
        "Failed to set UDP config to multicast with set_udp_multicast"
    )

    # with set_udp_unicast
    dest_ip = "192.168.99.43"
    dest_port = 4749
    sonar.set_udp_unicast(dest_ip, dest_port)
    udp_config_after_unicast = sonar.get_udp_config()
    print("Sonar UDP config after set_udp_unicast:", udp_config_after_unicast)
    assert (
        udp_config_after_unicast.mode == "unicast"
        and udp_config_after_unicast.unicast_destination_ip == dest_ip
        and udp_config_after_unicast.unicast_destination_port == dest_port
    ), "Failed to set UDP config to unicast with set_udp_unicast"

    # set UDP config back
    sonar.set_udp_config(existing_udp_config)
    reset_udp_config = sonar.get_udp_config()
    print("Sonar UDP config after resetting:", reset_udp_config)
    assert reset_udp_config == existing_udp_config, "Failed to reset UDP config"

    ################################################################################################
    # mode
    ################################################################################################

    if _semver_is_less_than(sonar.sonar_version, "1.7.0"):
        with pytest.raises(VersionException):
            sonar.get_mode()
        print(
            f"Sonar release {sonar.sonar_version} does not support .get_mode. "
            "Got expected VersionException."
        )
        with pytest.raises(VersionException):
            sonar.set_mode("low-frequency")
        print(
            f"Sonar release {sonar.sonar_version} does not support .set_mode. "
            "Got expected VersionException."
        )
    else:
        had_mode = sonar.get_mode()
        print(f"Sonar mode: {had_mode}")

        # try toggling mode

        # determine the mode we are not currently using
        other_mode = "high-frequency" if had_mode == "low-frequency" else "low-frequency"
        # cast: make type checker happy
        other_mode = cast(Literal["low-frequency", "high-frequency"], other_mode)

        sonar.set_mode(other_mode)
        mode_after_toggle = sonar.get_mode()
        print(f"Toggled sonar mode to: {mode_after_toggle}")
        assert mode_after_toggle == other_mode, "Failed to toggle mode"
        sonar.set_mode(had_mode)
        mode_after_toggle_back = sonar.get_mode()
        print(f"Toggled sonar mode back to: {mode_after_toggle_back}")
        assert mode_after_toggle_back == had_mode, "Failed to toggle mode back"

    ####################################################################################################
    # salinity
    ####################################################################################################

    if _semver_is_less_than(sonar.sonar_version, "1.7.0"):
        with pytest.raises(VersionException):
            sonar.get_salinity()
        print(
            f"Sonar release {sonar.sonar_version} does not support .get_salinity. "
            "Got expected VersionException."
        )
        with pytest.raises(VersionException):
            sonar.set_salinity("salt")
        print(
            f"Sonar release {sonar.sonar_version} does not support .set_salinity. "
            "Got expected VersionException."
        )
    else:
        had_salinity = sonar.get_salinity()
        print(f"Sonar salinity: {had_salinity}")

        # toggle salinity type

        # determine the salinity we are not currently using
        other_salinity = "salt" if had_salinity == "fresh" else "fresh"
        other_salinity = cast(Literal["salt", "fresh"], other_salinity)  # make type checker happy

        sonar.set_salinity(other_salinity)
        salinity_after_toggle = sonar.get_salinity()
        print(f"Toggled salinity to: {salinity_after_toggle}")
        assert salinity_after_toggle == other_salinity, "Failed to toggle salinity"
        sonar.set_salinity(had_salinity)
        salinity_after_toggle_back = sonar.get_salinity()
        print(f"Toggled salinity back to: {salinity_after_toggle_back}")
        assert salinity_after_toggle_back == had_salinity, "Failed to toggle salinity back"

    print("Sonar3D client tested against real sonar: all checks passed.")
