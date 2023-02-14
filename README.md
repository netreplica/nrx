<p align=center><img src="https://raw.githubusercontent.com/netreplica/ntopex/readme/images/ntopex_concept_diagram.png" width="500px"/></p>

---

# Netreplica ntopex

Network Topology Exporter

Ntopex helps you export network topology graphs from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and create topology files for [Containerlab](https://containerlab.dev) network emulation tool. This is a [NANOG-87 Hackathon project](https://docs.google.com/presentation/d/?1-WcKsDuaFh3tozmTdTxGYXjMFuthRyevsRZbIc2j2Kw/edit?usp=sharing).

## Capabilities

Ntopex works in two steps:

1. Export step. A graph is exported from NetBox into a file using a [GML](https://networkx.org/documentation/stable/reference/readwrite/gml.html) as well as [CYJS](http://manual.cytoscape.org/en/stable/index.html) formats.
2. Conversion step. A separate program read the graph from a CYJS file and creates a Containerlab topology file

Ntopex is in a very early, proof-of-concept phase.

Export capabilities:

* Connecting to a NetBox instance over an API using a user-provided authentication token
* Exporting a network topology graph for one Site at a time
* Only Devices with Roles from a customizable list will be exported
* Only connections (Cables) between Devices will be exported. Connections to Circuits will be excluded
* Only Ethernet connections will be exported

Conversion capabilities:

* Read input graph data from a file in CYJS format
* Convert the graph into Containerlab topology definition file in YAML format
* Create mapping between interface names in the CYJS file (same as in NetBox) and interface names used by Containerlab
* Currently supported mapping formats: Arista cEOSLab
* Containerlab `kind` and `image` values for all the nodes are statically defined in the Jinja2 template `clab.j2` and currently are set for `ceos`

## Prerequisites

```Shell
python3.9 -V
pip -V
cd /tmp
wget https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py
pip -V
pip install virtualenv
```

## Create venv environment

```Shell
mkdir -p ~/.venv
cd ~/.venv
export PYENV=ntopex-py39
python3.9 -m venv $PYENV; cd $PYENV; export PYENV_DIR=`pwd`
source "$PYENV_DIR/bin/activate"
```

Create venv environment for Jupyter

```Shell
mkdir -p ~/.venv
cd ~/.venv
export PYENV=ntopex-jup39
python3.9 -m venv $PYENV; cd $PYENV; export PYENV_DIR=`pwd`
source "$PYENV_DIR/bin/activate"
```

Clone and initialize venv
```Shell
git clone https://github.com/netreplica/ntopex.git

source ~/.venv/ntopex-py39/bin/activate
cd ntopex
pip3 install -r requirements.txt
```

Run as a Jupyter notebook:
```Shell
source ~/.venv/ntopex-jup39/bin/activate
cd ntopex
pip3 install -r requirements.txt -r requirements_jupyter.txt
jupyter notebook --ip=0.0.0.0
```