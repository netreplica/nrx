# NVIDIA Air Example

This guide shows how to export a topology from NetBox in NVIDIA Air format.

## Prerequisites

* NVIDIA Air account with API access
* NetBox API access with a valid token
* nrx installed and configured

## About NVIDIA Air

[NVIDIA Air](https://www.nvidia.com/en-us/networking/ethernet-switching/air/) is a cloud-hosted data center simulation platform that provides a digital twin of your network infrastructure.

nrx supports NVIDIA Air API v2 (starting with Air v9.15.8).

## Step 1: Export from NetBox

Run `nrx --output air` to export a topology graph from NetBox in NVIDIA Air format.

### Example: Using NetBox Demo

```bash
export NB_API_TOKEN='replace_with_valid_API_token'
nrx --api https://demo.netbox.dev \
    --templates templates \
    --output air \
    --dir demo \
    --site DM-Akron
```

This will create:

* `demo/DM-Akron.air.json` - NVIDIA Air topology file
* `demo/DM-Akron.cyjs` - Cytoscape JSON graph data
* Configuration files for each device (if available)

### Command Options Explained

* `--api` - NetBox API URL
* `--templates` - Path to template directory
* `--output air` - Export in NVIDIA Air format
* `--dir demo` - Save output to `demo` directory
* `--site DM-Akron` - Export devices from DM-Akron site

## Step 2: Upload to NVIDIA Air

### Via Web Interface

1. Log in to your NVIDIA Air account
2. Navigate to **Simulations**
3. Click **Create Simulation**
4. Choose **Upload Topology**
5. Select `DM-Akron.air.json`
6. Configure simulation settings (duration, etc.)
7. Click **Create**

### Via API (Advanced)

You can upload topologies programmatically using the Air API:

```bash
# Example using curl
curl -X POST https://air.nvidia.com/api/v2/simulation \
  -H "Authorization: Bearer $AIR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @demo/DM-Akron.air.json
```

## Step 3: Start the Simulation

1. In the NVIDIA Air interface, locate your simulation
2. Click **Start Simulation**
3. Wait for the simulation to become active
4. Access devices via web console or SSH

## Output Format

The NVIDIA Air export creates a JSON file with:

* Node definitions (switches, routers, servers)
* Link definitions (connections between nodes)
* Configuration data (if exported from NetBox)
* Layout information for visualization

## Alternative: Export via CYJS

Export to CYJS first, then convert to Air format:

```bash
# Step 1: Export to CYJS
nrx --api https://demo.netbox.dev \
    --site DM-Akron \
    --dir demo

# Step 2: Convert to Air format
nrx --input cyjs \
    --file demo/DM-Akron.cyjs \
    --templates templates \
    --output air \
    --dir demo
```

## Advanced Usage

### Export Multiple Sites

```bash
nrx --api https://demo.netbox.dev \
    --sites "site1,site2,site3" \
    --output air \
    --dir multi-site
```

### Filter by Tags

Export devices with specific tags:

```bash
nrx --api https://demo.netbox.dev \
    --tags "production,spine-leaf" \
    --output air \
    --name production-fabric
```

### Custom Simulation Name

```bash
nrx --api https://demo.netbox.dev \
    --site DM-Akron \
    --name "Production-DC-Simulation" \
    --output air
```

## Supported Devices

NVIDIA Air supports simulation of:

* NVIDIA Cumulus Linux switches
* SONiC switches
* Generic Linux hosts and servers
* Ubuntu, CentOS, and other Linux distributions

Ensure your [platform_map.yaml](../platform_map.md) correctly maps NetBox platforms to Air-compatible node types.

## Device Configurations

When device configurations are available in NetBox:

* They are included in the Air topology file
* They're applied when the simulation starts
* ZTP (Zero Touch Provisioning) can be used for initial setup

## Troubleshooting

### Unsupported Node Types

If you see warnings about unsupported devices:

1. Check the [platform_map.yaml](../platform_map.md)
2. Verify the platform maps to an Air-compatible node type
3. Consider using a generic Linux host as a substitute

### API Version Compatibility

nrx uses Air API v2. If you're using an older Air version:

1. Check your Air version (must be v9.15.8 or later)
2. Update templates if using a custom template set
3. Contact NVIDIA support for API compatibility

### Debug Mode

Enable debug output for troubleshooting:

```bash
nrx --debug \
    --api https://demo.netbox.dev \
    --site DM-Akron \
    --output air
```

## Integration with NetBox

NVIDIA Air topologies can be:

* Generated from NetBox data center designs
* Used to validate configurations before deployment
* Integrated into CI/CD pipelines for testing

## Next Steps

* [Containerlab Example](containerlab.md) - Export for Containerlab
* [CML Example](cml.md) - Export for Cisco Modeling Labs
* [Platform Map](../platform_map.md) - Configure platform mappings
* [Templates](../templates.md) - Customize Air output format
