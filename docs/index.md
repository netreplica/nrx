# nrx - netreplica exporter

<p align=center><img src="https://github.com/netreplica/nrx/raw/main/images/concept_diagram.png" width="500px"/></p>

[![Discord](https://img.shields.io/discord/1075106069862416525?label=discord)](https://discord.gg/M2SkgSdKht)
[![CI](https://github.com/netreplica/nrx/actions/workflows/systest.yml/badge.svg)](https://github.com/netreplica/nrx/actions/workflows/systest.yml)

**nrx** reads a network topology graph from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and exports as one of the following:

* [Containerlab](https://containerlab.dev) topology for container-based networking labs
* [NVIDIA Air](https://www.nvidia.com/en-us/networking/ethernet-switching/air/) topology for data center digital twin labs
* [Cisco Modeling Labs](https://developer.cisco.com/modeling-labs/) topology for VM-based labs
* Network visualization format for [Graphite](https://github.com/netreplica/graphite) or [D2](https://d2lang.com/)
* Graph data as a JSON file in [Cytoscape](https://cytoscape.org/) format [CYJS](http://manual.cytoscape.org/en/stable/Supported_Network_File_Formats.html#cytoscape-js-json)
* Any other user-defined format using [Jinja2](https://palletsprojects.com/p/jinja/) templates

It can also read the topology graph previously saved as a CYJS file to convert it into other formats.

!!! info "Early Phase Project"
    This project is in early phase. We're experimenting with the best ways to automate software network lab orchestration. If you have any feedback, questions or suggestions, please reach out to us via the Netreplica Discord server, [#netreplica](https://netdev-community.slack.com/archives/C054GKBC4LB) channel in NetDev Community on Slack, or open a GitHub issue.

## Latest Capabilities

The latest releases have a significant set of new capabilities:

* **0.8.0** - NVIDIA Air support
* **0.7.0** - NetBox v4.2 compatibility. Bug fixes. Minimum Python version 3.10
* **0.6.2** - NetBox v4.1 compatibility
* **0.6.0** - Filter links between devices via interface tags
* **0.5.0** - PyPA packaging and distribution: `pip install nrx`
* **0.4.0** - Ability to create new output formats without code changes
* **0.4.0** - Mapping between NetBox platform values and node parameters via [`platform_map.yaml`](platform_map.md)
* **0.4.0** - `$HOME/.nr` configuration directory with automatic initialization using `--init` argument

Find detailed release notes on the [Releases page](https://github.com/netreplica/nrx/releases).

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

## Quick Start

For detailed installation instructions, see the [Installation Guide](installation.md).

### Using uv (fast)

```bash
# Install nrx as a persistent tool
uv tool install nrx
nrx --version

# Or run nrx directly without installation
uv tool run nrx --version
```

### Using pip (traditional)

```bash
mkdir -p ~/.venv
python3.10 -m venv ~/.venv/nrx
source ~/.venv/nrx/bin/activate
pip install nrx
nrx --version
```

## Next Steps

* [Installation Guide](installation.md) - Detailed installation instructions
* [Configuration](CONFIGURATION.md) - How to configure nrx
* [Templates](templates.md) - Understanding and customizing templates
* [Examples](examples/containerlab.md) - Step-by-step usage examples
