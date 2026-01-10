# Infragraph Export Design Summary

## Overview

Export NetBox network topologies to [infragraph](https://infragraph.dev/) format, enabling AI/HPC infrastructure modeling with automatic device grouping and intelligent name optimization.

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

Progressive compaction finds shortest conflict-free names:

| Scenario | NetBox | Infragraph Instance |
|----------|--------|---------------------|
| Single-site | dc1/leaf01, dc1/leaf02 | `leaf_7050` (site removed) |
| Multi-site same devices | dc1/leaf01, dc2/leaf01 | `dc1_leaf_7050`, `dc2_leaf_7050` (site kept) |
| Multi-site different devices | dc1/arista-leaf, dc2/cisco-leaf | `leaf_7050`, `leaf_9300` (site+vendor removed) |

### 3. Stable Instance Indexing

**Sort by NetBox device ID** within each group:

```python
# Group: dc1_leaf_7050
devices.sort(key=lambda d: d['id'])

device_id: 42  → leaf01 → instance_index: 0
device_id: 43  → leaf02 → instance_index: 1
device_id: 47  → leaf03 → instance_index: 2
```

**Benefits:**
- Stable across device renames
- Preserves chronological order
- High portability probability between NetBox instances

### 4. NetBox Metadata Preservation

Use infragraph's `annotate_graph` API to preserve NetBox metadata:

```python
# Annotations on instance nodes:
leaf_7050.0:
  netbox_device_name: "leaf01"
  netbox_site: "dc1"
  netbox_role: "leaf"
  netbox_platform: "arista-eos"
```

**Two-file output:**
- `topology.infragraph.json` - Clean infrastructure model
- `topology.infragraph.annotated.json` - With NetBox metadata

### 5. Portable Identifiers

**Never use NetBox database IDs in exported data:**
- ✅ Device names (portable)
- ✅ Compacted instance names (portable)
- ✅ Alphabetically sorted interface indices (portable)
- ❌ NetBox device IDs (only for internal sorting)
- ❌ NetBox interface IDs (database-specific)

## Mapping Summary

| NetBox Concept | Infragraph Concept | Mapping |
|----------------|-------------------|---------|
| Device Type | Device (template) | Group by (vendor, model) |
| Devices (grouped) | Instance with count | Automatic grouping + compaction |
| Individual Device | Instance index | Sort by device ID |
| Interface | Component (Port) | Alphabetical by interface name |
| Cable | Edge (ONE2ONE) | Point-to-point connection |
| Interface speed | Link bandwidth | Kbps → Gbps conversion |

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

## References

- **Detailed Design:** [INFRAGRAPH_INSTANCE_INDEXING.md](INFRAGRAPH_INSTANCE_INDEXING.md)
- **Implementation Plan:** [INFRAGRAPH_IMPLEMENTATION_PLAN.md](INFRAGRAPH_IMPLEMENTATION_PLAN.md)
- **Infragraph Docs:** https://infragraph.dev/
- **Infragraph SDK:** https://pypi.org/project/infragraph/
