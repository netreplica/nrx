# Netreplica `ntopex`
Network Topology Exporter

<p align=center><img src="https://raw.githubusercontent.com/netreplica/ntopex/readme/images/ntopex_concept_diagram.png"  width="500px"/></p>

> NANOG-87 Hackathon project. Intro [slides](https://docs.google.com/presentation/d/?1-WcKsDuaFh3tozmTdTxGYXjMFuthRyevsRZbIc2j2Kw/edit?usp=sharing)

`ntopex` helps you export network topology graphs from [NetBox](https://docs.netbox.dev/en/stable/) DCIM system and create topology files for [Containerlab](https://containerlab.dev) network emulation tool.

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