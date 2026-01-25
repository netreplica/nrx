# Installation

## Prerequisites

Python 3.10 or higher is required. In the commands below we assume you have `python3.10` executable. If it is under a different name, change accordingly.

Choose one of the following installation methods:

### Option 1: uv (fast)

[uv](https://docs.astral.sh/uv/) is a fast Python package installer and runner. It allows running Python tools without installation, or installing them without creating and managing virtual environments manually.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Option 2: pip (traditional)

```bash
curl -sL https://bootstrap.pypa.io/get-pip.py | python3.10 -
pip install virtualenv
```

## Installing nrx

### Option 1: Using uv

```bash
# Install nrx as a persistent tool
uv tool install nrx
nrx --version

# Or run nrx directly without installation
uv tool run nrx --version
```

### Option 2: Using pip

```bash
mkdir -p ~/.venv
python3.10 -m venv ~/.venv/nrx
source ~/.venv/nrx/bin/activate
pip install nrx
nrx --version
```

### Development Installation

After running the following commands, you will have a working `nrx` command in the current directory.

```bash
git clone https://github.com/netreplica/nrx.git --recursive
cd nrx
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nrx --version
```

## Initialize Configuration Directory

If this is the first time you're running `nrx`, you need to initialize its configuration directory. This will create the `$HOME/.nr` folder and populate it with a configuration file example and a compatible version of the templates.

```bash
nrx --init
```

The configuration directory is optional for basic usage, but the templates must be present for nrx to function properly. The examples in this documentation assume the configuration directory has been initialized.

## Verifying Installation

To verify that nrx is installed correctly, run:

```bash
nrx --version
```

You should see the version number of nrx displayed.

## Next Steps

* [Configuration](configuration.md) - Learn how to configure nrx
* [Templates](../customization/templates.md) - Understanding templates
* [Examples](../examples/containerlab.md) - Try some examples
