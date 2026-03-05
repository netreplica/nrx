# Templates

**nrx** renders all topology artifacts using [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/) templates. The user points `nrx` to the set of templates to use with `--templates` parameter.

## Template Search Path

If `--templates` parameter is not provided, **nrx** will search for Jinja2 files in the following locations:

1. `templates` folder in the current directory
2. `$HOME/.nr/templates`

You can also provide an alternative list of folders to search via `TEMPLATES_PATH` parameter in the [configuration file](../userguide/configuration.md).

## Template Organization

Inside the template folders, the required Jinja2 files are taken from a subfolder matching the desired output format. For example:

* Output format `clab` → templates from `clab` subfolder
* Output format `cml` → templates from `cml` subfolder
* Output format `graphite` → templates from `graphite` subfolder

A user can create their own templates for any output format and store them in a subfolder with a format name they would use for `--output` argument.

!!! tip "Custom Output Formats"
    To make a new output format available to **nrx**, an entry describing basic properties of the format must be added to `formats.yaml` file in the `templates` folder.

## Template Types

The full list of template search rules:

### Topology Template (Mandatory)

* **Path**: `<format>/topology.j2`
* **Purpose**: Template for the final topology file
* **Required**: Yes

### Node Templates

* **Path**: `<format>/nodes/<kind>.j2`
* **Purpose**: Templates for individual node entries in the topology file
* **Required**: `default.j2` is mandatory as a fallback template

### Interface Name Templates

* **Path**: `<format>/interface_names/<kind>.j2`
* **Purpose**: Templates for generating emulated interface names used by each `kind`
* **Required**: No (only needed for certain output formats)
* **Fallback**: `default.j2`

Not all output formats need emulated interface names. For example, visualization output formats don't require them.

### Interface Map Templates

* **Path**: `<format>/interface_maps/<kind>.j2`
* **Purpose**: Templates for mappings between real interface names and emulated interface names
* **Required**: No (only certain NOS kinds support such mappings)

## Platform Selection

To identify which template to use for each device in the topology, **nrx** uses the `slug` field of the device's **platform** field in NetBox.

If a template with a name matching the platform `slug` exists, it would be used by default. Since naming of the platforms is unique for every NetBox deployment, it is not possible to create a generic library of templates that could work out-of-the-box for all users.

Instead, **nrx** uses a mapping file [`platform_map.yaml`](platform_map.md) to identify which template to use for each platform, with possible additional parameters like value of the `image` tag for Containerlab nodes.

## Available Templates

The **nrx** repository includes a set of [netreplica/templates](https://github.com/netreplica/templates) as a submodule. These templates support:

### Output Formats

* **Containerlab** (`clab`) - Container-based networking labs
* **Cisco Modeling Labs** (`cml`) - VM-based labs
* **NVIDIA Air** (`air`) - Data center digital twin labs
* **Graphite** (`graphite`) - Network topology visualization
* **D2** (`d2`) - Declarative diagram language
* **CYJS** (`cyjs`) - Cytoscape JSON format

### Supported Network Operating Systems

See the [templates/README.md](https://github.com/netreplica/templates) for a complete list of supported network operating systems and their template kinds.

## Customizing Templates

Although you can directly customize the templates according to your needs, the [platform map file](platform_map.md) often provides a less intrusive way.

### When to Use Platform Map

Use the platform map file when you need to:

* Tell `nrx` which templates to use for specific Device Platform values in your NetBox system
* Override node images instead of the names specified in the templates
* Override other node parameters (memory, CPU, etc.)

### When to Customize Templates

Customize templates directly when you need to:

* Create a completely new output format
* Add custom logic to topology generation
* Modify the structure of generated files

## Creating Custom Templates

To create a custom output format:

1. Create a new subdirectory in your templates folder with your format name
2. Create at minimum a `topology.j2` file
3. Create `nodes/default.j2` for node rendering
4. Add an entry in `formats.yaml` describing your format
5. Use `--output <your_format>` to generate output

### Example formats.yaml Entry

```yaml
myformat:
  description: "My Custom Format"
  file_extension: ".myformat.yaml"
  output_type: "file"
```

## Template Variables

Templates have access to various variables representing the network topology:

* `topology_name` - Name of the topology
* `nodes` - List of all devices/nodes
* `links` - List of all connections between devices
* `roles` - Dictionary grouping devices by role

### Device Fields Available in Templates

Each device in the `nodes` list includes **all fields from NetBox**, plus processed fields for convenience:

#### Commonly Used Fields

**Backward-compatible fields** (extracted for template convenience):

* `name` - Device name (auto-generated if not set)
* `site` - Site name (string)
* `platform` - Platform slug
* `platform_name` - Platform display name
* `model` - Device type slug
* `model_name` - Device type model name
* `vendor` - Manufacturer slug
* `vendor_name` - Manufacturer display name
* `role` - Device role slug
* `role_name` - Device role display name
* `primary_ip4` - Primary IPv4 address (string)
* `primary_ip6` - Primary IPv6 address (string)
* `config` - Rendered device configuration (if enabled)

**nrx-specific fields:**

* `type` - Always "device"
* `node_id` - Internal node identifier
* `device_index` - Device index in the topology
* `level` - Device level (based on role)
* `rank` - Device rank within its role group
* `interfaces` - Dictionary of device interfaces

#### All NetBox Fields

In addition to the above, templates have access to **all raw NetBox device fields**, including:

* `id` - NetBox device ID
* `url` - NetBox API URL for the device
* `display` - Display name
* `device_type` - Full device type object (with id, url, manufacturer details)
* `status` - Device status object
* `serial` - Serial number
* `asset_tag` - Asset tag
* `tenant` - Tenant object (if assigned)
* `location` - Location object (if assigned)
* `rack` - Rack object (if assigned)
* `position` - Position in rack
* `face` - Rack face
* `latitude` - Latitude coordinate
* `longitude` - Longitude coordinate
* `comments` - Comments
* `tags` - List of tag objects
* `custom_fields` - Dictionary of custom field values
* `config_context` - Merged configuration context
* `created` - Creation timestamp
* `last_updated` - Last update timestamp

And many more! Templates can access any field that NetBox provides in its device API response.

!!! tip "Exploring Available Fields"
    To see all available fields for your NetBox version, export a topology as CYJS format (`--output cyjs`) and examine the device data in the resulting JSON file.

### Example Template Usage

```jinja2
{# Access backward-compatible fields #}
{{ node.name }} - {{ node.vendor_name }} {{ node.model_name }}

{# Access NetBox fields directly #}
Serial: {{ node.serial }}
Asset Tag: {{ node.asset_tag }}
Status: {{ node.status.label }}

{# Check custom fields #}
{% if node.custom_fields.environment %}
Environment: {{ node.custom_fields.environment }}
{% endif %}

{# Use tags #}
{% for tag in node.tags %}
  - {{ tag.name }}
{% endfor %}
```

Refer to existing templates in the [netreplica/templates](https://github.com/netreplica/templates) repository for more examples.

## Next Steps

* [Platform Map](platform_map.md) - Configure platform-to-template mappings
* [Examples](../examples/containerlab.md) - See templates in action
* [Templates Repository](https://github.com/netreplica/templates) - Browse available templates
