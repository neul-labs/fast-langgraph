# Test Scripts

This directory contains scripts for testing Fast LangGraph compatibility and functionality.

## Scripts

### `test_compatibility.py`

**Primary compatibility testing tool** - Cross-platform Python script that:

- Clones LangGraph repository
- Installs LangGraph with dependencies
- Builds and installs Fast LangGraph
- Applies the shim to replace Python implementations
- Runs LangGraph's complete test suite
- Reports compatibility results

**Usage**:
```bash
# Basic usage
python scripts/test_compatibility.py

# Test against specific branch
python scripts/test_compatibility.py --branch v0.2.0

# Keep test directory for debugging
python scripts/test_compatibility.py --keep

# Verbose output
python scripts/test_compatibility.py -v

# Pass pytest options
python scripts/test_compatibility.py -- -k test_channels -x
```

**Options**:
- `--repo URL`: LangGraph repository URL
- `--branch NAME`: Branch to test against (default: main)
- `--test-dir PATH`: Custom test directory
- `--keep`: Keep test directory after completion
- `-v, --verbose`: Verbose output
- `pytest_args`: Additional arguments for pytest

### `test_langgraph_compatibility.sh`

**Bash version** of the compatibility test (Linux/macOS only).

Same functionality as `test_compatibility.py` but in bash.

**Usage**:
```bash
./scripts/test_langgraph_compatibility.sh

# With options
LANGGRAPH_BRANCH=v0.2.0 ./scripts/test_langgraph_compatibility.sh
KEEP_TEST_DIR=1 ./scripts/test_langgraph_compatibility.sh
TEST_OPTIONS="-k test_channels" ./scripts/test_langgraph_compatibility.sh
```

**Environment Variables**:
- `LANGGRAPH_BRANCH`: Branch to test against
- `KEEP_TEST_DIR`: Set to 1 to keep test directory
- `TEST_OPTIONS`: Pytest options (default: "-v -x")

## How It Works

The compatibility testing process:

```
┌─────────────────────────────────────────┐
│  1. Setup Test Environment              │
│     - Create temporary directory        │
│     - Create virtual environment        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. Clone LangGraph                     │
│     - Clone from official repo          │
│     - Checkout specified branch         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. Install Dependencies                │
│     - Install LangGraph + test deps     │
│     - Build Fast LangGraph with maturin │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. Create Test Runner                  │
│     - Script that applies shim          │
│     - Then runs pytest                  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5. Apply Shim & Run Tests              │
│     - Import fast_langgraph             │
│     - Call shim.patch_langgraph()       │
│     - Run LangGraph's test suite        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  6. Report Results                      │
│     - Show patched components           │
│     - Display test results              │
│     - Cleanup (or keep for debugging)   │
└─────────────────────────────────────────┘
```

## Examples

### Test against main branch

```bash
python scripts/test_compatibility.py
```

### Test against specific version

```bash
python scripts/test_compatibility.py --branch v0.2.5
```

### Debug failing tests

```bash
# Keep test directory
python scripts/test_compatibility.py --keep

# Navigate to test environment
cd .langgraph-test
source venv/bin/activate
cd langgraph

# Run specific test
python ../run_tests.py tests/test_failing.py -v

# Or without shim
FAST_LANGGRAPH_AUTO_PATCH=0 pytest tests/test_failing.py
```

### Run subset of tests

```bash
# Only run channel tests
python scripts/test_compatibility.py -- -k test_channels

# Stop on first failure, verbose
python scripts/test_compatibility.py -- -x -v

# Run with coverage
python scripts/test_compatibility.py -- --cov=langgraph
```

### Test against a fork

```bash
python scripts/test_compatibility.py \
  --repo https://github.com/your-username/langgraph.git \
  --branch feature-branch
```

## Interpreting Results

### Success

```
[✓] All tests passed! ✨

╔══════════════════════════════════════════════════════════╗
║  Fast LangGraph is fully compatible with LangGraph! 🎉  ║
╚══════════════════════════════════════════════════════════╝
```

All LangGraph tests pass with Fast LangGraph shim applied!

### Failure

```
[✗] Some tests failed

⚠ This may indicate compatibility issues or differences in behavior
⚠ Review the test output above for details
```

Possible reasons:
1. **API Changes**: LangGraph API changed since last update
2. **Missing Implementation**: Feature not yet implemented in Rust
3. **Behavior Difference**: Edge case handling differs
4. **Test Environment**: Issue with test setup

### Debugging Steps

1. Check which tests failed
2. Look for error messages
3. Keep test directory: `--keep`
4. Run failing test in isolation
5. Compare with unpatched version
6. Check patched components list

## CI/CD Integration

These scripts are used in GitHub Actions:

- **`.github/workflows/compatibility-tests.yml`**: Runs daily
- Tests against LangGraph main branch
- Tests on multiple OS/Python versions
- Creates issue on failure

## Requirements

- Python 3.8+
- Git
- Rust toolchain
- Poetry (recommended) or pip + maturin

## Troubleshooting

### "Maturin not found"

```bash
pip install maturin
# or
poetry install --with build
```

### "Permission denied"

```bash
chmod +x scripts/test_compatibility.py
chmod +x scripts/test_langgraph_compatibility.sh
```

### "Virtual environment issues"

```bash
# Clean and retry
rm -rf .langgraph-test
python scripts/test_compatibility.py
```

### "LangGraph clone fails"

```bash
# Check network connection
# Or use specific branch that exists
python scripts/test_compatibility.py --branch v0.2.0
```

## See Also

- **[TESTING.md](../TESTING.md)**: Complete testing guide
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Development guide
- **[.github/workflows/](../.github/workflows/)**: CI/CD workflows
