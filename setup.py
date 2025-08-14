#!/usr/bin/env python3
"""
Setup script for Python Package Manager.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="vibe-coded-pkg-manager",
    version="1.0.0",
    author="Vibe Coded",
    description="A smart Python package manager that finds optimal package combinations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/edwardwarner/vibe-coded-pkg-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.31.0",
        "packaging>=23.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "pkg-manager=pkg_manager.cli:app",
        ],
    },
    keywords="package manager, dependency resolution, python, pip",
    project_urls={
        "Bug Reports": "https://github.com/edwardwarner/vibe-coded-pkg-manager/issues",
        "Source": "https://github.com/edwardwarner/vibe-coded-pkg-manager",
        "Documentation": "https://github.com/edwardwarner/vibe-coded-pkg-manager#readme",
    },
) 