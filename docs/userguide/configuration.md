# Configuration

**nrx** accepts configuration options in the following order of precedence:

1. [Command-line arguments](#command-line-arguments)
2. [Environmental variables](#environmental-variables)
3. [Configuration file](#configuration-file)

## Command-line Arguments

Command-line arguments take the highest priority.

```bash
nrx --help
```

```
usage: nrx [-h] [-v] [-d] [-I [VERSION]] [-c CONFIG] [-i INPUT] [-o OUTPUT] [-a API] [-s SITE] [-t TAGS] [-n NAME]
           [--noconfigs] [-k | --insecure] [-f FILE] [-M MAP] [-T TEMPLATES] [-D DIR]

nrx - network topology exporter by netreplica

online documentation: https://github.com/netreplica/nrx/blob/main/README.md

optional arguments:
  -h, --help                show this help message and exit
  -v, --version             show version number and exit
  -d, --debug               enable debug output
  -I, --init [VERSION]      initialize configuration directory in $HOME/.nr and exit.
                            optionally, specify a VERSION to initialize with: -I 0.1.0
  -c, --config CONFIG       configuration file, default: $HOME/.nr/nrx.conf
  -i, --input INPUT         input source: netbox (default) | cyjs
  -o, --output OUTPUT       output format: cyjs | air | clab | cml | graphite | d2
                            or any other format supported by provided templates
  -a, --api API             netbox API URL
  -s, --site SITE           netbox site to export, cannot be combined with --sites
      --sites SITES         netbox sites to export, for multiple tags use a comma-separated list:
                            site1,site2,site3 (uses OR logic)
  -t, --tags TAGS           netbox tags to export, for multiple tags use a comma-separated list:
                            tag1,tag2,tag3 (uses AND logic)
      --interface-tags TAGS netbox tags to filter interfaces to export, for multiple tags use a
                            comma-separated list: tag1,tag2,tag3 (uses OR logic)
  -n, --name NAME           name of the exported topology (site name or tags by default)
      --noconfigs           disable device configuration export (enabled by default)
  -k, --insecure            allow insecure server connections when using TLS
  -f, --file FILE           file with the network graph to import
  -T, --templates TEMPLATES directory with template files, will be prepended to TEMPLATES_PATH
                            list in the configuration file
  -M, --map MAP             file with platform mappings to node parameters
                            (default: platform_map.yaml in templates folder)
  -D, --dir DIR             save files into directory DIR (topology name is used by default).
                            nested relative and absolute paths are OK

To pass authentication token, use configuration file or environment variable:
export NB_API_TOKEN='replace_with_valid_API_token'
```

!!! warning "Security Notice"
    For security reasons, there is no command-line argument to pass an API token. Use either an environmental variable or a configuration file.

## Environmental Variables

As an alternative to a configuration file, use environmental variables to provide NetBox API connection parameters.

```bash
# NetBox API URL
export NB_API_URL='https://demo.netbox.dev'

# NetBox API Token
export NB_API_TOKEN='replace_with_valid_API_token'
```

Several file system path parameters can also be set using environmental variables:

- `OUTPUT_DIR`
- `TEMPLATES_PATH`
- `PLATFORM_MAP`

## Configuration File

Use `--config <filename>` argument to specify a configuration file to use. By default, **nrx** uses `$HOME/.nr/nrx.conf` if such file exists.

The sample configuration file is provided as [`nrx.conf`](https://github.com/netreplica/nrx/blob/main/nrx.conf) in the repository.

### Configuration File Format

The configuration file uses TOML format. Here's an example with commonly used options:

```toml
# NetBox API URL. Alternatively, use --api argument or NB_API_URL environmental variable
NB_API_URL = 'https://demo.netbox.dev'

# NetBox API Token. Alternatively, use NB_API_TOKEN environmental variable
NB_API_TOKEN = ''

# Perform TLS certification validation
TLS_VALIDATE = true

# API request timeout, in seconds
API_TIMEOUT = 10

# Netbox API bulk queries optimization
[NB_API_PARAMS]
interfaces_block_size = 4
cables_block_size = 64

# Name of the topology, optional. Alternatively, use --name argument
TOPOLOGY_NAME = 'DemoSite'

# Output format to use for export: 'cyjs' | 'air' | 'clab' | 'cml' | 'graphite' | 'd2'
# Alternatively, use --output argument
OUTPUT_FORMAT = 'clab'

# Override output directory. By default, a subdirectory matching topology name will be created
# Alternatively, use --dir argument. Environment variables are supported
OUTPUT_DIR = '$HOME/nrx'

# Templates search path. Default path is ['./templates','$HOME/.nr/templates']
# Environment variables are supported
TEMPLATES_PATH = ['./templates', '$HOME/.nr/custom', '$HOME/.nr/templates']

# Platform map path. If not provided, 'platform_map.yaml' in the current directory
# is checked first, and then in the TEMPLATES_PATH folders
# Environment variables are supported
PLATFORM_MAP = '$HOME/.nr/platform_map.yaml'

# List of NetBox Device Roles to export
EXPORT_DEVICE_ROLES = ['router', 'core-switch', 'distribution-switch',
                       'access-switch', 'tor-switch', 'server']

# NetBox Site(s) to export. Alternatively, use --sites argument
EXPORT_SITES = ['DM-Akron']

# NetBox tags to export. Alternatively, use --tags argument
EXPORT_TAGS = []

# Export device configurations, when available
EXPORT_CONFIGS = true

# Levels of device roles for visualization
[DEVICE_ROLE_LEVELS]
unknown = 0
server = 0
tor-switch = 1
access-switch = 1
leaf = 1
distribution-switch = 2
spine = 2
core-switch = 3
super-spine = 3
router = 4
```

## Configuration Directory

By default, **nrx** looks for the following assets in the `$HOME/.nr` directory:

* **Configuration file**: `nrx.conf`, unless overridden by `--config` argument
* **Templates**: `templates`, which can be supplemented by additional paths with `--templates` argument

To initialize the configuration directory, run:

```bash
nrx --init
```

This will create the `$HOME/.nr` folder and populate it with:

* A configuration file example (`nrx.conf`)
* A compatible version of the templates in the `templates` subdirectory

### Versioned Initialization

You can optionally specify a version when initializing:

```bash
nrx --init 0.8.0
```

This ensures you get templates compatible with a specific version of nrx.

## Next Steps

* [Containerlab](../examples/containerlab.md) - Export and deploy container-based labs
* [Cisco Modeling Labs](../examples/cml.md) - Export for CML VM-based labs
* [NVIDIA Air](../examples/air.md) - Export for Air digital twin labs
* [Graphite Visualization](../examples/graphite.md) - Visualize network topologies
