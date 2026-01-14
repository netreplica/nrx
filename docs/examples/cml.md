# Cisco Modeling Labs Example

This guide shows how to export a topology from NetBox in Cisco Modeling Labs (CML) format and import it.

## Prerequisites

* Cisco Modeling Labs v2.5 or later
* NetBox API access with a valid token
* nrx installed and configured

## Step 1: Export from NetBox

Run `nrx --output cml` to export a topology graph from NetBox in CML format.

### Example: Using NetBox Demo

Here's an example exporting the "DM-Akron" site from [NetBox Demo](https://demo.netbox.dev):

```bash
export NB_API_TOKEN='replace_with_valid_API_token'
nrx --api https://demo.netbox.dev \
    --templates templates \
    --output cml \
    --dir demo \
    --site DM-Akron
```

This will create:

* `demo/DM-Akron.cml.yaml` - CML topology file
* `demo/DM-Akron.cyjs` - Cytoscape JSON graph data
* Configuration files for each device (if available)

### Command Options Explained

* `--api` - NetBox API URL
* `--templates` - Path to template directory
* `--output cml` - Export in CML format
* `--dir demo` - Save output to `demo` directory
* `--site DM-Akron` - Export devices from DM-Akron site

## Step 2: Import into CML

### Via Web Interface

1. Open your CML Dashboard in a browser
2. Choose **IMPORT**
3. Select `DM-Akron.cml.yaml` as the file to import
4. Verify the import status shows "Imported"
5. Choose **GO TO LAB**

### Via API (Optional)

You can also import programmatically using the CML API:

```bash
# Example using curl
curl -X POST https://your-cml-server/api/v0/import \
  -H "Authorization: Bearer $CML_TOKEN" \
  -F "file=@demo/DM-Akron.cml.yaml"
```

## Step 3: Start the Lab

1. In the CML interface, navigate to **SIMULATE** menu
2. Choose **START LAB**
3. Use the **NODES** menu to monitor the status of each node
4. Wait for all nodes to reach "ACTIVE" state

## Step 4: Access Devices

Once the lab is running, you can access devices via:

* **Console** - Click on a node and select "Console"
* **SSH** - If external connectivity is configured
* **Telnet** - Via the CML console server

## Alternative: Export via CYJS

You can also export in two steps using CYJS as an intermediate format.

### Step 1: Export to CYJS

Without `--output cml` argument, `nrx` will save data from NetBox as a CYJS file:

```bash
export NB_API_TOKEN='replace_with_valid_API_token'
nrx --api https://demo.netbox.dev \
    --site DM-Akron \
    --dir demo
```

This creates `demo/DM-Akron.cyjs`.

### Step 2: Convert CYJS to CML

Convert the CYJS file to CML format:

```bash
nrx --input cyjs \
    --file demo/DM-Akron.cyjs \
    --templates templates \
    --output cml \
    --dir demo
```

## Stopping the Lab

To stop the lab:

1. In the CML interface, go to **SIMULATE** menu
2. Choose **STOP LAB**
3. Wait for all nodes to reach "STOPPED" state

## Advanced Usage

### Export Multiple Sites

```bash
nrx --api https://demo.netbox.dev \
    --sites "site1,site2,site3" \
    --output cml \
    --dir multi-site
```

### Filter by Tags

Export devices with specific tags:

```bash
nrx --api https://demo.netbox.dev \
    --tags "production,core" \
    --output cml \
    --name prod-core
```

### Without Device Configurations

If you don't want to export device configurations:

```bash
nrx --api https://demo.netbox.dev \
    --site DM-Akron \
    --output cml \
    --noconfigs
```

## Configuration Files

When device configurations are available in NetBox, nrx will export them as startup configurations. In CML:

* Configurations are applied when the node boots
* They appear in the node's configuration editor
* You can modify them before starting the lab

## Troubleshooting

### Node Definition Issues

If you see errors about unsupported node types:

1. Check your [platform_map.yaml](../platform_map.md)
2. Ensure the platform slug in NetBox maps to a CML node definition
3. Verify the node definition exists in your CML installation

### Image Availability

Make sure the required VM images are available in your CML server:

1. Go to **TOOLS** → **Node Definitions**
2. Check that images for your node types are present
3. Upload missing images if needed

### Debug Mode

Enable debug output for detailed troubleshooting:

```bash
nrx --debug \
    --api https://demo.netbox.dev \
    --site DM-Akron \
    --output cml
```

## Next Steps

* [Containerlab Example](containerlab.md) - Export for Containerlab
* [NVIDIA Air Example](air.md) - Export for Air
* [Platform Map](../platform_map.md) - Configure platform mappings
* [Graphite Visualization](graphite.md) - Visualize your topology
