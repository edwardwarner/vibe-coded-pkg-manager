"""
Parallel core package manager functionality.
"""

import os
import sys
import time
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

from ..models import Environment, ResolutionResult, ConflictResolutionStrategy
from ..clients import ParallelPyPIClient
from ..resolvers import ParallelDependencyResolver
from ..generators import ScriptGenerator


class ParallelPackageManager:
    """Parallel package manager class that orchestrates the resolution and script generation."""
    
    def __init__(self, max_workers: int = 10, timeout: int = 10):
        self.console = Console()
        self.max_workers = max_workers
        self.timeout = timeout
        self.pypi_client = ParallelPyPIClient(max_workers=max_workers, timeout=timeout)
        self.resolver = ParallelDependencyResolver(max_workers=max_workers, timeout=timeout)
        self.script_generator = ScriptGenerator()
    
    def resolve_packages(self, 
                        package_specs: List[str], 
                        python_version: str = "3.9",
                        platform: str = "any",
                        conflict_strategy: Optional[ConflictResolutionStrategy] = None) -> ResolutionResult:
        """Resolve package dependencies and find optimal versions using parallel processing."""
        
        environment = Environment(
            python_version=python_version,
            platform=platform
        )
        
        self.console.print(f"[bold blue]Resolving {len(package_specs)} packages for Python {python_version} using {self.max_workers} workers...[/bold blue]")
        
        start_time = time.time()
        
        # Resolve dependencies
        result = self.resolver.resolve_dependencies(package_specs, environment, conflict_strategy)
        
        # Optimize versions
        optimized_result = self.resolver.optimize_versions(result, environment)
        
        total_time = time.time() - start_time
        self.console.print(f"[bold green]Total resolution time: {total_time:.2f} seconds[/bold green]")
        
        return optimized_result
    
    def generate_scripts(self, 
                        resolution_result: ResolutionResult,
                        environment: Environment,
                        output_dir: str = ".",
                        venv_name: str = "venv") -> dict:
        """Generate installation scripts and requirements file."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate bash script
        install_script_path = os.path.join(output_dir, "install.sh")
        install_script = self.script_generator.generate_install_script(
            resolution_result, environment, install_script_path, venv_name
        )
        
        # Generate requirements file
        requirements_path = os.path.join(output_dir, "requirements.txt")
        requirements_content = self.script_generator.generate_requirements_file(
            resolution_result, requirements_path
        )
        
        # Generate activation script
        activation_script_path = os.path.join(output_dir, "activate.sh")
        activation_script = self.script_generator.generate_activation_script(
            venv_name, activation_script_path
        )
        
        # Generate Windows script if needed
        windows_script_path = os.path.join(output_dir, "install.bat")
        windows_script = self.script_generator.generate_windows_script(
            resolution_result, environment, windows_script_path, venv_name
        )
        
        return {
            "install_script": install_script_path,
            "requirements_file": requirements_path,
            "activation_script": activation_script_path,
            "windows_script": windows_script_path
        }
    
    def display_resolution_result(self, result: ResolutionResult):
        """Display the resolution result in a nice format."""
        
        # Create a table for packages
        table = Table(title="Resolved Packages")
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Dependencies", style="yellow")
        
        for package in result.packages:
            deps = ", ".join(package.dependencies) if package.dependencies else "None"
            package_type = "Direct" if package.is_direct else "Dependency"
            table.add_row(package.name, package.version, package_type, deps)
        
        self.console.print(table)
        
        # Display conflicts if any
        if result.package_conflicts:
            self.console.print("\n[bold red]Conflicts Found:[/bold red]")
            for conflict in result.package_conflicts:
                self.console.print(f"  • {conflict.package_name}: {conflict.reason}")
                if conflict.resolution_suggestions:
                    self.console.print(f"    Suggestions: {', '.join(conflict.resolution_suggestions[:3])}")
        
        # Display resolutions if any
        if result.resolutions:
            self.console.print("\n[bold green]Conflict Resolutions:[/bold green]")
            for resolution in result.resolutions:
                self.console.print(f"  ✅ {resolution.package_name}: {resolution.chosen_version} ({resolution.strategy_used})")
        
        # Display warnings if any
        if result.warnings:
            self.console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result.warnings:
                self.console.print(f"  • {warning}")
        
        # Display dependency tree
        if result.dependency_tree:
            self.console.print("\n[bold blue]Dependency Tree:[/bold blue]")
            tree = Tree("📦 Packages")
            for package, deps in result.dependency_tree.items():
                package_node = tree.add(f"📦 {package}")
                for dep in deps:
                    package_node.add(f"  📦 {dep}")
            self.console.print(tree)
    
    def load_packages_from_file(self, file_path: str) -> List[str]:
        """Load package specifications from a file."""
        packages = []
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        packages.append(line)
        except FileNotFoundError:
            self.console.print(f"[red]Error: File {file_path} not found[/red]")
            return []
        except Exception as e:
            self.console.print(f"[red]Error reading file {file_path}: {e}[/red]")
            return []
        
        return packages
    
    def run(self, 
            packages: Optional[str] = None,
            input_file: Optional[str] = None,
            python_version: str = "3.9",
            platform: str = "any",
            output_dir: str = ".",
            venv_name: str = "venv",
            display_result: bool = True,
            max_workers: Optional[int] = None,
            conflict_strategy: Optional[ConflictResolutionStrategy] = None) -> dict:
        """Main method to run the parallel package manager."""
        
        # Update max_workers if specified
        if max_workers is not None:
            self.max_workers = max_workers
            self.pypi_client.max_workers = max_workers
            self.resolver.max_workers = max_workers
        
        # Load packages
        if input_file:
            package_specs = self.load_packages_from_file(input_file)
        elif packages:
            # Parse comma-separated packages
            package_specs = [pkg.strip() for pkg in packages.split(',') if pkg.strip()]
        else:
            raise ValueError("Either packages or input_file must be provided")
        
        if not package_specs:
            raise ValueError("No packages specified")
        
        self.console.print(f"[bold blue]Processing {len(package_specs)} packages with {self.max_workers} parallel workers[/bold blue]")
        
        # Resolve packages
        resolution_result = self.resolve_packages(package_specs, python_version, platform, conflict_strategy)
        
        # Display result if requested
        if display_result:
            self.display_resolution_result(resolution_result)
        
        # Generate scripts
        try:
            environment = Environment(python_version=python_version, platform=platform)
            generated_files = self.generate_scripts(
                resolution_result, environment, output_dir, venv_name
            )
            
            # Display generated files
            self.console.print(f"\n[bold green]Generated files:[/bold green]")
            for file_type, file_path in generated_files.items():
                self.console.print(f"  • {file_type}: {file_path}")
        except Exception as e:
            self.console.print(f"[red]Error generating scripts: {e}[/red]")
            generated_files = {}
        
        return {
            "resolution_result": resolution_result,
            "generated_files": generated_files
        }
