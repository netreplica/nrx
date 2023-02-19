<p align=center><img src="https://github.com/netreplica/ntopex/raw/main/images/ntopex_concept_diagram.png" width="500px"/></p>

---
[![Discord](https://img.shields.io/discord/1075106069862416525?label=discord)](https://discord.gg/M2SkgSdKht)

# Netreplica ntopex

Network Topology Exporter

Ntopex helps you export network topology graphs from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and create topology files for [Containerlab](https://containerlab.dev) network emulation tool.

## Workflow

Ntopex works in two steps:

1. **Export step**: A graph is exported from NetBox into a file using [CYJS](http://manual.cytoscape.org/en/stable/index.html) format: `<site_name.cyjs>`
2. **Conversion step**: A separate program reads the graph from the CYJS file and creates a Containerlab topology file: `<site_name>.clab.yml`

## Capabilities

Ntopex is in a very early, proof-of-concept phase.

Export capabilities:

* Connects to a NetBox instance over an API using a user-provided authentication token
* Exports a network topology graph for one Site at a time
* Only Devices with Roles from a customizable list will be exported
* Only connections (Cables) between Devices will be exported. Connections to Circuits will be excluded
* Only Ethernet connections will be exported

Conversion capabilities:

* Reads input graph data from a file in CYJS format
* Converts the graph into Containerlab topology definition file in YAML format
* Creates mapping between interface names in the CYJS file (same as in NetBox) and interface names used by Containerlab
* Supported mapping formats: Arista cEOSLab
* Containerlab `kind` and `image` values for all the nodes are statically defined in the Jinja2 template `clab.j2` and currently are set for `ceos`

## Prerequisites

* Python 3.9
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

* Containerlab – not required for `ntopex`, but needed to deploy the topology created

    ```Shell
    bash -c "$(curl -sL https://get.containerlab.dev)"
    ```

## How to install

1. Create venv environment (adjust path to `.venv` folder if needed) 

    ```Shell
    CUR_DIR="${PWD}"
    VENV_DIR="${HOME}/.venv"
    mkdir -p "${VENV_DIR}" && cd "${VENV_DIR}"
    PYENV="ntopex"
    python3.9 -m venv "${PYENV}"
    cd "${CUR_DIR}"
    ```

2. Active venv environment

    ```Shell
    VENV_DIR="${HOME}/.venv"
    PYENV="ntopex"
    source "${VENV_DIR}/${PYENV}/bin/activate"
    ```

3. Clone this repository and install required modules

    ```Shell
    git clone https://github.com/netreplica/ntopex.git
    cd ntopex
    pip3 install -r requirements.txt
    ```

## How to configure

`ntopex` accepts the following configuration options, in the order of precedence:

1. Command-line arguments
2. Environmental variables
3. Configuration file

### Command-line arguments

Note: NB_API_TOKEN is not supported as an argument for security reasons

```Shell
./ntopex.py -h
usage: ntopex.py [-h] [-c CONFIG] [-o OUTPUT] [-a API] [-s SITE] [-d | --debug | --no-debug]

Network Topology Exporter

optional arguments:
-h, --help            show this help message and exit
-c CONFIG, --config CONFIG
                        configuration file
-o OUTPUT, --output OUTPUT
                        export format: gml | cyjs
-a API, --api API     NetBox API URL
-s SITE, --site SITE  NetBox Site to export
-d, --debug, --no-debug
                        enable debug output
```

### Environmental variables 

Environmental variables support NetBox API connection parameters, as an alternative to a configuration file.

```Shell
# NetBox API URL
export NB_API_URL           = 'https://demo.netbox.dev'
# NetBox API Token
export NB_API_TOKEN         = ''
```

### Configuration file

Use `--config <filename>` argument to specify the file to use. Example configuration file is provided as [`ntopex.conf`](ntopex.conf)

```TOML
# NetBox API URL. Alternatively, use --api argument or NB_API_URL environmental variable
NB_API_URL           = 'https://demo.netbox.dev'
# NetBox API Token. Alternatively, use NB_API_TOKEN environmental variable
NB_API_TOKEN         = ''
# Output format to use for export: 'gml' | 'cyjs'. Alternatively, use --output argument
OUTPUT_FORMAT        = 'cyjs'
# List of NetBox Device Roles to export
EXPORT_DEVICE_ROLES  = ['router', 'core-switch', 'access-switch', 'distribution-switch', 'tor-switch']
# NetBox Site to export. Alternatively, use --site argument
EXPORT_SITE          = 'DM-Akron'
```

## How to use

1. Active venv environment

    ```Shell
    VENV_DIR="${HOME}/.venv"
    PYENV="ntopex"
    source "${VENV_DIR}/${PYENV}/bin/activate"
    ```

2. Run `./ntopex.py` to export a topology graph from NetBox. See How to configure for details. Note, you need to use `cyjs` output format for the next step to work. Here is an example of running `ntopex.py` to export a graph for NetBox Site "DM-Albany" from [NetBox Demo](https://demo.netbox.dev) instance:

    ```Shell
    export NB_API_TOKEN='replace_with_valid_API_token'
    ./ntopex.py --api https://demo.netbox.dev --site DM-Albany
    ```

6. Run `./clab.py --file <site>.cyjs` to create a Containerlab topology file from the CYJS graph you exported in the previous step. To keep following the example, run:

    ```Shell
    ./clab.py --file DM-Albany.cyjs
    ```

7. Now you're ready to start the Containerlab topology. Here is the example for "DM-Albany" site

    ```Shell
    sudo -E containerlab deploy -t DM-Albany.clab.yml --reconfigure
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