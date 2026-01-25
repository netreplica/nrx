<p align=center><img src="https://github.com/netreplica/nrx/raw/main/images/concept_diagram.png" width="500px"/></p>

<!--p ><h1 align=center>nrx - netreplica exporter</h1></p-->

**nrx** reads data center inventory from [NetBox](https://docs.netbox.dev/en/stable/) and exports as one of:

* [Containerlab](https://containerlab.dev) topology for container-based networking labs
* [NVIDIA Air](https://www.nvidia.com/en-us/networking/ethernet-switching/air/) topology for data center digital twin labs
* [Cisco Modeling Labs](https://developer.cisco.com/modeling-labs/) topology for VM-based labs
* Network visualization format for [Graphite](https://github.com/netreplica/graphite) or [D2](https://d2lang.com/)
* Graph data as a JSON file in [Cytoscape](https://cytoscape.org/) format [CYJS](http://manual.cytoscape.org/en/stable/Supported_Network_File_Formats.html#cytoscape-js-json)
* Any other user-defined format using [Jinja2](https://palletsprojects.com/p/jinja/) templates

It can also read a topology data previously saved as a CYJS file to convert it into other formats.

## Latest Updates

* **0.8.0** - NVIDIA Air export format.
* **0.7.0** - NetBox v4.2 compatibility. Bug fixes. Minimum Python version 3.10
* **0.6.0** - Filter links between devices via interface tags

Find detailed release notes on the [Releases page](https://github.com/netreplica/nrx/releases).

## Quick Start

### Install

For detailed installation instructions, see the [Installation Guide](userguide/installation.md).

```bash
uv tool install nrx
nrx --init
```

### Connect to NetBox

In this example we're using NetBox [Demo](https://demo.netbox.dev) instance to source data. Login to the demo instance, [create an API token](https://demo.netbox.dev/users/tokens/) and set it as an environment variable:

```bash
export NB_API_URL='https://demo.netbox.dev'
export NB_API_TOKEN='replace_with_valid_API_token'
```

### Export Containerlab topology

Run `nrx --output clab` to export a topology graph from NetBox in Containerlab format. Here's an example exporting the "DM-Albany" site:

```bash
nrx --output clab --site DM-Albany
```

This will create:

* `DM-Albany/DM-Albany.clab.yaml` - Containerlab topology file

### Deploy the Topology

Deploy the topology using Containerlab:

```bash
sudo -E clab deploy -t DM-Albany/DM-Albany.clab.yaml
```

## Key Capabilities

### Data Sourcing

* Connects to a NetBox instance over API using a user-provided authentication token
* Exports a network topology graph with Devices that:
    * belong to a Site specified with `--site` parameter
    * have a list of Tags specified with `--tags` parameter
* A combination of the two methods above is possible
* Only Devices with Roles from a customizable list will be exported
* Direct connections between Devices via Cables will be exported as topology edges
* Connections via Patch Panels and Circuits will be exported as well with help of NetBox [Cable Tracing API](https://docs.netbox.dev/en/stable/models/dcim/cable/#tracing-cables)
* Only Ethernet connections will be exported
* Device configurations will be rendered and exported if not empty
* As an alternative to sourcing live data from NetBox, imports a graph from a previously exported file in CYJS format

### Export Capabilities

* Exports the graph as a Containerlab (Clab) topology definition file in YAML format
* Exports the graph as a NVIDIA Air topology definition file in JSON format
* Exports the graph as a Cisco Modeling Labs (CML) topology definition file in YAML format
* Exported device configurations can be used as `startup-config` for Containerlab and CML
* Exports the graph in formats for visualization with Graphite or D2
* User-defined output formats using Jinja2 templates
* Uses NetBox Device Platform `slug` field to identify node templates when rendering the export file
* Customizable mapping between NetBox Platform values and node parameters via `platform_map.yaml` file
* Creates mapping between real interface names and interface names used by the supported lab tools
* Calculates `level` and `rank` values for each node based on Device Role to help visualize the topology
* Exports the graph into CYJS format that can be later converted into a topology definition file, or used by 3rd party software

## Compatibility

The following software versions were tested for compatibility with `nrx`:

* **NetBox** v4.1-v4.2 (previously supported v3.4-4.0 versions are no longer tested)
* **Containerlab** v0.39 (earlier and later versions should work fine)
* **NVIDIA Air** API v9.15.8+ (API v2 is used)
* **Cisco Modeling Labs** v2.5
* **Netreplica Graphite** v0.4.0

## Next Steps

* [Installation Guide](userguide/installation.md) - Detailed installation instructions
* [Configuration](userguide/configuration.md) - How to configure nrx
* [Templates](customization/templates.md) - Understanding and customizing templates
* [Examples](examples/containerlab.md) - Step-by-step usage examples
