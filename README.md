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

## How to use

1. Create venv environment (adjust path to `.venv` folder if needed)

    ```Shell
    mkdir -p ~/.venv
    cd ~/.venv
    export PYENV=ntopex-py39
    python3.9 -m venv $PYENV; cd $PYENV; export PYENV_DIR=`pwd`; cd $HOME
    source "$PYENV_DIR/bin/activate"
    ```

2. Clone this repository and install required modules

    ```Shell
    git clone https://github.com/netreplica/ntopex.git
    cd ntopex
    pip3 install -r requirements.txt -r requirements_jupyter.txt
    ```

4. Launch a Jupyter server (we're working on CLI-only programs) and connect to its web interface using one of the URLs that will be presented to you

    ```Shell
    jupyter notebook
    ```

5. Open and run [`ntopex.ipynb`](ntopex.ipynb) to export topology graph. Change initial parameters in the first code block to use NetBox instance you have and export the site you need

6. Open and run [`clab.ipynb`](clab.ipynb) to create a Containerlab topology. Change initial parameters in the first code block to match the site name you used in the previous stop

7. Now you're ready to start the Containerlab topology:

    ```Shell
    sudo -E containerlab deploy -t <site_name>.clab.yml --reconfigure
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