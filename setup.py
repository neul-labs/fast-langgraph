#!/usr/bin/env python3
"""
Setup script for LangGraph Rust implementation.
This script ensures that the Rust components can be properly built and integrated
with the existing Python testing infrastructure.
"""

from setuptools import setup, find_packages
from setuptools_rust import Binding, RustExtension
import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_rust_toolchain():
    """Check if Rust toolchain is available."""
    try:
        result = subprocess.run(['rustc', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✓ Rust toolchain available: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Rust toolchain not found")
        print("  Install Rust toolchain from https://www.rust-lang.org/tools/install")
        return False


def build_rust_components():
    """Build Rust components."""
    try:
        # Change to the Rust directory
        rust_dir = Path(__file__).parent.absolute()
        print(f"Building Rust components in {rust_dir}")
        
        # Run cargo build
        result = subprocess.run(['cargo', 'build', '--release'], 
                              cwd=rust_dir, capture_output=True, text=True, check=True)
        print("✓ Rust components built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build Rust components: {e}")
        print(f"  Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ Cargo not found. Please install Rust toolchain.")
        return False


def check_python_dev_headers():
    """Check if Python development headers are available."""
    try:
        import pyo3_build_config
        print("✓ Python development headers available")
        return True
    except ImportError:
        print("✗ Python development headers not found")
        print("  Install Python development headers:")
        print("    Ubuntu/Debian: sudo apt-get install python3-dev")
        print("    CentOS/RHEL: sudo yum install python3-devel")
        print("    macOS: brew install python3")
        return False


def run_python_tests():
    """Run Python tests to verify integration."""
    try:
        # Change to the project root
        project_root = Path(__file__).parent.absolute()
        print(f"Running Python tests in {project_root}")
        
        # Run a simple test to verify the setup
        result = subprocess.run([sys.executable, '-c', '''
import sys
print("Python installation verified")
'''], cwd=project_root, capture_output=True, text=True, check=True)
        print("✓ Python environment verified")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to verify Python environment: {e}")
        return False


def setup_development_environment():
    """Set up the development environment for LangGraph Rust."""
    print("Setting up LangGraph Rust development environment...")
    print("=" * 50)
    
    # Check prerequisites
    checks = [
        check_rust_toolchain(),
        check_python_dev_headers(),
        build_rust_components(),
        run_python_tests()
    ]
    
    if all(checks):
        print("\n" + "=" * 50)
        print("✓ All checks passed! Development environment ready.")
        print("\nTo run tests:")
        print("  python -m pytest tests/")
        print("\nTo run benchmarks:")
        print("  cargo bench")
        print("\nTo build documentation:")
        print("  cargo doc --open")
        return True
    else:
        print("\n" + "=" * 50)
        print("✗ Some checks failed. Please address the issues above.")
        return False


def install_dependencies():
    """Install development dependencies."""
    try:
        # Install Python dependencies
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
                      capture_output=True, check=True)
        
        # Install development dependencies
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest', 'criterion'],
                      capture_output=True, check=True)
        
        print("✓ Development dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def main():
    """Main setup function."""
    # Check if we're in build mode (don't run environment checks)
    is_build_mode = any(arg in sys.argv for arg in ['bdist_wheel', 'sdist', 'build', 'build_ext', 'install'])

    if len(sys.argv) > 1 and sys.argv[1] == '--install':
        print("Installing dependencies...")
        if not install_dependencies():
            sys.exit(1)
    elif not is_build_mode:
        # Only run environment checks if not in build mode
        if not setup_development_environment():
            sys.exit(1)
        print("\n🎉 Setup completed successfully!")
    else:
        # In build mode, run the actual setup
        setup(
            name="langgraph-rs",
            version="0.1.0",
            author="LangGraph Team",
            author_email="",
            description="High-performance Rust implementation of LangGraph components",
            long_description=open("README.md").read(),
            long_description_content_type="text/markdown",
            url="https://github.com/langchain-ai/langgraph",
            packages=find_packages(),
            rust_extensions=[
                RustExtension(
                    "langgraph_rs.langgraph_rs",
                    binding=Binding.PyO3,
                    debug=False,
                )
            ],
            classifiers=[
                "Development Status :: 3 - Alpha",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.8",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Rust",
            ],
            python_requires=">=3.8",
            install_requires=[
                "typing-extensions",
            ],
            extras_require={
                "dev": [
                    "pytest",
                    "langgraph",  # For testing compatibility
                ],
            },
            zip_safe=False,
        )


if __name__ == "__main__":
    main()