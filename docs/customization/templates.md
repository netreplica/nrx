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
* `nodes` - Dictionary of all devices/nodes
* `edges` - List of all connections
* `configs` - Device configurations (if exported)

Refer to existing templates in the [netreplica/templates](https://github.com/netreplica/templates) repository for examples of how to use these variables.

## Next Steps

* [Platform Map](platform_map.md) - Configure platform-to-template mappings
* [Examples](../examples/containerlab.md) - See templates in action
* [Templates Repository](https://github.com/netreplica/templates) - Browse available templates
