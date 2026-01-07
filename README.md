# wlsonar

Package wlsonar is a python client library for the Water Linked [Sonar 3D-15](https://www.waterlinked.com/shop/wl-21045-2-sonar-3d-15-689).

The key features of this package are:

- `wlsonar.Sonar3D` for configuration and inspection of system state.
- `wlsonar.range_image_protocol` for [Range Image Protocol](https://docs.waterlinked.com/sonar-3d/sonar-3d-15-api/#range-image-protocol-rip2) packets.

## Installation 

The wlsonar package is hosted on pypi and can be installed with pip:

```bash
pip install wlsonar
```

## Quickstart

Following is a snippet showing how to connect to the sonar and receive images.

```python
import wlsonar
import wlsonar.range_image_protocol as rip

# (set to your sonar's IP address
ip = "10.1.2.24"

# connect, enable acoustics, configure to send images over UDP multicast
sonar = wlsonar.Sonar3D(ip)
sonar.set_acoustics_enabled(True)
sonar.set_udp_multicast()

print("Sonar configured, listening for UDP packets...")

# receive UDP packets, parse them into protobuf, and extract voxels
sock = wlsonar.open_sonar_udp_socket()
try:
    while True:
        packet, _ = sock.recvfrom(wlsonar.UDP_MAX_DATAGRAM_SIZE)
        try:
            msg = rip.unpackb(packet)
        except rip.UnknownProtobufTypeError:
            continue
        if isinstance(msg, rip.RangeImage):
            xyz = wlsonar.range_image_to_xyz(msg)
            id = msg.header.sequence_id
            print(f"Got range image {id} with {len(xyz)} voxels")
finally:
    sock.close()
```

More elaborate examples can be found in [the examples folder](./examples/).

## Documentation and resources

Documentation for this package is provided in the form of:

- Elaborate examples in [the examples folder](./examples/).
- Tests in [the tests folder](./tests).
- Docstrings in code.

For general documentation about the Sonar 3D-15 see: https://docs.waterlinked.com/sonar-3d/sonar-3d-15/. The integration API that this package interfaces with is documented here: https://docs.waterlinked.com/sonar-3d/sonar-3d-15-api/. See also the replayer: https://sonar.replay.waterlinked.com/.

## Development and testing

`uv` is required for development of the package. Run the following to set up the project:

```bash
uv sync
```

### Linting

The package is linted with `ruff` and `mypy`:

```bash
uv run ruff check
uv run ruff format --diff
uv run mypy .
```

### Testing

The package is tested with pytest:

```bash
uv run pytest
```

There are also end-to-end (e2e) tests to verify the package against a real Sonar 3D-15. Make sure to read the documentation of [tests/test_e2e_real_sonar.py](tests/test_e2e_real_sonar.py), then run the e2e test with:

```bash
uv run pytest -m e2e -s --sonar-ip <sonar ip>
```

### Versioning

Versioning is handled with `uv`. Setting a new version with `uv version <new version>` and merging to master will build a new version on pypi. We follow semantic versioning.

### Protobuf

The Sonar 3D-15 uses a .proto file to define message formats. This package includes generated Python for these messages. When changing the .proto file, run the following to generate new Python code:

```bash
uv run protoc \
    --proto_path=src/wlsonar/range_image_protocol/_proto/ \
    --python_out=src/wlsonar/range_image_protocol/_proto/ \
    --mypy_out=src/wlsonar/range_image_protocol/_proto/  \
    src/wlsonar/range_image_protocol/_proto/WaterLinkedSonarIntegrationProtocol.proto
```