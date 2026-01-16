# Infragraph Export Design Summary

## Overview

Export NetBox network topologies to [infragraph](https://infragraph.dev/) format, enabling AI/HPC infrastructure modeling with automatic device grouping and intelligent name optimization.

## Background

### What is Infragraph?

[Infragraph](https://infragraph.dev/) is a model-driven, vendor-neutral API for representing AI/HPC infrastructure using graph theory. It uses:

- **Devices**: Templates defining hardware types with components
- **Components**: Device parts (CPU, XPU, NIC, Port, Switch, Memory)
- **Instances**: Actual deployed copies of devices
- **Links**: Connection characteristics (bandwidth, latency)
- **Edges**: Connections between instance components

### Key Insights from infragraph_service.py

The `InfraGraphService` module reveals that:

1. **Node naming convention**: `{instance}.{device_idx}.{component}.{component_idx}`
2. **Service generates graph**: `InfraGraphService.set_graph()` converts Infrastructure → NetworkX
3. **Built-in validation**: We can validate our output by loading it back
4. **Component indexing is critical**: Must map interface names to component indices precisely
5. **Indices must be 0-based and sequential**: Component indices start at 0 and increment

## Two-Phase Implementation

### Phase A: Enhance NetworkX Graph
Preserve complete NetBox data in the existing NetworkX graph structure:

- Add interface metadata (speed, type, description, tags)
- Add cable attributes (type, status, length)
- Use **device names** (not IDs) for portable references
- Cache device type information

**Benefit:** Single code path benefits all exporters.

### Phase B: Infragraph Export
Transform enhanced graph to infragraph format using the [infragraph Python SDK](https://pypi.org/project/infragraph/).

**Critical Difference:** Unlike other exporters (clab, cml, cyjs) which use actual device interfaces, infragraph export uses **NetBox Device Type templates** to ensure consistent component indices across all devices of the same type. This means:

- Device interface templates are fetched from NetBox Device Types API
- Per-device customizations (modules, subinterfaces) are ignored
- Edges with interfaces not in device type templates are skipped with warnings
- Users must ensure NetBox device types are accurate and complete

## Key Design Decisions

### 1. Automatic Instance Grouping

**Approach:** Group devices by `(site, role, vendor, model)`, then compact names

```python
# NetBox devices:
dc1-leaf01 (site=dc1, role=leaf, type=arista/dcs-7050sx-64)
dc1-leaf02 (site=dc1, role=leaf, type=arista/dcs-7050sx-64)

# Becomes infragraph instance:
instance_name: "dc1_leaf_7050"  # Compacted
count: 2                        # Two devices in group
```

**No user configuration required** - compaction routine automatically removes unnecessary parts.

### 2. Smart Name Compaction

**Start maximal, then remove parts** to find shortest conflict-free names:

**Phase 1:** Start with maximal name (site_role_vendor_model_full)

**Phase 2:** Remove parts only if uniqueness is preserved

**Removal and compaction order:**

1. Drop site (if still unique)
2. Drop vendor (if still unique)
3. Compact model (full → extended → core) only if still unique
4. Stop at the shortest unique form

**Example scenarios:**

| Scenario | NetBox Devices | Initial Names | Conflict? | Final Names |
|----------|----------------|---------------|-----------|-------------|
| Single-site | dc1/leaf01 (7050sx), dc1/leaf02 (7050sx) | dc1_leaf_arista_7050sx64 | No | `leaf_7050` (site+vendor removed, model compacted) |
| Multi-site same type | dc1/leaf01 (7050sx), dc2/leaf01 (7050sx) | dc1_leaf_arista_7050sx64, dc2_leaf_arista_7050sx64 | Yes | `dc1_leaf_7050`, `dc2_leaf_7050` (site kept) |
| Same role, different models | leaf01 (7050sx), leaf02 (7050tx) | leaf_arista_7050sx64, leaf_arista_7050tx48 | Yes | `leaf_7050sx`, `leaf_7050tx` (extended model) |
| Multi-site different vendors | dc1/arista-leaf, dc2/cisco-leaf | dc1_leaf_arista_7050sx64, dc2_leaf_cisco_9300 | No | `leaf_7050`, `leaf_9300` (site+vendor removed) |

**See [INFRAGRAPH_INSTANCE_INDEXING.md](INFRAGRAPH_INSTANCE_INDEXING.md) Q4 (lines 1091-1235) for complete algorithm details.**

### 3. Stable Instance Indexing

**Request name-based ordering from NetBox API** within each group:

```python
# Request name-based ordering from NetBox API
devices = nb_session.dcim.devices.filter(..., ordering='name')

# Group: dc1_leaf_7050
# Devices are kept in NetBox API order (name-sorted by NetBox)
device_name: leaf01 → instance_index: 0
device_name: leaf02 → instance_index: 1
device_name: leaf03 → instance_index: 2
```

**Benefits:**

- Users have direct control via NetBox device naming
- Ordering depends on NetBox's implementation (typically case-sensitive alphabetical)
- Mirrors what users see in NetBox when sorted by name
- Portable across NetBox instances when names are preserved

**Implementation Note:**

- nrx explicitly requests `ordering='name'` from NetBox API
- The final ordering depends on how NetBox implements name sorting
- No local re-sorting in Python ensures consistency with NetBox

### 4. NetBox Metadata Preservation

Use infragraph's `annotate_graph` API to preserve NetBox metadata:

```python
# Annotations on Instance nodes (device instances):
leaf_7050.0:
  device_name: "leaf01"
  site: "dc1"
  role: "leaf"
  platform: "arista-eos"
  source_id: "42"

# Annotations on Device component nodes:
arista_dcs_7050sx_64.port.0:
  interface_name: "Ethernet1"
arista_dcs_7050sx_64.port.1:
  interface_name: "Ethernet2"
# ... defined once at Device level

# Instance components (leaf_7050.0.port.0) are NOT annotated
# They reference the Device
```

**Two-file output:**

- `topology.infragraph.json` - Clean infrastructure model (no metadata)
- `topology.infragraph.annotated.json` - With NetBox device and instance annotations

**Annotation strategy:**
- **Instance nodes**: Annotated with device-specific metadata (device_name, site, role, platform)
- **Device components**: Annotated with interface names (once per device type)
- **Instance components**: NOT annotated (reference Device for interface names)
- Interface names come from NetBox Device Type definition (not individual devices)
- No per-device configuration data (MTU, descriptions, etc.) which can vary between devices

**Queryable metadata:** Use infragraph's `query_graph` API to:
- Find device instance by name: `device_name = "leaf01"` → `leaf_7050.0`
- Find Device components: `interface_name = "Ethernet1"` → `arista_dcs_7050sx_64.port.0`
- Reverse lookup: `arista_dcs_7050sx_64.port.5` → `interface_name = "Ethernet6"`

### 5. Portable Identifiers (Use Names, Not IDs)

**Problem:** NetBox database IDs change between instances. Same topology in different NetBox instances will have different device/interface IDs, making exports non-portable.

**Solution:** Use names and sorted indices for all identifiers:

- ✅ Device names (portable across NetBox instances)
- ✅ Compacted instance names (portable)
- ✅ Alphabetically sorted interface names → component indices (portable)
- ❌ NetBox device IDs (database-specific, not used)
- ❌ NetBox interface IDs (database-specific, not used)

**Result:** Same NetBox topology data produces identical infragraph exports regardless of which NetBox instance it comes from, as long as device names are preserved.

## Mapping Summary

| NetBox Concept | Infragraph Concept | Mapping |
|----------------|-------------------|---------|
| Device Type | Device (template) | Group by (vendor, model) |
| Device Type Interfaces | Component (Port) count | Fetched from Device Types API, sorted alphabetically |
| Devices (grouped) | Instance with count | Automatic grouping + compaction |
| Individual Device | Instance index | Preserve NetBox API order |
| Device Interface (actual) | Component index | Only if exists in Device Type template |
| Cable | Edge (ONE2ONE) | Point-to-point connection (if both interfaces in templates) |
| Interface speed | Link bandwidth | Kbps → Gbps conversion |

**Important:** Infragraph uses Device Type interface definitions, not actual device interfaces. Cables connecting interfaces not defined in device types are skipped.

## Node Naming Convention

```
{instance_name}.{instance_index}.{component}.{component_index}

Examples:
leaf_7050.0.port.0   # leaf01's Ethernet1
leaf_7050.0.port.1   # leaf01's Ethernet2
leaf_7050.1.port.0   # leaf02's Ethernet1
dc1_spine_7280.0.port.10  # Multi-site export
```

## Example Transformations

### Single-Site Export

**NetBox:**
```
Site: dc1
  leaf01 (arista/dcs-7050sx-64)
  leaf02 (arista/dcs-7050sx-64)
  spine01 (arista/dcs-7280sr-48c6)
```

**Infragraph:**
```
Instances:
  leaf_7050: count=2    # Site removed (unique)
  spine_7280: count=1   # Site removed (unique)

Nodes:
  leaf_7050.0   → leaf01
  leaf_7050.1   → leaf02
  spine_7280.0  → spine01
```

### Multi-Site Export (Same Devices)

**NetBox:**
```
Site: dc1
  leaf01, leaf02 (arista/dcs-7050sx-64)

Site: dc2
  leaf01, leaf02 (arista/dcs-7050sx-64)
```

**Infragraph:**
```
Instances:
  dc1_leaf_7050: count=2   # Site kept (needed)
  dc2_leaf_7050: count=2   # Site kept (needed)

Nodes:
  dc1_leaf_7050.0 → dc1-leaf01
  dc1_leaf_7050.1 → dc1-leaf02
  dc2_leaf_7050.0 → dc2-leaf01
  dc2_leaf_7050.1 → dc2-leaf02
```

### Multi-Site Export (Different Devices)

**NetBox:**
```
Site: dc1
  leaf01 (arista/dcs-7050sx-64)

Site: dc2
  leaf01 (cisco/nexus-9300)
```

**Infragraph:**
```
Instances:
  leaf_7050: count=1   # Site removed (arista unique)
  leaf_9300: count=1   # Site removed (cisco unique)

Nodes:
  leaf_7050.0 → dc1-leaf01 (arista)
  leaf_9300.0 → dc2-leaf01 (cisco)
```

## Benefits

- ✅ **Fully automatic** - No user configuration for grouping
- ✅ **Optimal readability** - Shortest possible conflict-free names
- ✅ **Portable** - Consistent output across NetBox instances
- ✅ **Stable** - Device renames don't break indices
- ✅ **Queryable** - Reverse lookup via annotations
- ✅ **Standard** - Uses infragraph best practices

## Usage

```bash
# Export to infragraph format
nrx --source netbox --output infragraph

# Output files:
# - topology.infragraph.json (clean infrastructure)
# - topology.infragraph.annotated.json (with NetBox metadata)
```

## Troubleshooting

### Warning: Skipped edges due to interfaces not in device type templates

**Cause:** The export found cables connecting interfaces that are not defined in the NetBox Device Type.

**Example:**
```
⚠ Warning: Skipped 3 edges due to interfaces not in device type templates:
  - leaf01:Ethernet49 (not in device type)
  - spine01:Management0 (not in device type)
  - leaf02:Ethernet1.100 (not in device type)
```

**Solution:**

1. Review the NetBox Device Type definition for the affected devices
2. Add missing interfaces to the Device Type template in NetBox
3. Re-run the export

**Why this happens:**

- Device has a custom module or add-on interface not in the device type
- Device has subinterfaces (e.g., `Ethernet1.100`) not defined in device type
- Device has management interfaces not included in device type template

**Expected behavior:** Infragraph requires consistent device templates. Per-device customizations are intentionally ignored to ensure all devices of the same type have identical component structures.

### Interface Ordering and Component Indices

**How component indices are assigned:**

Component indices for interfaces are assigned based on the **order of interfaces in the NetBox Device Type definition**, not by alphabetical or natural sorting.

**Example:**
```
NetBox Device Type: Arista DCS-7050SX-64
Interface order in NetBox:
  1. Management1        → component index 0
  2. Ethernet1          → component index 1
  3. Ethernet2          → component index 2
  ...
  50. Ethernet49        → component index 49
```

**Important notes:**

- nrx preserves the exact interface order from NetBox device types
- No local sorting is performed (alphabetical, natural, or otherwise)
- Component indices will shift if you reorder interfaces in the NetBox device type
- Users should ensure device type interfaces are ordered correctly in NetBox before export

**Why this approach:**

- NetBox is the canonical source of truth for device type definitions
- Users have full control over interface ordering in NetBox UI
- Avoids issues with complex interface naming schemes (e.g., `Ethernet1/10` vs `Ethernet1/2`)
- Consistent behavior across different NetBox versions

## References

- **Detailed Design:** [INFRAGRAPH_INSTANCE_INDEXING.md](INFRAGRAPH_INSTANCE_INDEXING.md)
- **Implementation Plan:** [INFRAGRAPH_IMPLEMENTATION_PLAN.md](INFRAGRAPH_IMPLEMENTATION_PLAN.md)
- **Infragraph Docs:** [https://infragraph.dev/](https://infragraph.dev/)
- **Infragraph SDK:** [https://pypi.org/project/infragraph/](https://pypi.org/project/infragraph/)
