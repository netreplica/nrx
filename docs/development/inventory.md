# Inventory Export Proposal: Export Devices Only (Without Links)

## Overview

Add capability to export device inventory without any network connections/links between devices. This would be useful for:
- Creating device inventory lists
- Exporting to systems that only need device information
- Generating documentation that focuses on devices rather than topology
- Creating simplified visualizations showing devices without connections

## Proposed Implementation

### Option 1: CLI Argument (Recommended)

Add a new CLI argument that mirrors the existing `--noconfigs` pattern:

```bash
--nolinks           disable network links export (enabled by default)
```

**Advantages:**
- Consistent with existing `--noconfigs` flag pattern
- Clear and explicit
- Easy to use for one-off exports
- Self-documenting in `--help` output

**Example usage:**
```bash
# Export devices only from a site
nrx --output cyjs --site DC1 --nolinks

# Export devices only with custom config
nrx -c myconfig.conf --nolinks
```

### Option 2: Configuration File Parameter

Add a new configuration parameter similar to `EXPORT_CONFIGS`:

```toml
# Export network links between devices
EXPORT_LINKS = true
```

**Advantages:**
- Persistent setting for projects that always need devices-only
- Can be combined with other config options
- Consistent with `EXPORT_CONFIGS` pattern

**Example config:**
```toml
EXPORT_SITES = ['DC1']
EXPORT_DEVICE_ROLES = ['server', 'router']
EXPORT_LINKS = false  # Only export devices, no connections
EXPORT_CONFIGS = true
```

### Option 3: Combined Approach (Best)

Support **both** CLI argument and configuration file, with CLI taking precedence:

1. Configuration file: `EXPORT_LINKS = true` (default)
2. CLI argument: `--nolinks` to disable
3. Precedence: CLI > Config file > Default (true)

This follows the same pattern as `EXPORT_CONFIGS` / `--noconfigs`.

## Implementation Details

### Code Changes Required

1. **Argument Parser** ([nrx.py:1085](src/nrx/nrx.py#L1085))
   ```python
   args_parser.add_argument('--nolinks', required=False,
                           help='disable network links export (enabled by default)',
                           action=argparse.BooleanOptionalAction)
   ```

2. **Configuration File** (nrx.conf)
   ```toml
   # Export network links between devices
   ;EXPORT_LINKS = true
   ```

3. **Config Loading**
   - Add `EXPORT_LINKS` to default config with value `True`
   - Handle `--nolinks` argument same as `--noconfigs`

4. **NBFactory Class** ([nrx.py:239-243](src/nrx/nrx.py#L239-L243))
   - Skip `_get_nb_objects("interfaces", ...)` when `EXPORT_LINKS = false`
   - Skip `_get_nb_objects("cables", ...)` when `EXPORT_LINKS = false`
   - Still call `_add_disconnected_devices_to_graph()` since all devices are now "disconnected"

5. **Graph Building**
   - When `EXPORT_LINKS = false`, skip interface and cable fetching
   - Only fetch devices and add them directly to the graph
   - All devices will be treated as disconnected nodes

### Behavior

When `EXPORT_LINKS = false` or `--nolinks` is specified:

✅ **Exported:**
- All devices matching site/tag/role filters
- Device metadata (name, role, platform, IP addresses, custom fields, etc.)
- Device configurations (if `EXPORT_CONFIGS = true`)

❌ **Not Exported:**
- Interfaces
- Cables/connections between devices
- Cable paths through patch panels/circuits
- Network topology edges

### Output Format Impact

The output will contain:
- **CYJS**: Nodes only, no edges array entries
- **Containerlab**: Devices only, no links section
- **CML**: Devices only, no connections
- **Graphite/D2**: Devices only, no lines between them
- **NVIDIA Air**: Devices only, no links

## Use Cases

1. **Device Inventory Export**
   ```bash
   nrx --site DC1 --output cyjs --nolinks
   ```
   Export all devices in DC1 as a list without topology

2. **Documentation Generation**
   ```bash
   nrx --tags production --output graphite --nolinks
   ```
   Create device-only visualization for documentation

3. **CMDB Integration**
   ```bash
   nrx --sites DC1,DC2,DC3 --nolinks --output custom-json
   ```
   Export device inventory to custom format for CMDB

4. **Simplified Lab Setup**
   ```bash
   nrx --site LAB --output clab --nolinks --noconfigs
   ```
   Create containerlab topology with devices but no interconnections
   (useful for initially deploying lab devices)

## Testing

1. Add unit test to verify `EXPORT_LINKS` config parameter handling
2. Add system test with `--nolinks` to verify:
   - Devices are exported
   - No links/edges in output
   - All output formats work correctly
3. Test with existing `tests/colo` setup by adding `--nolinks` variant

## Documentation Updates

1. **README.md**: Add to "Latest capabilities" section
2. **docs/userguide/configuration.md**: Document `EXPORT_LINKS` parameter
3. **CLI help**: Automatically updated via argparse
4. **Examples**: Add example usage to appropriate docs

## Comparison with Similar Features

| Feature | CLI Flag | Config Param | Default |
|---------|----------|--------------|---------|
| Device configs | `--noconfigs` | `EXPORT_CONFIGS` | `true` |
| Network links | `--nolinks` | `EXPORT_LINKS` | `true` |

## Questions for Discussion

1. ✅ Should this be `--nolinks` (disable) or `--links-only` (enable)?
   - **Recommendation**: `--nolinks` to match `--noconfigs` pattern

2. ✅ Should we skip interface fetching entirely or still fetch but not create edges?
   - **Recommendation**: Skip entirely for performance (no need to query interfaces/cables)

3. ✅ Config parameter name: `EXPORT_LINKS` or `EXPORT_CONNECTIONS`?
   - **Recommendation**: `EXPORT_LINKS` (shorter, matches other parameters)

4. Should there be any validation/warnings when using certain output formats with `--nolinks`?
   - Example: Warn if using `--output clab` with `--nolinks` since a lab without links may be unusual
   - **Recommendation**: No warnings, trust user intent

## Alternative Names Considered

- `--no-topology` - Too vague
- `--devices-only` - Verbose but clear
- `--no-connections` - Alternative to `--nolinks`
- `--skip-links` - Alternative verb
- `--nolinks` - **Selected** (matches `--noconfigs` pattern)

## Recommendation

Implement **Option 3 (Combined Approach)** with:
- CLI argument: `--nolinks`
- Config parameter: `EXPORT_LINKS = true`
- Default behavior: Export links (backwards compatible)
- Precedence: CLI > Config > Default

This provides maximum flexibility while maintaining consistency with existing patterns in the codebase.
