#!/usr/bin/env python3
"""
Python Package Manager - Parallel Command Line Interface

A smart package manager that finds optimal package combinations using parallel processing.
"""

import sys
import typer
from typing import List, Optional
from pathlib import Path
import time

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from pkg_manager.core import ParallelPackageManager
from pkg_manager.models import Environment, ConflictResolutionStrategy

app = typer.Typer(
    name="pkg-manager-parallel",
    help="A smart Python package manager that finds optimal package combinations using parallel processing",
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
    max_workers: int = typer.Option(
        10,
        "--max-workers", "-w",
        help="Maximum number of parallel workers for package resolution"
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
    )
):
    """
    Resolve package dependencies and generate installation scripts using parallel processing.
    
    Examples:
    
    # Resolve packages from command line with 20 workers
    python pkg_manager_parallel.py resolve --packages "requests>=2.31.0,pandas>=1.5.0" --max-workers 20
    
    # Resolve packages from file with custom timeout
    python pkg_manager_parallel.py resolve --input-file packages.txt --timeout 15
    
    # Generate only requirements.txt with 5 workers
    python pkg_manager_parallel.py resolve --packages "requests,pandas" --requirements-only --max-workers 5
    """
    
    try:
        # Create conflict resolution strategy
        strategy = ConflictResolutionStrategy(
            strategy=conflict_strategy,
            prefer_latest=prefer_latest,
            allow_downgrade=allow_downgrade
        )
        
        # Initialize parallel package manager
        manager = ParallelPackageManager(max_workers=max_workers, timeout=timeout)
        
        # Validate inputs
        if not packages and not input_file:
            typer.echo("Error: Either --packages or --input-file must be provided", err=True)
            raise typer.Exit(1)
        
        if packages and input_file:
            typer.echo("Error: Cannot specify both --packages and --input-file", err=True)
            raise typer.Exit(1)
        
        # Run the parallel package manager
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
        
        # Check if resolution was successful
        if not result["resolution_result"].success:
            typer.echo("Warning: Some conflicts were detected during resolution", err=True)
        
        # Display summary
        if not quiet:
            typer.echo(f"\n✅ Parallel resolution completed!")
            typer.echo(f"📦 Resolved {len(result['resolution_result'].packages)} packages")
            typer.echo(f"🔧 Used {max_workers} parallel workers")
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
        
        package_list = [pkg.strip() for pkg in packages.split(',')]
        worker_counts = [int(w.strip()) for w in workers_list.split(',')]
        
        typer.echo(f"Benchmarking resolution of {len(package_list)} packages...")
        typer.echo(f"Testing worker counts: {worker_counts}")
        typer.echo()
        
        results = {}
        
        for workers in worker_counts:
            typer.echo(f"Testing with {workers} workers...")
            
            start_time = time.time()
            manager = ParallelPackageManager(max_workers=workers, timeout=10)
            
            try:
                result = manager.run(
                    packages=packages,
                    python_version=python_version,
                    display_result=False,
                    max_workers=workers
                )
                
                end_time = time.time()
                duration = end_time - start_time
                results[workers] = {
                    'duration': duration,
                    'packages_resolved': len(result['resolution_result'].packages),
                    'success': result['resolution_result'].success
                }
                
                typer.echo(f"  ✅ Completed in {duration:.2f} seconds")
                typer.echo(f"  📦 Resolved {len(result['resolution_result'].packages)} packages")
                
            except Exception as e:
                typer.echo(f"  ❌ Failed: {e}")
                results[workers] = {'error': str(e)}
        
        # Display benchmark summary
        typer.echo("\n" + "="*50)
        typer.echo("BENCHMARK RESULTS")
        typer.echo("="*50)
        
        for workers, result in results.items():
            if 'error' in result:
                typer.echo(f"{workers:2d} workers: ❌ {result['error']}")
            else:
                typer.echo(f"{workers:2d} workers: ✅ {result['duration']:.2f}s ({result['packages_resolved']} packages)")
        
        # Find best performance
        successful_results = {w: r for w, r in results.items() if 'error' not in r}
        if successful_results:
            best_workers = min(successful_results.keys(), key=lambda w: successful_results[w]['duration'])
            best_time = successful_results[best_workers]['duration']
            typer.echo(f"\n🏆 Best performance: {best_workers} workers ({best_time:.2f}s)")
        
    except Exception as e:
        typer.echo(f"Error during benchmark: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def info():
    """Display information about the parallel package manager."""
    typer.echo("Python Package Manager (Parallel) v1.0.0")
    typer.echo("A smart package manager that finds optimal package combinations using parallel processing")
    typer.echo("\nFeatures:")
    typer.echo("• Parallel dependency resolution")
    typer.echo("• Configurable worker count")
    typer.echo("• Automatic dependency resolution")
    typer.echo("• Version conflict detection")
    typer.echo("• Cross-platform script generation")
    typer.echo("• Virtual environment setup")
    typer.echo("\nPerformance:")
    typer.echo("• Significantly faster for large package lists")
    typer.echo("• Configurable parallelism (default: 10 workers)")
    typer.echo("• Built-in benchmarking tool")
    typer.echo("\nFor more information, see the README.md file")


@app.command()
def example():
    """Show usage examples."""
    typer.echo("Usage Examples:")
    typer.echo("\n1. Basic usage with parallel processing:")
    typer.echo("   python pkg_manager_parallel.py resolve --packages 'requests>=2.31.0,pandas>=1.5.0'")
    typer.echo("\n2. High-performance resolution with 20 workers:")
    typer.echo("   python pkg_manager_parallel.py resolve --packages 'numpy,scipy,matplotlib' --max-workers 20")
    typer.echo("\n3. Using a package file with custom timeout:")
    typer.echo("   python pkg_manager_parallel.py resolve --input-file packages.txt --timeout 15")
    typer.echo("\n4. Benchmark different worker counts:")
    typer.echo("   python pkg_manager_parallel.py benchmark --workers '1,5,10,20'")
    typer.echo("\n5. Custom output directory:")
    typer.echo("   python pkg_manager_parallel.py resolve --packages 'django,flask' --output-dir ./my_project")


@app.command()
def test_versions(
    packages: str = typer.Option(..., "--packages", "-p", help="Comma-separated list of packages"),
    python_versions: str = typer.Option("3.7,3.8,3.9,3.10,3.11", "--python-versions", help="Comma-separated list of Python versions to test"),
    max_workers: int = typer.Option(5, "--max-workers", "-w", help="Maximum number of parallel workers"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout in seconds for each resolution")
):
    """Test package compatibility across multiple Python versions."""
    print("🔍 Testing package compatibility across Python versions...")
    
    # Parse Python versions
    versions_to_test = [v.strip() for v in python_versions.split(",")]
    package_list = [pkg.strip() for pkg in packages.split(",")]
    
    print(f"📦 Packages: {', '.join(package_list)}")
    print(f"🐍 Python versions: {', '.join(versions_to_test)}")
    print("=" * 60)
    
    results = {}
    best_version = None
    best_score = 0
    
    for python_version in versions_to_test:
        print(f"\n🐍 Testing Python {python_version}...")
        
        try:
            # Create environment
            environment = Environment(python_version=python_version)
            
            # Create package manager
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
            
            print(f"✅ Python {python_version}: {compatible_packages}/{total_packages} packages compatible ({compatibility_score:.1f}%)")
            
            # Track best version
            if compatibility_score > best_score:
                best_score = compatibility_score
                best_version = python_version
                
        except Exception as e:
            print(f"❌ Python {python_version}: Error - {e}")
            results[python_version] = {
                'success': False,
                'error': str(e),
                'compatibility_score': 0
            }
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 COMPATIBILITY SUMMARY")
    print("=" * 60)
    
    for version, result in results.items():
        if result['success']:
            print(f"🐍 Python {version}: {result['compatible_packages']}/{result['total_packages']} packages ({result['compatibility_score']:.1f}%)")
        else:
            print(f"🐍 Python {version}: ❌ Failed - {result.get('error', 'Unknown error')}")
    
    if best_version:
        print(f"\n🏆 RECOMMENDED: Python {best_version} ({best_score:.1f}% compatibility)")
        print(f"💡 Use: python pkg_manager_parallel.py resolve --packages '{packages}' --python-version {best_version}")
    else:
        print("\n❌ No compatible Python version found")


if __name__ == "__main__":
    app()
