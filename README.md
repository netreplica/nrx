<p align=center><img src="https://github.com/netreplica/nrx/raw/main/images/concept_diagram.png" width="500px"/></p>

---
[![Discord](https://img.shields.io/discord/1075106069862416525?label=discord)](https://discord.gg/M2SkgSdKht)

# nrx - network topology exporter by netreplica

**nrx** reads a network topology graph from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and exports it in one of the following formats:

* Topology file for [Containerlab](https://containerlab.dev) network emulation tool
* Graph data as a JSON file in [Cytoscape](https://cytoscape.org/) format [CYJS](http://manual.cytoscape.org/en/stable/Supported_Network_File_Formats.html#cytoscape-js-json)

It can also read the topology graph previously saved as a CYJS file to convert it into Containerlab format.

## Capabilities

**nrx** is in a very early, proof-of-concept phase.

Data sourcing capabilities:

* Connects to a NetBox instance over an API using a user-provided authentication token
* Exports a network topology graph for one Site at a time
* Only Devices with Roles from a customizable list will be exported
* Only connections (Cables) between Devices will be exported. Connections to Circuits will be excluded
* Only Ethernet connections will be exported
* Instead of querying live data from NetBox, import the graph from a file in CYJS format

Export capabilities:

* Exports the graph as a Containerlab topology definition file in YAML format
* Uses NetBox Device Platform to identify Containerlab node settings
* Creates mapping between real interface names and interface names used by Containerlab
* Exports the graph into CYJS format that can be later converted into a Containerlab topology, or used by 3rd party software

## Prerequisites

* Python 3.9+
* PIP

    ```Shell
    cd /tmp
    wget https://bootstrap.pypa.io/get-pip.py
    python3.9 get-pip.py
    ```

* Virtualenv (recommended)

    ```Shell
    pip install virtualenv
    ```

* Containerlab – not required for **nrx**, but needed to deploy the topology created

    ```Shell
    bash -c "$(curl -sL https://get.containerlab.dev)"
    ```

## How to install

1. Clone this repository and create Python virtual environment

    ```Shell
    git clone https://github.com/netreplica/nrx.git
    cd nrx
    python3.9 -m venv nrx39
    source nrx39/bin/activate
    ```

2. Install required modules

    ```Shell
    pip3 install -r requirements.txt
    ```

## How to configure

**nrx** accepts the following configuration options, in the order of precedence:

1. [Command-line arguments](#command-line-arguments)
2. [Environmental variables](#environmental-variables)
3. [Configuration file](#configuration-file)

### Command-line arguments

Command-line arguments take the highest priority.

```
./nrx.sh --help
usage: nrx [-h] [-c CONFIG] [-i INPUT] [-o OUTPUT] [-a API] [-s SITE] [-k | --insecure | --no-insecure] [-d | --debug | --no-debug] [-f FILE] [-t TEMPLATES]

nrx - network topology exporter by netreplica

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        configuration file
  -i INPUT, --input INPUT
                        input source: netbox (default) | cyjs
  -o OUTPUT, --output OUTPUT
                        output format: cyjs | gml | clab
  -a API, --api API     netbox API URL
  -s SITE, --site SITE  netbox site to export
  -k, --insecure, --no-insecure
                        allow insecure server connections when using TLS
  -d, --debug, --no-debug
                        enable debug output
  -f FILE, --file FILE  file with the network graph to import
  -t TEMPLATES, --templates TEMPLATES
                        directory with template files, will be prepended to TEMPLATES_PATH list in the configuration file
```

Note: `NB_API_TOKEN` is not supported as an argument for security reasons.

### Environmental variables

As an alternative to a configuration file, use environmental variables to provide NetBox API connection parameters.

```Shell
# NetBox API URL
export NB_API_URL           = 'https://demo.netbox.dev'
# NetBox API Token
export NB_API_TOKEN         = 'replace_with_valid_API_token'
```

### Configuration file

Use `--config <filename>` argument to specify a configuration file to use. The sample configuration file is provided as [`nrx.conf`](nrx.conf).

## Templates

### Containerlab

All elements of a Containerlab topology file that **nrx** can produce has to be provided to it as Jinja2 templates:

* `clab/topology.j2`: template for the final Containerlab topology file
* `clab/kinds/<device.platform.slug>.j2`: templates for Clab node entries, separate file for each `device.platform.slug` exported from NetBox
* `interface_maps/<device.platform.slug>.j2`: templates for mappings between real interface names and interface names used by Containerlab

This repository provides a small set of such templates as examples. To customize the way Containerlab topology file should be generated, you would need to change these templates as needed. For example, you might want to change `image` values depending on the `kind`. You can also add new templates, if the platforms you have are not covered by the provided set of templates. In case a template for the needed `kind` already exists, but in NetBox you're using a different `device.platform.slug` value for it, you can either rename the template, or create a symbolic link to it with a new name.

By default, **nrx** searches for the template files in the current directory. You can provide a list of folders to search for the templates via `TEMPLATES_PATH` parameter in the [configuration file](#configuration-file), or use `--templates` argument.

## How to use

1. Activate venv environment

    ```Shell
    source nrx39/bin/activate
    ```

2. Run `./nrx.sh --output clab` to export a topology graph from NetBox in a Containerlab format. See [How to configure](#how-to-configure) for details. Here is an example of running `nrx.py` to export a graph for NetBox Site "DM-Albany" from [NetBox Demo](https://demo.netbox.dev) instance:

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.sh --api https://demo.netbox.dev --site DM-Albany --output clab
    ```

3. Now you're ready to start the Containerlab topology. Here is the example for "DM-Albany" site

    ```Shell
    sudo -E containerlab deploy -t DM-Albany.clab.yml --reconfigure
    ```

4. Without `--output clab` argument, `nrx.py` will save data from NetBox as a CYJS file `<site_name>.cyjs`

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./nrx.sh --api https://demo.netbox.dev --site DM-Albany
    ```

5. If you have a CYJS file, run `./nrx.sh --input cyjs --file <site>.cyjs --output clab` to create a Containerlab topology file from the CYJS graph you exported in the previous step. For example, run:

    ```Shell
    ./nrx.sh --input cyjs --file DM-Albany.cyjs --output clab
    ```

# Credits

## Original idea and implementation

This is a [NANOG-87 Hackathon](https://www.nanog.org/events/nanog-87-hackathon/) project. The original project [slides](https://docs.google.com/presentation/d/1-WcKsDuaFh3tozmTdTxGYXjMFuthRyevsRZbIc2j2Kw/edit?usp=sharing). The project team:

* [Alex Bortok](https://github.com/bortok)
* [Chip Gwyn](https://github.com/chipgwyn)
* [Toni Yannick Kalombo](https://github.com/tonikalombo)

The implementation is inspired by [ContainerLab random labs](https://gist.github.com/renatoalmeidaoliveira/fdb772a5a02f3cfc0b5fbe7e8b7586a2) by [Renato Almeida de Oliveira](https://github.com/renatoalmeidaoliveira).

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