# Development and testing

[`uv`](https://docs.astral.sh/uv/) is required for development of the package. Run the following to set up the project:

```bash
uv sync
```

## Examples

To run the example code with a locally edited version of wlsonar, use: `uv run --with-editable . examples/trim_recording.py`.

## Linting

The package is linted with `ruff` and `mypy`:

```bash
uv run ruff check
uv run ruff format --diff
uv run mypy . --exclude examples
```

## Testing

The package is tested with pytest:

```bash
uv run pytest
```

There are also end-to-end (e2e) tests to verify the package against a real Sonar 3D-15. Make sure to read the documentation of [tests/test_e2e_real_sonar.py](tests/test_e2e_real_sonar.py), then run the e2e test with:

```bash
uv run pytest -m e2e -s --sonar-ip <sonar ip>
```

## Versioning

Versioning is handled with `uv`. Setting a new version with `uv version <new version>` and merging to master will build a new version on pypi. We follow semantic versioning.

## Protobuf

The Sonar 3D-15 uses a .proto file to define message formats. wlsonar includes generated Python for these messages using protoc.

The version of protoc used to generate code should match the Python protobuf package requirement in pyproject.toml.
At the time of writing the Python protobuf dependency is `>=6.33.2,<7`, meaning the protoc compiler should be 33.2.

Install 33.2 here: https://github.com/protocolbuffers/protobuf/releases/tag/v33.2

There is a pipeline check to assert that the generated code matches the expected protoc version.

> [!IMPORTANT]
> If the Python library in pyproject.toml is updated, this section should be updated also.

When changing the .proto file, run the following to generate new Python code:

```bash
uv run protoc \
    --proto_path=src/wlsonar/range_image_protocol/_proto/ \
    --python_out=src/wlsonar/range_image_protocol/_proto/ \
    --mypy_out=src/wlsonar/range_image_protocol/_proto/  \
    src/wlsonar/range_image_protocol/_proto/WaterLinkedSonarIntegrationProtocol.proto
```
