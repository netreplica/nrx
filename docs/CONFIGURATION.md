# Configuration options for nrx

## Configuration file

Use `--config <filename>` argument to specify a configuration file to use.

## Support for environmental variables

Several parameters in the configuration file that define paths in the file system an be set using environmental variables:

- `OUTPUT_DIR`
- `TEMPLATES_PATH`
- `PLATFORM_MAP`

## Available options

```
# NetBox API URL. Alternatively, use --api argument or NB_API_URL environmental variable
NB_API_URL           = 'https://demo.netbox.dev'
# NetBox API Token. Alternatively, use NB_API_TOKEN environmental variable
NB_API_TOKEN         = ''
# Peform TLS certification validation
TLS_VALIDATE	     = true
# API request timeout, in seconds
API_TIMEOUT          = 10
# Netbox API bulk queries optimization
[NB_API_PARAMS]
interfaces_block_size = 4
cables_block_size =     64

# Output format to use for export: 'gml' | 'cyjs' | 'clab'. Alternatively, use --output argument
OUTPUT_FORMAT        = 'clab'
# Override output directory. By default, a subdirectory matching topology name will be created. Alternatively, use --dir argument. Env vars are supported
OUTPUT_DIR           = '$HOME/nrx'
# Templates search path. Default path is ['./templates','$HOME/.nr/templates']. Env vars are supported
TEMPLATES_PATH       = ['./templates','$HOME/.nr/custom','$HOME/.nr/templates']
# Platform map path. If not provided, 'platform_map.yaml' in the current directory is checked first, and then in the TEMPLATES_PATH folders. Env vars are supported
PLATFORM_MAP         = '$HOME/.nr/platform_map.yaml'

# List of NetBox Device Roles to export
EXPORT_DEVICE_ROLES  = ['router', 'core-switch', 'distribution-switch', 'access-switch', 'tor-switch', 'server']
# NetBox Site to export. Alternatively, use --site argument
EXPORT_SITE          = 'DM-Akron'
# NetBox tags to export. Alternatively, use --tags argument
EXPORT_TAGS          = []
# Export device configurations, when available
EXPORT_CONFIGS       = true

# Levels of device roles for visualization
[DEVICE_ROLE_LEVELS]
unknown =              0
server =               0
tor-switch =           1
access-switch =        1
leaf =                 1
distribution-switch =  2
spine =                2
core-switch =          3
super-spine =          3
router =               4
```