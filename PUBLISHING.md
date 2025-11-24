# Publishing to PyPI

This guide covers how to build and publish Fast LangGraph to PyPI.

## Prerequisites

1. **Rust toolchain** (1.70+)
2. **Python** (3.8+)
3. **Poetry** for dependency management
4. **Maturin** for building Rust extensions
5. **PyPI account** and API token

## Setup

### 1. Install Dependencies

```bash
# Install poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install --with build

# Verify maturin is available
poetry run maturin --version
```

### 2. Configure PyPI Credentials

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-API-TOKEN-HERE
```

Or use environment variables:
```bash
export MATURIN_PYPI_TOKEN=pypi-YOUR-API-TOKEN-HERE
```

## Building

### Development Build

For local testing and development:

```bash
# Build and install in development mode
poetry run maturin develop

# Or with release optimizations
poetry run maturin develop --release
```

### Production Build

Build wheel files for distribution:

```bash
# Build for current platform
poetry run maturin build --release

# Build for multiple Python versions
poetry run maturin build --release --interpreter python3.8 python3.9 python3.10 python3.11 python3.12

# Wheels will be in target/wheels/
ls -lh target/wheels/
```

## Testing the Build

### Test Locally

```bash
# Install the built wheel
pip install target/wheels/fast_langgraph-0.1.0-*.whl

# Test import
python -c "import fast_langgraph; print(fast_langgraph.is_rust_available())"

# Run examples
python examples/simple_test.py
```

### Test on TestPyPI

```bash
# Publish to TestPyPI first
poetry run maturin publish --repository testpypi

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ fast-langgraph

# Test the installation
python -c "import fast_langgraph; print(fast_langgraph.__version__)"
```

## Publishing to PyPI

### Pre-flight Checklist

- [ ] Version number updated in `pyproject.toml` and `Cargo.toml`
- [ ] CHANGELOG.md updated with release notes
- [ ] All tests passing: `poetry run pytest`
- [ ] Documentation up to date
- [ ] README.md reviewed
- [ ] Git tag created: `git tag v0.1.0 && git push origin v0.1.0`

### Publish

```bash
# Build and publish in one command
poetry run maturin publish

# Or build first, then publish
poetry run maturin build --release
poetry run maturin upload target/wheels/*
```

### Verify Publication

```bash
# Wait a few minutes, then install from PyPI
pip install fast-langgraph

# Verify installation
python -c "import fast_langgraph; print(fast_langgraph.__version__)"
```

## Multi-Platform Builds

For maximum compatibility, build for multiple platforms using GitHub Actions or local cross-compilation:

### Using GitHub Actions (Recommended)

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  release:
    types: [created]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - uses: messense/maturin-action@v1
        with:
          command: build
          args: --release --out dist
      - uses: actions/upload-artifact@v3
        with:
          name: wheels
          path: dist

  publish:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
        with:
          name: wheels
          path: dist
      - uses: messense/maturin-action@v1
        with:
          command: upload
          args: --skip-existing dist/*
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

## Version Management

### Updating Version

Update version in both files:

1. `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. `Cargo.toml`:
   ```toml
   version = "0.2.0"
   ```

3. Update `CHANGELOG.md` with release notes

4. Create git tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

## Troubleshooting

### Build Fails

- Ensure Rust toolchain is up to date: `rustup update`
- Clear target directory: `cargo clean`
- Check Python version compatibility

### Import Errors After Install

- Verify the wheel was built for the correct platform
- Check Python version matches wheel metadata
- Try reinstalling: `pip uninstall fast-langgraph && pip install fast-langgraph`

### Publishing Errors

- Verify API token is correct
- Check package name is not already taken
- Ensure version number is incremented

## Resources

- [Maturin Documentation](https://maturin.rs/)
- [PyPI Publishing Guide](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [PyO3 Guide](https://pyo3.rs/)
