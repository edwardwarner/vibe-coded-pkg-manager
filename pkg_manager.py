#!/usr/bin/env python3
"""
Python Package Manager - Command Line Interface

A smart package manager that finds optimal package combinations and generates installation scripts.
"""

import sys
import typer
from typing import List, Optional
from pathlib import Path

# Add the current directory to the path so we can import our package
sys.path.insert(0, str(Path(__file__).parent))

from pkg_manager.core import PackageManager
from pkg_manager.models import Environment, ConflictResolutionStrategy

app = typer.Typer(
    name="pkg-manager",
    help="A smart Python package manager that finds optimal package combinations",
    add_completion=False
)


@app.command()
def resolve(
    packages: Optional[str] = typer.Option(
        None,
        "--packages", "-p",
        help="Comma-separated list of packages to resolve (e.g., 'requests>=2.31.0,pandas>=1.5.0')"
    ),
    input_file: Optional[str] = typer.Option(
        None,
        "--input-file", "-f",
        help="File containing package specifications (one per line)"
    ),
    python_version: str = typer.Option(
        "3.9",
        "--python-version", "-v",
        help="Target Python version"
    ),
    platform: str = typer.Option(
        "any",
        "--platform", "-P",
        help="Target platform (linux, windows, macos, any)"
    ),
    output_dir: str = typer.Option(
        ".",
        "--output-dir", "-o",
        help="Output directory for generated files"
    ),
    venv_name: str = typer.Option(
        "venv",
        "--venv-name", "-n",
        help="Name of the virtual environment"
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Suppress output display"
    ),
    requirements_only: bool = typer.Option(
        False,
        "--requirements-only", "-r",
        help="Generate only requirements.txt file"
    ),
    conflict_strategy: str = typer.Option(
        "auto",
        "--conflict-strategy", "-c",
        help="Strategy for resolving package conflicts (auto, manual, ignore, fail)"
    ),
    prefer_latest: bool = typer.Option(
        True,
        "--prefer-latest",
        help="Prefer latest versions when resolving conflicts"
    ),
    allow_downgrade: bool = typer.Option(
        False,
        "--allow-downgrade",
        help="Allow downgrading packages to resolve conflicts"
    )
):
    """
    Resolve package dependencies and generate installation scripts.
    
    Examples:
    
    # Resolve packages from command line
    python pkg_manager.py resolve --packages "requests>=2.31.0" "pandas>=1.5.0" --python-version "3.9"
    
    # Resolve packages from file
    python pkg_manager.py resolve --input-file packages.txt --python-version "3.8"
    
    # Generate only requirements.txt
    python pkg_manager.py resolve --packages "requests" "pandas" --requirements-only
    """
    
    try:
        # Create conflict resolution strategy
        strategy = ConflictResolutionStrategy(
            strategy=conflict_strategy,
            prefer_latest=prefer_latest,
            allow_downgrade=allow_downgrade
        )
        
        # Initialize package manager
        manager = PackageManager()
        
        # Validate inputs
        if not packages and not input_file:
            typer.echo("Error: Either --packages or --input-file must be provided", err=True)
            raise typer.Exit(1)
        
        if packages and input_file:
            typer.echo("Error: Cannot specify both --packages and --input-file", err=True)
            raise typer.Exit(1)
        
        # Run the package manager
        result = manager.run(
            packages=packages,
            input_file=input_file,
            python_version=python_version,
            platform=platform,
            output_dir=output_dir,
            venv_name=venv_name,
            display_result=not quiet,
            conflict_strategy=strategy
        )
        
        # Check if resolution was successful
        if not result["resolution_result"].success:
            typer.echo("Warning: Some conflicts were detected during resolution", err=True)
        
        # Display summary
        if not quiet:
            typer.echo(f"\n✅ Resolution completed!")
            typer.echo(f"📦 Resolved {len(result['resolution_result'].packages)} packages")
            typer.echo(f"📁 Generated files in: {output_dir}")
        
        # Exit with appropriate code
        if result["resolution_result"].success:
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def info():
    """Display information about the package manager."""
    typer.echo("Python Package Manager v1.0.0")
    typer.echo("A smart package manager that finds optimal package combinations")
    typer.echo("\nFeatures:")
    typer.echo("• Automatic dependency resolution")
    typer.echo("• Version conflict detection")
    typer.echo("• Cross-platform script generation")
    typer.echo("• Virtual environment setup")
    typer.echo("\nFor more information, see the README.md file")


@app.command()
def example():
    """Show usage examples."""
    typer.echo("Usage Examples:")
    typer.echo("\n1. Basic usage with command line packages:")
    typer.echo("   python pkg_manager.py resolve --packages 'requests>=2.31.0,pandas>=1.5.0'")
    typer.echo("\n2. Using a package file:")
    typer.echo("   python pkg_manager.py resolve --input-file packages.txt --python-version 3.8")
    typer.echo("\n3. Generate only requirements.txt:")
    typer.echo("   python pkg_manager.py resolve --packages 'requests,pandas' --requirements-only")
    typer.echo("\n4. Custom output directory:")
    typer.echo("   python pkg_manager.py resolve --packages 'numpy,scipy' --output-dir ./my_project")
    typer.echo("\n5. Different Python version:")
    typer.echo("   python pkg_manager.py resolve --packages 'django>=4.0' --python-version 3.11")


if __name__ == "__main__":
    app() 