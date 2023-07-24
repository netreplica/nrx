# Configuration options for nrx

## Configuration file

Use `--config <filename>` argument to specify a configuration file to use. The sample configuration file is provided as [`nrx.conf`](nrx.conf).

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
NB_API_INTERFACES_BLOCK_SIZE = 4
NB_API_CABLES_BLOCK_SIZE = 64

# Output format to use for export: 'gml' | 'cyjs' | 'clab'. Alternatively, use --output argument
OUTPUT_FORMAT        = 'clab'
# Override output directory. By default, a subdirectory matching topology name will be created. Alternatively, use --dir argument
OUTPUT_DIR           = 'demo'
# Templates path
TEMPLATES_PATH       = ['templates']

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