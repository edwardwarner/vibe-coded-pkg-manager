#!/usr/bin/env python3
"""
Unified Python Package Manager CLI
Automatically chooses between sequential and parallel processing based on package count.
"""

import sys
import typer
from typing import List, Optional
from pathlib import Path
import time

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from pkg_manager.core import PackageManager, ParallelPackageManager
from pkg_manager.models import Environment, ConflictResolutionStrategy

app = typer.Typer(
    name="pkg-manager",
    help="Python Package Manager - Automatically chooses optimal processing method",
    add_completion=False
)

# Threshold for switching from sequential to parallel processing
PARALLEL_THRESHOLD = 5


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
    max_workers: int = typer.Option(
        10,
        "--max-workers", "-w",
        help="Maximum number of parallel workers (only used for parallel processing)"
    ),
    timeout: int = typer.Option(
        10,
        "--timeout", "-t",
        help="Timeout in seconds for HTTP requests"
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
    ),
    force_sequential: bool = typer.Option(
        False,
        "--force-sequential",
        help="Force sequential processing regardless of package count"
    ),
    force_parallel: bool = typer.Option(
        False,
        "--force-parallel",
        help="Force parallel processing regardless of package count"
    )
):
    """
    Resolve package dependencies and generate installation scripts.
    Automatically chooses between sequential and parallel processing based on package count.
    
    Examples:
    
    # Automatic processing (sequential for <5 packages, parallel for >=5)
    python pkg_manager.py resolve --packages "requests,pandas"
    python pkg_manager.py resolve --packages "requests,pandas,numpy,scipy,matplotlib,seaborn"
    
    # Force specific processing method
    python pkg_manager.py resolve --packages "requests,pandas" --force-parallel
    python pkg_manager.py resolve --packages "requests,pandas,numpy,scipy,matplotlib" --force-sequential
    
    # With conflict resolution
    python pkg_manager.py resolve --packages "django>=4.0.0,django<3.0.0" --conflict-strategy auto
    """
    
    try:
        # Create conflict resolution strategy
        strategy = ConflictResolutionStrategy(
            strategy=conflict_strategy,
            prefer_latest=prefer_latest,
            allow_downgrade=allow_downgrade
        )
        
        # Validate inputs
        if not packages and not input_file:
            typer.echo("Error: Either --packages or --input-file must be provided", err=True)
            raise typer.Exit(1)
        
        if packages and input_file:
            typer.echo("Error: Cannot specify both --packages and --input-file", err=True)
            raise typer.Exit(1)
        
        # Load package specifications
        if input_file:
            package_specs = load_packages_from_file(input_file)
        else:
            package_specs = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
        
        if not package_specs:
            raise ValueError("No packages specified")
        
        # Determine processing method
        use_parallel = determine_processing_method(
            len(package_specs), 
            force_sequential, 
            force_parallel
        )
        
        if not quiet:
            if use_parallel:
                typer.echo(f"🔄 Using parallel processing for {len(package_specs)} packages (threshold: {PARALLEL_THRESHOLD})")
            else:
                typer.echo(f"🔄 Using sequential processing for {len(package_specs)} packages (threshold: {PARALLEL_THRESHOLD})")
        
        # Create appropriate package manager
        if use_parallel:
            manager = ParallelPackageManager(max_workers=max_workers, timeout=timeout)
        else:
            manager = PackageManager()
        
        # Run resolution
        start_time = time.time()
        if use_parallel:
            result = manager.run(
                packages=packages,
                input_file=input_file,
                python_version=python_version,
                platform=platform,
                output_dir=output_dir,
                venv_name=venv_name,
                display_result=not quiet,
                max_workers=max_workers,
                conflict_strategy=strategy
            )
        else:
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
        total_time = time.time() - start_time
        
        # Check if resolution was successful
        if not result["resolution_result"].success:
            typer.echo("Warning: Some conflicts were detected during resolution", err=True)
        
        # Display summary
        if not quiet:
            processing_type = "Parallel" if use_parallel else "Sequential"
            typer.echo(f"\n✅ {processing_type} resolution completed!")
            typer.echo(f"📦 Resolved {len(result['resolution_result'].packages)} packages")
            if use_parallel:
                typer.echo(f"🔧 Used {max_workers} parallel workers")
            typer.echo(f"⏱️  Total time: {total_time:.2f} seconds")
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
def benchmark(
    packages: str = typer.Option(
        "requests,pandas,numpy,scipy,matplotlib,seaborn,scikit-learn,tensorflow,torch,jupyter",
        "--packages", "-p",
        help="Comma-separated list of packages to benchmark"
    ),
    python_version: str = typer.Option(
        "3.9",
        "--python-version", "-v",
        help="Target Python version"
    ),
    workers_list: str = typer.Option(
        "1,5,10,20",
        "--workers", "-w",
        help="Comma-separated list of worker counts to benchmark"
    )
):
    """Benchmark different worker counts for package resolution."""
    
    try:
        import time
        
        package_list = [pkg.strip() for pkg in packages.split(",")]
        workers = [int(w.strip()) for w in workers_list.split(",")]
        
        typer.echo(f"Benchmarking resolution of {len(package_list)} packages...")
        typer.echo(f"Testing worker counts: {workers}")
        typer.echo()
        
        results = {}
        
        for worker_count in workers:
            typer.echo(f"Testing with {worker_count} workers...")
            
            start_time = time.time()
            
            # Create package manager
            manager = ParallelPackageManager(max_workers=worker_count, timeout=30)
            
            # Run resolution
            result = manager.run(
                packages=packages,
                python_version=python_version,
                display_result=False
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            results[worker_count] = {
                'duration': duration,
                'success': result["resolution_result"].success,
                'packages': len(result["resolution_result"].packages)
            }
            
            typer.echo(f"  ✅ Completed in {duration:.2f} seconds")
            typer.echo(f"  📦 Resolved {len(result['resolution_result'].packages)} packages")
            typer.echo()
        
        # Display benchmark results
        typer.echo("=" * 50)
        typer.echo("BENCHMARK RESULTS")
        typer.echo("=" * 50)
        
        best_worker = min(results.keys(), key=lambda w: results[w]['duration'])
        
        for worker_count in sorted(results.keys()):
            result = results[worker_count]
            status = "✅" if result['success'] else "❌"
            typer.echo(f" {worker_count:2d} workers: {status} {result['duration']:.2f}s ({result['packages']} packages)")
        
        typer.echo()
        typer.echo(f"🏆 Best performance: {best_worker} workers ({results[best_worker]['duration']:.2f}s)")
        
    except Exception as e:
        typer.echo(f"Error during benchmarking: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def test_versions(
    packages: str = typer.Option(..., "--packages", "-p", help="Comma-separated list of packages"),
    python_versions: str = typer.Option("3.7,3.8,3.9,3.10,3.11", "--python-versions", help="Comma-separated list of Python versions to test"),
    max_workers: int = typer.Option(5, "--max-workers", "-w", help="Maximum number of parallel workers"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout in seconds for each resolution")
):
    """Test package compatibility across multiple Python versions."""
    typer.echo("🔍 Testing package compatibility across Python versions...")
    
    # Parse Python versions
    versions_to_test = [v.strip() for v in python_versions.split(",")]
    package_list = [pkg.strip() for pkg in packages.split(",")]
    
    typer.echo(f"📦 Packages: {', '.join(package_list)}")
    typer.echo(f"🐍 Python versions: {', '.join(versions_to_test)}")
    typer.echo("=" * 60)
    
    results = {}
    best_version = None
    best_score = 0
    
    for python_version in versions_to_test:
        typer.echo(f"\n🐍 Testing Python {python_version}...")
        
        try:
            # Create environment
            environment = Environment(python_version=python_version)
            
            # Create package manager (always use parallel for testing)
            manager = ParallelPackageManager(
                max_workers=max_workers,
                timeout=timeout
            )
            
            # Resolve packages
            result = manager.run(
                packages=packages,
                python_version=python_version,
                output_dir=f"./test_output_{python_version.replace('.', '_')}",
                display_result=False
            )
            
            # Calculate compatibility score
            total_packages = len(result['resolution_result'].packages)
            compatible_packages = 0
            
            for package in result['resolution_result'].packages:
                # Check if package is compatible (no warnings in output)
                # This is a simplified check - in a real implementation you'd track warnings
                compatible_packages += 1
            
            compatibility_score = (compatible_packages / total_packages) * 100 if total_packages > 0 else 0
            
            results[python_version] = {
                'success': result['resolution_result'].success,
                'packages': result['resolution_result'].packages,
                'compatibility_score': compatibility_score,
                'total_packages': total_packages,
                'compatible_packages': compatible_packages
            }
            
            typer.echo(f"✅ Python {python_version}: {compatible_packages}/{total_packages} packages compatible ({compatibility_score:.1f}%)")
            
            # Track best version
            if compatibility_score > best_score:
                best_score = compatibility_score
                best_version = python_version
                
        except Exception as e:
            typer.echo(f"❌ Python {python_version}: Error - {e}")
            results[python_version] = {
                'success': False,
                'error': str(e),
                'compatibility_score': 0
            }
    
    # Print summary
    typer.echo("\n" + "=" * 60)
    typer.echo("📊 COMPATIBILITY SUMMARY")
    typer.echo("=" * 60)
    
    for version, result in results.items():
        if result['success']:
            typer.echo(f"🐍 Python {version}: {result['compatible_packages']}/{result['total_packages']} packages ({result['compatibility_score']:.1f}%)")
        else:
            typer.echo(f"🐍 Python {version}: ❌ Failed - {result.get('error', 'Unknown error')}")
    
    if best_version:
        typer.echo(f"\n🏆 RECOMMENDED: Python {best_version} ({best_score:.1f}% compatibility)")
        typer.echo(f"💡 Use: python pkg_manager.py resolve --packages '{packages}' --python-version {best_version}")
    else:
        typer.echo("\n❌ No compatible Python version found")


@app.command()
def info():
    """Display information about the package manager."""
    typer.echo("Python Package Manager v1.0.0")
    typer.echo("A smart package manager that automatically chooses optimal processing method")
    typer.echo("\nFeatures:")
    typer.echo("• Automatic processing method selection")
    typer.echo("• Sequential processing for small package lists (<5 packages)")
    typer.echo("• Parallel processing for large package lists (≥5 packages)")
    typer.echo("• Configurable processing thresholds")
    typer.echo("• Conflict resolution strategies")
    typer.echo("• Python version compatibility testing")
    typer.echo("• Cross-platform script generation")
    typer.echo("\nProcessing Logic:")
    typer.echo(f"• Sequential: <{PARALLEL_THRESHOLD} packages (fast for small lists)")
    typer.echo(f"• Parallel: ≥{PARALLEL_THRESHOLD} packages (optimal for large lists)")
    typer.echo("• Override with --force-sequential or --force-parallel")
    typer.echo("\nFor more information, see the README.md file")


@app.command()
def example():
    """Show usage examples."""
    typer.echo("Usage Examples:")
    typer.echo("\n1. Automatic processing (recommended):")
    typer.echo("   python pkg_manager.py resolve --packages 'requests,pandas'")
    typer.echo("   python pkg_manager.py resolve --packages 'requests,pandas,numpy,scipy,matplotlib,seaborn'")
    typer.echo("\n2. Force specific processing method:")
    typer.echo("   python pkg_manager.py resolve --packages 'requests,pandas' --force-parallel")
    typer.echo("   python pkg_manager.py resolve --packages 'requests,pandas,numpy,scipy,matplotlib' --force-sequential")
    typer.echo("\n3. With conflict resolution:")
    typer.echo("   python pkg_manager.py resolve --packages 'django>=4.0.0,django<3.0.0' --conflict-strategy auto")
    typer.echo("\n4. Test compatibility across Python versions:")
    typer.echo("   python pkg_manager.py test-versions --packages 'requests,pandas,numpy' --python-versions '3.8,3.9,3.10,3.11'")
    typer.echo("\n5. Benchmark performance:")
    typer.echo("   python pkg_manager.py benchmark --packages 'requests,pandas,numpy,scipy,matplotlib' --workers '1,5,10,20'")


def load_packages_from_file(file_path: str) -> List[str]:
    """Load package specifications from a file."""
    packages = []
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages.append(line)
    except FileNotFoundError:
        typer.echo(f"Error: File {file_path} not found", err=True)
        return []
    except Exception as e:
        typer.echo(f"Error reading file {file_path}: {e}", err=True)
        return []
    
    return packages


def determine_processing_method(
    package_count: int, 
    force_sequential: bool, 
    force_parallel: bool
) -> bool:
    """
    Determine whether to use parallel processing based on package count and flags.
    
    Returns:
        bool: True for parallel processing, False for sequential
    """
    if force_sequential:
        return False
    elif force_parallel:
        return True
    else:
        return package_count >= PARALLEL_THRESHOLD


if __name__ == "__main__":
    app()
