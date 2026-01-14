# Containerlab Example

This guide shows how to export a topology from NetBox in Containerlab format and deploy it.

## Prerequisites

* [Containerlab](https://containerlab.dev) v0.39 or later installed
* NetBox API access with a valid token
* nrx installed and configured

## Step 1: Export from NetBox

Run `nrx --output clab` to export a topology graph from NetBox in Containerlab format.

### Example: Using NetBox Demo

Here's an example exporting the "DM-Albany" site from [NetBox Demo](https://demo.netbox.dev):

```bash
export NB_API_TOKEN='replace_with_valid_API_token'
nrx --api https://demo.netbox.dev \
    --templates templates \
    --output clab \
    --dir demo \
    --site DM-Albany
```

This will create:

* `demo/DM-Albany.clab.yaml` - Containerlab topology file
* `demo/DM-Albany.cyjs` - Cytoscape JSON graph data
* Configuration files for each device (if available)

### Command Options Explained

* `--api` - NetBox API URL
* `--templates` - Path to template directory
* `--output clab` - Export in Containerlab format
* `--dir demo` - Save output to `demo` directory
* `--site DM-Albany` - Export devices from DM-Albany site

## Step 2: Deploy the Topology

Deploy the topology using Containerlab:

```bash
sudo -E containerlab deploy -t demo/DM-Albany.clab.yaml --reconfigure
```

### Command Options

* `-E` - Preserve environment variables (for tokens, etc.)
* `-t` - Topology file to deploy
* `--reconfigure` - Reconfigure existing lab if it exists

## Step 3: Verify Deployment

Check the status of your lab:

```bash
sudo containerlab inspect --name DM-Albany
```

## Step 4: Access Devices

Connect to a device:

```bash
sudo containerlab connect --name DM-Albany --node <device-name>
```

## Alternative: Export via CYJS

You can also export in two steps using CYJS as an intermediate format.

### Step 1: Export to CYJS

Without `--output clab` argument, `nrx` will save data from NetBox as a CYJS file:

```bash
export NB_API_TOKEN='replace_with_valid_API_token'
nrx --api https://demo.netbox.dev \
    --site DM-Albany \
    --dir demo
```

This creates `demo/DM-Albany.cyjs`.

### Step 2: Convert CYJS to Containerlab

Convert the CYJS file to Containerlab format:

```bash
nrx --input cyjs \
    --file demo/DM-Albany.cyjs \
    --templates templates \
    --output clab \
    --dir demo
```

This two-step approach is useful when you want to:

* Save the NetBox state for later use
* Convert the same topology to multiple formats
* Work offline without NetBox access

## Cleanup

To destroy the lab:

```bash
sudo containerlab destroy --name DM-Albany
```

## Advanced Usage

### Export Multiple Sites

```bash
nrx --api https://demo.netbox.dev \
    --sites "site1,site2,site3" \
    --output clab \
    --dir multi-site
```

### Filter by Tags

Export devices with specific tags:

```bash
nrx --api https://demo.netbox.dev \
    --tags "production,core" \
    --output clab \
    --name prod-core
```

### Custom Template Path

Use custom templates:

```bash
nrx --api https://demo.netbox.dev \
    --site DM-Albany \
    --templates /path/to/custom/templates \
    --output clab
```

## Troubleshooting

### Missing Device Images

If you see errors about missing container images, update your [platform_map.yaml](../platform_map.md) to specify the correct container images for your platforms.

### Configuration Issues

Enable debug output to see detailed information:

```bash
nrx --debug --api https://demo.netbox.dev --site DM-Albany --output clab
```

## Next Steps

* [Cisco Modeling Labs Example](cml.md) - Export for CML
* [NVIDIA Air Example](air.md) - Export for Air
* [Platform Map](../platform_map.md) - Configure platform mappings
