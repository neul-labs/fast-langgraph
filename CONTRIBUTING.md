# Contributing to LangGraph Rust Implementation

We welcome contributions to the LangGraph Rust Implementation! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/langgraph-rs.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature/your-feature-name`
7. Create a new Pull Request

## Development Setup

### Prerequisites

- Rust toolchain (install with [rustup](https://rustup.rs/))
- Python 3.8 or higher
- pip

### Setup

1. Install Rust toolchain:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source $HOME/.cargo/env
   ```

2. Install Python dependencies:
   ```bash
   pip install -e .[dev]
   ```

## Code Organization

- `src/` - Rust source code
- `python/` - Python package structure
- `tests/` - Test suite
- `examples/` - Example code
- `benches/` - Performance benchmarks

## Rust Code Style

We follow the Rust community coding standards. Before submitting code, please run:

```bash
cargo fmt  # Format code
cargo clippy  # Lint code
```

## Python Code Style

We use ruff for Python code formatting and linting:

```bash
ruff check .  # Check for issues
ruff format .  # Format code
```

## Testing

All contributions should include appropriate tests. Run tests with:

```bash
# Run Python tests
python -m pytest tests/

# Run Rust tests
cargo test
```

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build
2. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you

## Reporting Issues

Please use the GitHub issue tracker to report bugs or suggest features.

When reporting a bug, please include:
- A clear and descriptive title
- A detailed description of the problem
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Any relevant error messages
- Your environment information (OS, Rust version, Python version, etc.)

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

If you have any questions, please open an issue or contact the maintainers.