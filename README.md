# NetCollector

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

🚨 **This is a Working ALPHA** 🚨

A modern, high-performance network automation tool for collecting and analyzing network device state data. NetCollector provides a streamlined CLI interface for gathering configuration and operational data from network devices, with support for multiple vendors and platforms.

## Features

- **Multi-Vendor Support**: Cisco (IOS-XE, IOS-XR, NX-OS), Arista EOS, Juniper Junos
- **Async Collection**: High-performance concurrent data collection from multiple devices
- **Flexible Authentication**: Support for SSH keys and password authentication
- **Structured Data Output**: Exports data to DuckDB/Parquet format for analysis
- **Extensible Parsing**: TextFSM-based parsing with customizable templates
- **Rich Logging**: Comprehensive logging with timing metrics and structured output
- **Type Safety**: Built with modern Python 3.12+ and comprehensive type hints

## Quick Start

### Installation

```bash
# Assumes Linux or macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install "git+https://github.com/ryanmerolle/netcollector" --forc
```

### Basic Usage

1. **Create an inventory file** (`inventory.yaml`):

```yaml
devices:
  - hostname: switch01
    host: 192.168.1.10
    platform: cisco_nxos
  - hostname: router01
    host: 192.168.1.20
    platform: cisco_iosxe
```

1. **Run data collection**:

```bash
# Using SSH key authentication
netcollector collect --user admin --private-key ~/.ssh/id_rsa

# Using password authentication
netcollector collect --user admin --password
```

2. **View collected data**:

Data is stored in DuckDB format in the `.artifacts/` directory with timestamped filenames.

## Configuration

### Inventory Configuration

The inventory file defines the network devices to collect data from:

```yaml
devices:
  - hostname: spine1-nxos          # Device hostname
    host: 172.29.151.1             # IP address or FQDN
    platform: cisco_nxos           # Platform type
    port: 22                       # SSH port (optional, defaults to 22)
    auth_username: admin           # Username (can be overridden by CLI)
    auth_password: secret          # Password (can be overridden by CLI)
    auth_private_key: ~/.ssh/id_rsa # SSH private key path
    auth_strict_key: false         # SSH strict key checking
    transport: asyncssh            # Transport method
```

**Supported Platforms:**

- `arista_eos`
- `cisco_iosxe`
- `cisco_iosxr`
- `cisco_nxos`
- `juniper_junos`

### Commands Configuration

Commands are defined in `src/netcollector/config/commands.yaml`:

```yaml
platforms:
  cisco_nxos:
    interfaces:
      command: "show interface"
    arp:
      command: "show ip arp detail vrf all"
    version:
      command: "show version"
```

### Application Configuration

Main configuration in `netcollector.yaml`:

```yaml
logging:
  level: INFO
  handlers:
    - console
    - file
artifacts_path: ./.artifacts
max_concurrent_tasks: 10
scrapli_timeout: 30.0
```

## CLI Reference

### collect

Collect data from network devices.

```bash
netcollector collect [OPTIONS]
```

**Authentication Options:**

- `--user, -u`: Username for device authentication
- `--password, -p`: Password for device authentication (prompts securely)
- `--private-key, -pk`: Path to SSH private key
- `--private-key-passphrase, -pkp`: Passphrase for SSH private key

**Configuration Options:**

- `--inventory-file, -i`: Path to inventory file (default: `inventory.yaml`)
- `--config-file, -c`: Path to configuration file (default: `netcollector.yaml`)

**Environment Variables:**
- `NETCOLLECTOR_USER`: Default username
- `NETCOLLECTOR_PASSWORD`: Default password
- `NETCOLLECTOR_AUTH_PRIVATE_KEY`: Default private key path
- `NETCOLLECTOR_PRIVATE_KEY_PASSPHRASE`: Default private key passphrase
- `NETCOLLECTOR_INVENTORY_FILE`: Default inventory file path
- `NETCOLLECTOR_CONFIG_FILE`: Default configuration file path

### export

Export collected data (planned feature).

```bash
netcollector export [OPTIONS]
```

## Project Structure

```bash
netcollector/
├── src/netcollector/
│   ├── cli/                    # Command-line interface
│   ├── collector/              # Data collection logic
│   │   ├── orchestrator.py     # Main collection workflow
│   │   ├── parsers.py          # Output parsing (TextFSM)
│   │   ├── factories.py        # Component factories
│   │   └── interfaces.py       # Abstract interfaces
│   ├── config/                 # Configuration management
│   │   ├── commands.yaml       # Command definitions
│   │   ├── inventory.py        # Device inventory models
│   │   └── config.py           # Application configuration
│   ├── exporter/               # Data export functionality
│   ├── processor/              # Data processing and analysis
│   └── utils/                  # Utility functions
├── tests/                      # Test suite
└── .artifacts/                 # Output directory (auto-created)
```

## Development

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd netcollector

# Install dependencies
uv sync

# Install pre-commit hooks (recommended)
pre-commit install
```

### Development Tasks

```bash
# Run all checks
task check

# Individual tasks
uv run ruff check src/ --fix          # Linting
uv run ruff format .                  # Code formatting
uv run pytest                        # Run tests
uv run coverage report               # Coverage report
```

### Code Quality

This project enforces strict code quality standards:

- **Linting**: Ruff with comprehensive rule set
- **Formatting**: Ruff format (88 character line length)
- **Type Checking**: Full type annotations required
- **Testing**: pytest with high coverage requirements (80%+)
- **Documentation**: Google-style docstrings

## Architecture

### Core Components

1. **CLI**: Command-line interface built with Typer
2. **Collector**: Async data collection using Scrapli
3. **Parser**: TextFSM-based output parsing
4. **Normalizer**: Data normalization and enrichment
5. **Exporter**: DuckDB/Parquet data storage
6. **Config**: Pydantic-based configuration management

### Data Flow

1. **Inventory Loading**: Load device definitions from YAML
2. **Command Resolution**: Map platform-specific commands
3. **Async Collection**: Connect to devices and execute commands
4. **Parsing**: Parse command output using TextFSM templates
5. **Normalization**: Clean and enrich data with metadata
6. **Storage**: Store in DuckDB with Parquet backend

### Key Design Principles

- **Async-First**: Built for high-performance concurrent operations
- **Type Safety**: Comprehensive type hints throughout
- **Modular Design**: Clean separation of concerns
- **Configuration-Driven**: YAML-based device and command configuration
- **Extensible**: Plugin architecture for parsers and exporters

## Examples

### Basic Collection

```bash
# Collect from all devices in inventory
netcollector collect --user admin --password

# Collect with SSH key
netcollector collect --user admin --private-key ~/.ssh/network_key

# Use custom inventory file
netcollector collect --user admin --password --inventory-file lab-devices.yaml
```

### Advanced Usage

```bash
# Set custom artifacts directory via config
echo "artifacts_path: /data/network-snapshots" > custom-config.yaml
netcollector collect --config-file custom-config.yaml --user admin --password

# Use environment variables
export NETCOLLECTOR_USER=admin
export NETCOLLECTOR_PASSWORD=secret
netcollector collect
```

## Data Analysis

Collected data is stored in DuckDB format for easy analysis:

```python
import duckdb

# Connect to collected data
conn = duckdb.connect('.artifacts/netcollector_20250530_143022.duckdb')

# Query interface data
interfaces = conn.execute("""
    SELECT hostname, interface, admin_state, link_status 
    FROM cisco_nxos_interfaces 
    WHERE link_status = 'up'
""").fetchall()

# Export to pandas for analysis
import pandas as pd
df = conn.execute("SELECT * FROM cisco_nxos_interfaces").df()
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes following the code style guidelines
4. Run tests: `task check`
5. Commit changes: `git commit -am 'Add feature'`
6. Push to branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Additional documentation in the `docs/` directory
- **Examples**: Sample configurations in the `examples/` directory

---

**NetCollector** - Modern network automation for the data-driven network engineer.
