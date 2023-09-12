<p align=center><img src="https://github.com/netreplica/nrx/raw/main/images/concept_diagram.png" width="500px"/></p>

---
[![Discord](https://img.shields.io/discord/1075106069862416525?label=discord)](https://discord.gg/M2SkgSdKht)
[![CI](https://github.com/netreplica/nrx/actions/workflows/systest.yml/badge.svg)](https://github.com/netreplica/nrx/actions/workflows/systest.yml)

# nrx - netreplica exporter

**nrx** reads a network topology graph from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and exports it in one of the following formats:

* Topology file for [Containerlab](https://containerlab.dev) tool for container-based networking labs
* Topology file for [Cisco Modeling Labs](https://developer.cisco.com/modeling-labs/) platform for network simulation
* Topology data for visualization using [Graphite](https://github.com/netreplica/graphite) or [D2](https://d2lang.com/)
* Graph data as a JSON file in [Cytoscape](https://cytoscape.org/) format [CYJS](http://manual.cytoscape.org/en/stable/Supported_Network_File_Formats.html#cytoscape-js-json)
* Any other user-defined format using [Jinja2](https://palletsprojects.com/p/jinja/) templates

It can also read the topology graph previously saved as a CYJS file to convert it into other formats.

This project is in early phase. We're experimenting with the best ways to automate software network lab orchestration. If you have any feedback, questions or suggestions, please reach out to us via the Netreplica Discord server linked above, [#netreplica](https://netdev-community.slack.com/archives/C054GKBC4LB) channel in NetDev Community on Slack, or open a github issue in this repository.

# Latest capabilities added

The last release adds the following capabilities:
* User-defined output formats using Jinja2 templates

Find detailed release notes on the [Releases page](https://github.com/netreplica/nrx/releases).

# Table of contents

* [Capabilities](#capabilities)
* [Compatibility](#compatibility)
* [Prerequisites](#prerequisites)
* [How to install](#how-to-install)
* [How to configure](#how-to-configure)
   * [Command-line arguments](#command-line-arguments)
   * [Environmental variables](#environmental-variables)
   * [Configuration file](#configuration-file)
* [Templates](#templates)
* [How to use](#how-to-use)
   * [Containerlab example](#containerlab-example)
   * [Cisco Modeling Labs example](#cisco-modeling-labs-example)
   * [Topology Visualization with Graphite](#topology-visualization-with-graphite)
* [Credits](#credits)
   * [Original idea and implementation](#original-idea-and-implementation)
   * [Copyright notice](#copyright-notice)

# Capabilities

Data sourcing capabilities:

* Connects to a NetBox instance over an API using a user-provided authentication token
* Exports a network topology graph for
    * a specific Site
    * multiple Sites interconnected via point-2-point Circuits
* Only Devices with Roles from a customizable list will be exported
* Uses Tags to further narrow down a list of Devices for export
* Direct connections between Devices via Cables will be exported as topology edges
* Connections via Patch Panels and Circuits will be exported as well with help of NetBox [Cable Tracing API](https://docs.netbox.dev/en/stable/models/dcim/cable/#tracing-cables)
* Only Ethernet connections will be exported
* Device configurations will be rendered and exported if not empty
* As an alternative to sourcing live data from NetBox, imports a graph from a previously exported file in CYJS format

Export capabilities:

* Exports the graph as a Containerlab topology definition file in YAML format
* Exports the graph as a Cisco Modeling Labs (CML) topology definition file in YAML format
* Exported device configurations will be used as `startup-config` for Containerlab and CML
* Exports the graph in formats for visualization with Graphite or D2
* User-defined output formats using Jinja2 templates
* Uses NetBox Device Platform `slug` field to identify node templates when rendering the export file
* Creates mapping between real interface names and interface names used by the supported lab tools
* Calculates `level` and `rank` values for each node based on Device Role to help visualize the topology
* Exports the graph into CYJS format that can be later converted into a topology definition file, or used by 3rd party software

# Compatibility

The following software versions were tested for compatibility with `nrx`:

* NetBox `v3.4`-`v3.5`. For device configuration export, `v3.5` is the minimum version.
* Containerlab `v0.39`, but earlier and later versions should work fine
* Cisco Modeling Labs `v2.5`
* Netreplica Graphite `v0.4.0`

# Prerequisites

* Python 3.9+. In the commands below we assume use have `python3.9` executable. If you have a different name, change accordingly.
* PIP

    ```Shell
    curl -sL https://bootstrap.pypa.io/get-pip.py | python3.9 -
    ```

* Virtualenv (recommended)

    ```Shell
    pip install virtualenv
    ```

* [Containerlab](https://containerlab.dev/) – not required for **nrx**, but is needed to deploy Containerlab topologies

    ```Shell
    bash -c "$(curl -sL https://get.containerlab.dev)"
    ```

* [Cisco Modeling Labs](https://developer.cisco.com/modeling-labs/) – not required for **nrx**, but is needed to deploy CML topologies

* [Netreplica Graphite](https://github.com/netreplica/graphite) – not required for **nrx**, but is needed for topology visualization

# How to install

1. Clone this repository and create Python virtual environment

    ```Shell
    git clone https://github.com/netreplica/nrx.git --recursive
    cd nrx
    python3.9 -m venv nrx39
    source nrx39/bin/activate
    ```

2. Install required modules

    ```Shell
    pip3 install -r requirements.txt
    ```

# How to configure

**nrx** accepts the following configuration options, in the order of precedence:

1. [Command-line arguments](#command-line-arguments)
2. [Environmental variables](#environmental-variables)
3. [Configuration file](#configuration-file)

## Command-line arguments

Command-line arguments take the highest priority.

```
./nrx.py --help
usage: nrx [-h] [-c CONFIG] [-i INPUT] [-o OUTPUT] [-a API] [-s SITE] [-k] [-d] [-f FILE] [-T TEMPLATES]

nrx - network topology exporter by netreplica

optional arguments:
  -h, --help                show this help message and exit
  -c, --config CONFIG       configuration file
  -i, --input INPUT         input source: netbox (default) | cyjs
  -o, --output OUTPUT       output format: cyjs for JSON, or any other format supported by provided templates
  -a, --api API             netbox API URL
  -s, --site SITE           netbox site to export
  -t, --tags TAGS           netbox tags to export, for multiple tags use a comma-separated list: tag1,tag2,tag3 (uses AND logic)
  -n, --noconfigs           disable device configuration export (enabled by default)
  -k, --insecure            allow insecure server connections when using TLS
  -d, --debug               enable debug output
  -f, --file FILE           file with the network graph to import
  -T, --templates TEMPLATES directory with template files, will be prepended to TEMPLATES_PATH list in the configuration file
  -D, --dir DIR             save files into directory DIR (topology name is used by default). nested relative and absolute paths are OK
```

Note: `NB_API_TOKEN` is not supported as an argument for security reasons.

## Environmental variables

As an alternative to a configuration file, use environmental variables to provide NetBox API connection parameters.

```Shell
# NetBox API URL
export NB_API_URL='https://demo.netbox.dev'
# NetBox API Token
export NB_API_TOKEN='replace_with_valid_API_token'
```

## Configuration file

Use `--config <filename>` argument to specify a configuration file to use. The sample configuration file is provided as [`nrx.conf`](nrx.conf). Detailed information on the configuration options can be found in [CONFIGURATION.md](docs/CONFIGURATION.md).

# Templates

**nrx** renders all topology artifacts from [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/) templates. Depending on the desired output format, the required templates are taken from a matching subfolder. For example, if the output format is `clab` for Containerlab, then templates are searched under `clab` subfolder. For Cisco Modelling Labs `cml` format the subfolder would be `cml`. A user can create their own templates for any output format and store them in a subfolder with a format name they would use for `--output` argument.

Most templates are unique for each node `kind`. Value of `kind` is taken from NetBox `device.platform.slug` field. The full list of template search rules:

* `<format>/topology.j2`: template for the final topology file. Mandatory.
* `<format>/kinds/<kind>.j2`: templates for individual node entries in the topology file, with `default.j2` being mandatory as a fallback template.
* `<format>/interface_names/<kind>.j2`: templates for generating emulated interface names used by this NOS `kind` with `default.j2` being a fallback template. Optional, as not all formats need emulated interface names.
* `<format>/interface_maps/<kind>.j2`: templates for mappings between real interface names and emulated interface names used by this NOS `kind`. Optional, as not all `kinds` support such mappings.

This repository includes a set of [netreplica/templates](https://github.com/netreplica/templates) as a submodule. See more details about available templates in the [templates/README.md](https://github.com/netreplica/templates).

By default, **nrx** searches for the template files in the current directory. You can provide a list of folders to search for the templates via `TEMPLATES_PATH` parameter in the [configuration file](#configuration-file), or use `--templates` argument.

# How to use

Start with activating venv environment

```Shell
source nrx39/bin/activate
```

## Containerlab example

1. Run `./nrx.py --output clab` to export a topology graph from NetBox in Containerlab format. See [How to configure](#how-to-configure) for details. Here is an example of running `nrx.py` to export a graph for NetBox Site "DM-Albany" from [NetBox Demo](https://demo.netbox.dev) instance:

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.py --api https://demo.netbox.dev --templates templates --output clab --dir demo --site DM-Albany
    ```

2. Now you're ready to start the Containerlab topology. Here is the example for "DM-Albany" site

    ```Shell
    sudo -E containerlab deploy -t demo/DM-Albany.clab.yaml --reconfigure
    ```

3. Without `--output clab` argument, `nrx.py` will save data from NetBox as a CYJS file `<site_name>.cyjs`

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.py --api https://demo.netbox.dev --site DM-Albany --dir demo
    ```

5. If you have a CYJS file, run `./nrx.py --input cyjs --file <site>.cyjs --output clab` to create a Containerlab topology file from the CYJS graph you exported in the previous step. For example, run:

    ```Shell
    ./nrx.py --input cyjs --file demo/DM-Albany.cyjs --templates templates --output clab --dir demo
    ```

## Cisco Modeling Labs example

1. Run `./nrx.py --output cml` to export a topology graph from NetBox in CML format. See [How to configure](#how-to-configure) for details. Here is an example of running `nrx.py` to export a graph for NetBox Site "DM-Akron" from [NetBox Demo](https://demo.netbox.dev) instance:

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.py --api https://demo.netbox.dev --templates templates --output cml --dir demo --site DM-Akron
    ```

2. Now you're ready to start the "DM-Akron" topology in CML.

    * Open your CML Dashboard in a browser
    * Choose "IMPORT"
    * Use `DM-Akron.cml.yaml` as a file to import. The import status should be Imported.
    * Choose "GO TO LAB". In SIMULATE menu, choose START LAB
    * Use NODES menu to monitor the status of each node

3. Without `--output cml` argument, `nrx.py` will save data from NetBox as a CYJS file `<site_name>.cyjs`

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.py --api https://demo.netbox.dev --dir demo --site DM-Akron
    ```

4. If you have a CYJS file, run `./nrx.py --input cyjs --file <site>.cyjs --output cml` to create a topology file from the CYJS graph you exported in the previous step. For example, run:

    ```Shell
    ./nrx.py --input cyjs --file demo/DM-Akron.cyjs --templates templates --output cml --dir demo
    ```

## Topology Visualization with Graphite

A combination of **netreplica** `nrx` and [`graphite`](https://github.com/netreplica/graphite) tools can be used to visualize NetBox topology data. Unlike typical plugin-based visualizers, this method can work with a standard NetBox instance without any plugins installed. You also don't need an administrative access to the NetBox host in order to use this type of visualization.

Follow a two-step process:

1. Export topology data from NetBox in the Graphite format: `nrx.py -o graphite`. For example, let's export "DM-Akron" site from the [NetBox Demo](https://demo.netbox.dev) instance:

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.py --api https://demo.netbox.dev --site DM-Akron --templates templates --output graphite
    ```

2. Start Graphite to visualize "DM-Akron" site:

    ```Shell
    TOPOLOGY="$(pwd)/DM-Akron.graphite.json"
    docker run -d -t --rm \
        --mount type=bind,source="${TOPOLOGY}",target=/htdocs/default/default.json,readonly \
        -p 8080:80 \
        --name graphite \
        netreplica/graphite:latest
    ```

    Open [http://localhost:8080/graphite](http://localhost:8080/graphite) to see the topology. If you're running Graphite on a remote host, or inside a VM, use this helper to show a working URL:

    ```Shell
    docker exec -t -e HOST_CONNECTION="${SSH_CONNECTION}" graphite graphite_motd.sh 8080
    ```

    The visualization should be similar to

    ![DM-Akron Diagram](images/graphite_topology.png)

    To stop Graphite, run

    ```Shell
    docker stop graphite
    ```


If you'd like to be able to switch between multiple exported topologies without restarting Graphite, use one of the methods described in [Graphite documentation](https://github.com/netreplica/graphite/blob/main/docs/DOCKER.md).

# Credits

## Original idea and implementation

This is a [NANOG-87 Hackathon](https://www.nanog.org/events/nanog-87-hackathon/) project. The original project [slides](https://docs.google.com/presentation/d/1-WcKsDuaFh3tozmTdTxGYXjMFuthRyevsRZbIc2j2Kw/edit?usp=sharing). The project team:

* [Alex Bortok](https://github.com/bortok)
* [Chip Gwyn](https://github.com/chipgwyn)
* [Toni Yannick Kalombo](https://github.com/tonikalombo)

The implementation is inspired by [ContainerLab random labs](https://gist.github.com/renatoalmeidaoliveira/fdb772a5a02f3cfc0b5fbe7e8b7586a2) by [Renato Almeida de Oliveira](https://github.com/renatoalmeidaoliveira).

## Device configuration export

We added capabilities to export device configurations at [NANOG-88 Hackathon](https://www.nanog.org/events/nanog-88-hackathon/). The project team:

* [Alex Bortok](https://www.linkedin.com/in/bortok/)
* [Mau Rojas](https://www.linkedin.com/in/pinrojas/)
* [Ahmed Elmokashfi](https://www.linkedin.com/in/elmokashfi/)

Watch [the demo of the project on YouTube](https://youtu.be/cP8PUr306ZM):

[![Watch the video](https://img.youtube.com/vi/cP8PUr306ZM/maxresdefault.jpg)](https://youtu.be/cP8PUr306ZM)

## Copyright notice

Copyright 2023 Netreplica Team

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.