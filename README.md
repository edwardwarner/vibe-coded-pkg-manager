# Vibe Coded Python Package Manager

A smart Python package manager that finds optimal package combinations for your environment and generates installation scripts. Features both sequential and high-performance parallel processing for handling packages of any scale.

## Features

- **Dependency Resolution**: Automatically resolves package dependencies and version conflicts
- **Optimal Version Selection**: Finds the best combination of package versions that work together
- **Environment Support**: Works with different Python versions and platforms
- **Script Generation**: Outputs bash scripts to create virtual environments and install packages
- **Conflict Detection**: Identifies and reports dependency conflicts
- **Parallel Processing**: High-performance parallel resolution for large package lists
- **Configurable Workers**: Adjustable number of parallel workers for optimal performance
- **Built-in Benchmarking**: Test different worker counts to find optimal performance

## Installation

```bash
# Clone the repository
git clone https://github.com/edwardwarner/vibe-coded-pkg-manager
cd pkg-manager

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Usage

### Basic Usage

```bash
# Sequential resolution (small to medium package lists)
python pkg_manager.py resolve --packages "requests>=2.31.0,pandas>=1.5.0" --python-version "3.9"

# Parallel resolution (large package lists)
python pkg_manager_parallel.py resolve --packages "requests,pandas,numpy,scipy,matplotlib" --max-workers 10
```

### Advanced Usage

```bash
# Sequential with multiple options
python pkg_manager.py resolve \
  --packages "requests>=2.31.0,pandas>=1.5.0,numpy>=1.21.0" \
  --python-version "3.9" \
  --platform "linux" \
  --output-dir "./my_project"

# Parallel with custom configuration
python pkg_manager_parallel.py resolve \
  --packages "requests,pandas,numpy,scipy,matplotlib,seaborn" \
  --max-workers 20 \
  --timeout 15 \
  --output-dir "./data_science_env"
```

### Parallel Processing (High Performance)

For large package lists, use the parallel version:

```bash
# Basic parallel resolution
python pkg_manager_parallel.py resolve --packages "requests,pandas,numpy,scipy,matplotlib" --max-workers 10

# High-performance resolution with 20 workers
python pkg_manager_parallel.py resolve --input-file large_packages.txt --max-workers 20

# Benchmark different worker counts
python pkg_manager_parallel.py benchmark --packages "requests,pandas,numpy,scipy,matplotlib" --workers "1,5,10,20"

# Custom timeout and worker configuration
python pkg_manager_parallel.py resolve --packages "..." --max-workers 15 --timeout 20
```

### Input File Usage

Create a `packages.txt` file:
```
requests>=2.31.0
pandas>=1.5.0
numpy>=1.21.0
```

Then run:
```bash
# Sequential resolution from file
python pkg_manager.py resolve --input-file packages.txt --python-version "3.9"

# Parallel resolution from file
python pkg_manager_parallel.py resolve --input-file packages.txt --max-workers 10
```

## Output

The tool generates:
1. **Resolved dependency tree** with optimal versions
2. **Installation scripts**:
   - `install.sh` - Bash script for Linux/macOS
   - `install.bat` - Windows batch script
   - `activate.sh` - Simple activation script
3. **Requirements file** - Pin-exact `requirements.txt` with resolved versions

### Example Output
```
              Resolved Packages               
┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Package  ┃ Version ┃ Type   ┃ Dependencies ┃
┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━┩
│ requests │ 2.32.4  │ Direct │ None         │
│ pandas   │ 2.3.1   │ Direct │ None         │
└──────────┴─────────┴────────┴──────────────┘

Generated files:
  • install_script: ./install.sh
  • requirements_file: ./requirements.txt
  • activation_script: ./activate.sh
  • windows_script: ./install.bat
```

## Performance

The package manager includes parallel processing capabilities for handling large package lists:

- **Sequential Version**: Standard resolution for small to medium package lists
- **Parallel Version**: High-performance resolution using configurable worker threads
- **Benchmarking**: Built-in tool to test different worker counts and find optimal performance
- **Scalability**: Significantly faster resolution for large package lists (30+ packages)

### Performance Examples
- **5 packages**: ~1 second with 10 workers (vs ~3 seconds sequential)
- **30+ packages**: ~9 seconds with 20 workers (vs ~30+ seconds sequential)
- **Large lists**: 3-10x faster with parallel processing

### Benchmark Results
```
==================================================
BENCHMARK RESULTS
==================================================
 1 workers: ✅ 1.46s (3 packages)
 5 workers: ✅ 0.63s (3 packages)
10 workers: ✅ 0.45s (3 packages)

🏆 Best performance: 10 workers (0.45s)
```

## Project Structure

The project is organized into logical modules for maintainability:

```
pkg-manager/
├── pkg_manager/
│   ├── models/          # Data models (PackageSpec, Environment, etc.)
│   ├── clients/         # PyPI clients (sequential and parallel)
│   ├── resolvers/       # Dependency resolvers (sequential and parallel)
│   ├── generators/      # Script generators
│   └── core/           # Core functionality and CLI
├── tests/              # Test suite
├── pkg_manager.py      # Sequential CLI
└── pkg_manager_parallel.py  # Parallel CLI
```

## Additional Features

### Command Line Options

#### Sequential Package Manager (`pkg_manager.py`)
```bash
python pkg_manager.py resolve [OPTIONS]
  --packages TEXT        Comma-separated list of packages
  --input-file TEXT      File containing package specifications
  --python-version TEXT  Target Python version [default: 3.9]
  --platform TEXT        Target platform [default: any]
  --output-dir TEXT      Output directory [default: .]
  --venv-name TEXT       Virtual environment name [default: venv]
  --quiet                Suppress output display
  --requirements-only    Generate only requirements.txt
```

#### Parallel Package Manager (`pkg_manager_parallel.py`)
```bash
python pkg_manager_parallel.py resolve [OPTIONS]
  --packages TEXT        Comma-separated list of packages
  --input-file TEXT      File containing package specifications
  --python-version TEXT  Target Python version [default: 3.9]
  --platform TEXT        Target platform [default: any]
  --output-dir TEXT      Output directory [default: .]
  --venv-name TEXT       Virtual environment name [default: venv]
  --max-workers INTEGER  Maximum parallel workers [default: 10]
  --timeout INTEGER      HTTP request timeout [default: 10]
  --quiet                Suppress output display
  --requirements-only    Generate only requirements.txt
```

### Utility Commands

```bash
# Display information about the package manager
python pkg_manager.py info
python pkg_manager_parallel.py info

# Show usage examples
python pkg_manager.py example
python pkg_manager_parallel.py example

# Benchmark performance
python pkg_manager_parallel.py benchmark --packages "requests,pandas,numpy" --workers "1,5,10,20"
```

## Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python tests/test_pkg_manager.py

# Test sequential resolution
python pkg_manager.py resolve --packages "requests,pandas" --python-version "3.9"

# Test parallel resolution
python pkg_manager_parallel.py resolve --packages "requests,pandas,numpy" --max-workers 5

# Test file input
python pkg_manager.py resolve --input-file example_packages.txt
```

## Supported Python Versions

- Python 3.7+
- Cross-platform support (Linux, macOS, Windows)

## Dependencies

- **requests**: HTTP client for PyPI API
- **packaging**: Version parsing and comparison
- **pydantic**: Data validation and serialization
- **rich**: Beautiful terminal output
- **typer**: Command-line interface
- **aiohttp**: Async HTTP client (for parallel processing)

## License

MIT 