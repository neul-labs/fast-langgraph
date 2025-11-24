# Contributing to Fast LangGraph

We welcome contributions to Fast LangGraph! This document provides guidelines for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Rust**: 1.70 or later
- **Python**: 3.8 or later with development headers
- **Git**: For version control
- **GitHub Account**: For submitting pull requests

### Areas for Contribution

We welcome contributions in these areas:

- **Performance Improvements**: Optimizing existing implementations
- **New Features**: Adding new channel types, checkpoint formats, etc.
- **Bug Fixes**: Resolving issues and edge cases
- **Documentation**: Improving guides, examples, and API docs
- **Testing**: Adding test coverage and benchmarks
- **Examples**: Creating usage examples and tutorials

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/fast-langgraph.git
cd fast-langgraph

# Add upstream remote
git remote add upstream https://github.com/neul-labs/fast-langgraph.git
```

### 2. Set Up Development Environment

```bash
# Install Rust if not already installed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install all dependencies including dev dependencies
poetry install --with dev,docs,test

# Build the Rust extension
poetry run maturin develop

# Activate the virtual environment (optional, Poetry handles this)
poetry shell
```

### 3. Verify Setup

```bash
# Run Rust tests
cargo test --no-default-features

# Run Python tests
poetry run pytest tests/

# Run basic functionality test
poetry run python examples/simple_test.py

# Format and lint code
poetry run black langgraph_rs/ tests/
poetry run ruff check langgraph_rs/
```

## Making Changes

### 1. Create a Branch

```bash
# Stay up to date with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 2. Development Guidelines

#### Code Organization

- **Rust Code**: Place in `src/` directory
- **Python Code**: Place in `langgraph_rs/` directory
- **Tests**: Add to `tests/` directory
- **Examples**: Add to `examples/` directory
- **Documentation**: Add to `docs/` directory

#### Rust Guidelines

- Follow Rust conventions and idioms
- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting
- Add comprehensive error handling
- Include documentation comments (`///`)

```rust
/// Updates the channel with new values.
///
/// # Arguments
///
/// * `values` - Vector of values to update with
///
/// # Returns
///
/// * `Result<bool, LangGraphError>` - True if update was successful
///
/// # Errors
///
/// Returns `LangGraphError::InvalidUpdate` if values are invalid.
pub fn update(&mut self, values: Vec<T>) -> Result<bool, LangGraphError> {
    // Implementation
}
```

#### Python Guidelines

- Follow PEP 8 style guide
- Use type hints
- Add docstrings for all public functions
- Handle errors gracefully

```python
def patch_langgraph() -> bool:
    """
    Patch LangGraph with Rust implementations.

    Returns:
        bool: True if patching was successful, False otherwise.

    Raises:
        ImportError: If Rust implementations are not available.
    """
    # Implementation
```

### 3. Adding Features

#### New Channel Types

1. Add Rust implementation in `src/channels.rs`
2. Add Python binding in `src/python.rs`
3. Export in `src/lib.rs`
4. Add to Python `__init__.py`
5. Add tests in both Rust and Python
6. Update documentation

#### New Checkpoint Formats

1. Add implementation in `src/checkpoint.rs`
2. Add feature flag if needed in `Cargo.toml`
3. Add Python bindings
4. Add tests and benchmarks
5. Update documentation

## Testing

### Running Tests

```bash
# Run all Rust tests
cargo test

# Run Rust tests without Python features
cargo test --no-default-features

# Run Python tests
poetry run pytest tests/

# Run with coverage
poetry run pytest --cov=langgraph_rs tests/

# Run specific test groups
poetry run pytest -m "not slow"  # Skip slow tests
poetry run pytest -m integration  # Only integration tests

# Run benchmarks
cargo bench

# Run Python linting and formatting
poetry run black langgraph_rs/ tests/
poetry run ruff check langgraph_rs/
poetry run mypy langgraph_rs/
```

### Test Requirements

#### For Bug Fixes
- Add regression test that reproduces the bug
- Verify the test fails before the fix
- Verify the test passes after the fix

#### For New Features
- Add unit tests for all public functions
- Add integration tests for complex features
- Add benchmarks for performance-critical code
- Test error conditions and edge cases

#### Test Structure

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_channel_update() {
        let mut channel = LastValueChannel::new();
        assert!(!channel.is_available());

        let result = channel.update(vec!["test".to_string()]);
        assert!(result.is_ok());
        assert!(channel.is_available());
        assert_eq!(channel.get().unwrap(), "test");
    }

    #[test]
    fn test_invalid_update() {
        let mut channel = LastValueChannel::new();
        let result = channel.update(vec!["a".to_string(), "b".to_string()]);
        assert!(result.is_err());
    }
}
```

```python
import pytest
import langgraph_rs

def test_channel_update():
    """Test basic channel update functionality."""
    channel = langgraph_rs.LastValue(str, "test")
    assert not channel.is_available()

    result = channel.update(["test_value"])
    assert result is True
    assert channel.is_available()
    assert channel.get() == "test_value"

def test_invalid_update():
    """Test that invalid updates raise appropriate errors."""
    channel = langgraph_rs.LastValue(str, "test")

    with pytest.raises(ValueError):
        channel.update(["a", "b"])  # Multiple values not allowed
```

## Submitting Changes

### 1. Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(channels): add BinaryOperatorAggregateChannel implementation

Add support for binary operator aggregation channels with
configurable operators and efficient accumulation.

Closes #123

fix(checkpoint): resolve memory leak in serialization

The checkpoint serialization was not properly releasing memory
after JSON conversion, causing gradual memory growth.

docs(api): update LastValue channel documentation

Add examples and clarify behavior for edge cases.
```

### 2. Pre-submission Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format
- [ ] No breaking changes (or clearly documented)
- [ ] Performance impact considered and tested

### 3. Create Pull Request

```bash
# Push your changes
git push origin feature/your-feature-name

# Create pull request on GitHub
# Include:
# - Clear description of changes
# - Reference to related issues
# - Screenshots/examples if applicable
# - Performance impact if relevant
```

### 4. Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issue
Fixes #(issue number)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Benchmarks added/updated (if performance-related)
- [ ] Manual testing performed

## Performance Impact
Describe any performance implications of these changes.

## Documentation
- [ ] Code comments updated
- [ ] API documentation updated
- [ ] User guide updated (if needed)
- [ ] Examples updated (if needed)

## Additional Notes
Any additional information about the changes.
```

## Code Style

### Rust Style

```bash
# Format code
cargo fmt

# Check linting
cargo clippy -- -D warnings

# Check for common issues
cargo audit
```

### Python Style

```bash
# Format code
poetry run black langgraph_rs/ tests/ examples/

# Sort imports (handled by black with profile)
poetry run isort langgraph_rs/ tests/ examples/

# Lint code with ruff (faster than flake8)
poetry run ruff check langgraph_rs/ tests/ examples/

# Type checking
poetry run mypy langgraph_rs/

# Run all formatting and linting
poetry run black . && poetry run ruff check . && poetry run mypy langgraph_rs/
```

### Documentation Style

- Use clear, concise language
- Include code examples where helpful
- Follow existing documentation structure
- Update table of contents when adding sections

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a professional tone

### Communication

- **Issues**: Use for bug reports and feature requests
- **Discussions**: Use for questions and general discussion
- **Pull Requests**: Use for code changes and documentation updates

### Getting Help

- Check existing documentation first
- Search existing issues and discussions
- Ask specific, detailed questions
- Provide minimal reproduction cases for bugs

### Recognition

Contributors will be recognized in:
- Release notes for significant contributions
- Contributors section in documentation
- Git commit history and GitHub contributions graph

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, backward compatible

### Release Timeline

- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly for new features
- **Major releases**: Quarterly or as needed for breaking changes

---

Thank you for contributing to LangGraph Rust! Your efforts help make the project better for everyone.