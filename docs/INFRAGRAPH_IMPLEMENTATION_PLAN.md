# Infragraph Export Implementation Plan

## Overview

This document outlines the plan to add infragraph export capability to nrx. The implementation follows a two-phase approach:

1. **Phase A**: Enhance NetworkX graph structure to preserve NetBox data without loss
2. **Phase B**: Implement infragraph export using the enhanced graph data

This approach ensures a single code path for data collection that benefits all export formats.

## Background

### What is Infragraph?

[Infragraph](https://infragraph.dev/) is a model-driven, vendor-neutral API for representing AI/HPC infrastructure using graph theory. It uses:

- **Devices**: Templates defining hardware types with components
- **Components**: Device parts (CPU, XPU, NIC, Port, Switch, Memory)
- **Instances**: Actual deployed copies of devices
- **Links**: Connection characteristics (bandwidth, latency)
- **Edges**: Connections between instance components

### NetBox to Infragraph Mapping

| NetBox Concept | Infragraph Concept | Mapping Strategy |
|----------------|-------------------|------------------|
| Device Type (manufacturer + model) | Device (template) | Group by (vendor, model) |
| Device (instance) | Instance | One-to-one |
| Interface | Component (Port/NIC) | Grouped by device type |
| Cable | Infrastructure.Edge | One-to-one with proper endpoints |
| Interface speed | Link.bandwidth | Extract from interface data |

### Key Insights from infragraph_service.py

The `InfraGraphService` module reveals that:

1. **Node naming convention**: `{instance}.{device_idx}.{component}.{component_idx}`
2. **Service generates graph**: `InfraGraphService.set_graph()` converts Infrastructure → NetworkX
3. **Built-in validation**: We can validate our output by loading it back
4. **Component indexing is critical**: Must map interface names to component indices precisely
5. **Indices must be 0-based and sequential**: Component indices start at 0 and increment

### Critical Design Decision: Use Names, Not IDs

**NetBox IDs are not suitable for portable exports:**

```python
# NetBox Instance A
Device ID: 42 → "leaf01" (Arista DCS-7050)
Interface ID: 156 → "Ethernet1" on device 42

# Same data imported into NetBox Instance B
Device ID: 108 → "leaf01" (same Arista DCS-7050)
Interface ID: 423 → "Ethernet1" on device 108

# Result: Same topology, different IDs!
```

**Infragraph requires consistent, portable identifiers:**

```python
# Both NetBox instances produce:
instance: "leaf01"           # Device name (portable)
component: "port"            # Component type
component_idx: 0             # 0-based index (Ethernet1 = first interface alphabetically)

# Infragraph node: leaf01.0.port.0
# Always the same, regardless of NetBox instance!
```

**Solution:**
- Use **device names** as instance identifiers
- Use **interface names** sorted alphabetically to generate **0-based sequential indices**
- Never use NetBox database IDs in exported data

## Current State Analysis

### Current NetworkX Graph Structure

**Device Nodes:**
```python
{
    "type": "device",
    "side": "a" | "b",
    "device": {
        "id": int,
        "name": str,
        "site": str,
        "platform": str,
        "vendor": str, "vendor_name": str,
        "model": str, "model_name": str,
        "role": str, "role_name": str,
        "primary_ip4": str,
        "primary_ip6": str,
        "config": str,
        "node_id": int,
        "device_index": int
    }
}
```

**Interface Nodes:**
```python
{
    "type": "interface",
    "side": "a" | "b",
    "interface": {
        "id": int,
        "type": "interface",
        "name": str,
        "node_id": int,
        "interface_index": int
    }
}
```

**Edges:**
- Device → Interface (ownership)
- Interface → Interface (cable connection, no attributes)

### Data Loss Identified

Comparing NetBox API objects to what nrx currently stores:

**Missing from Interface:**
- `label` - User-friendly label
- `description` - Interface description
- `interface_type` - Full type info (only partially checked)
- `speed` - **Critical for link bandwidth!**
- `mtu` - Maximum transmission unit
- `enabled` - Interface state
- `device_id` - Direct device reference (requires graph traversal currently)
- `device_name` - Device name (requires graph traversal)
- `tags` - Interface tags (checked but not stored)

**Missing from Cable (edge):**
- `cable_id` - Cable identifier
- `cable_type` - Cable type
- `cable_status` - Connection status
- `cable_length` - Physical length
- `cable_length_unit` - Length unit

**Missing from Device Type:**
- No cached inventory of device types
- No pre-built interface list per device type
- Must iterate all devices to find unique types

## Phase A: Enhance NetworkX Graph Structure

### Objectives

1. Store complete NetBox data in NetworkX graph
2. Maintain backward compatibility with existing exporters
3. Improve performance with cached device type information
4. Enable efficient infragraph export

### A1: Enhanced Interface Nodes

**Current:**
```python
i = {
    "id": interface.id,
    "type": "interface",
    "name": interface.name,
    "node_id": -1,
}
```

**Enhanced:**
```python
i = {
    "id": interface.id,  # Keep for internal nrx lookups only
    "type": "interface",
    "name": interface.name,
    "label": interface.label or "",
    "description": interface.description or "",
    "interface_type": interface.type.value if interface.type else "unknown",
    "speed": interface.speed or 0,  # Kbps - CRITICAL for infragraph!
    "mtu": interface.mtu or 0,
    "enabled": interface.enabled,
    "device_name": interface.device.name,  # Portable device reference!
    "tags": [tag.name for tag in interface.tags] if interface.tags else [],
    "node_id": -1,
    "interface_index": -1,
}
```

**Implementation location:** `NBFactory._get_nb_interfaces()` around line 319

**Important:** Store `device_name` NOT `device_id`. NetBox IDs are database primary keys that change between NetBox instances. Device names are portable identifiers.

**Benefits:**
- Direct device lookup by name (portable across NetBox instances)
- Speed data for infragraph link bandwidth calculation
- Tags for filtering/annotation
- Description for infragraph component descriptions

**Backward compatibility:** ✅ All existing fields preserved

### A2: Enhanced Cable Edge Attributes

**Current:**
```python
self.G.add_edges_from([
    (i_a["node_id"], i_b["node_id"]),
])
```

**Enhanced:**
```python
self.G.add_edge(
    i_a["node_id"],
    i_b["node_id"],
    cable_id=cable.id,
    cable_type=cable.type.value if cable.type else "unknown",
    cable_status=cable.status.value if cable.status else "unknown",
    cable_length=cable.length or 0,
    cable_length_unit=cable.length_unit or "",
)
```

**Implementation location:** `NBFactory._add_cable_to_graph()` around line 456

**Benefits:**
- Cable metadata available for all exporters
- Can filter by cable type/status
- Physical length data available

**Backward compatibility:** ✅ Edges still exist, just with added attributes

### A3: Device Type Caching

**Add to NBNetwork class:**
```python
class NBNetwork:
    def __init__(self):
        # ... existing fields ...
        self.device_types = {}  # (vendor, model) → device_type_info
        self.device_type_interfaces = {}  # (vendor, model) → [sorted interface list]
        self.device_name_to_type = {}  # device_name → (vendor, model)
```

**Build during device collection:**
```python
def _get_nb_devices(self):
    for device in devices:
        d = self._init_device(device)
        # ... existing code ...

        # Cache device type
        device_type_key = (d['vendor'], d['model'])

        # Map device name to type for quick lookup
        self.nb_net.device_name_to_type[d['name']] = device_type_key

        if device_type_key not in self.nb_net.device_types:
            self.nb_net.device_types[device_type_key] = {
                'vendor': d['vendor'],
                'vendor_name': d['vendor_name'],
                'model': d['model'],
                'model_name': d['model_name'],
                'platform': d['platform'],
                'platform_name': d['platform_name'],
                'sample_device_name': d['name'],  # Use name for interface template
            }
```

**Important:** Use device names, not IDs. NetBox IDs are instance-specific database keys that change when data is imported into different NetBox instances.

**Build interface inventory:**
```python
def _get_nb_interfaces(self, block_size=4):
    # ... existing code to fetch interfaces ...

    # After creating interface dict
    device_name = i['device_name']
    device_type_key = self.nb_net.device_name_to_type.get(device_name)

    if device_type_key:
        # Build interface list using first device of each type as template
        sample_name = self.nb_net.device_types[device_type_key]['sample_device_name']

        if device_name == sample_name:
            if device_type_key not in self.nb_net.device_type_interfaces:
                self.nb_net.device_type_interfaces[device_type_key] = []
            self.nb_net.device_type_interfaces[device_type_key].append(i)
```

**Helper method:**
```python
def _find_device_by_name(self, device_name):
    """Find device dict by device name"""
    for device in self.nb_net.devices:
        if device['name'] == device_name:
            return device
    return None
```

**Benefits:**
- Fast device type iteration for infragraph Device creation
- Pre-built interface lists per device type
- Device name-based lookups (portable across NetBox instances)
- Proper 0-based sequential indexing for infragraph components

**Backward compatibility:** ✅ Additive only, no changes to existing data

### A4: Testing Enhanced Graph

**Unit tests needed:**

1. Test interface data completeness
   - Verify all new fields populated
   - Verify device_id reference correct
   - Verify tags list correct

2. Test cable edge attributes
   - Verify cable metadata on edges
   - Verify backward compatibility (edges still exist)

3. Test device type caching
   - Verify unique device types identified
   - Verify interface lists built correctly
   - Verify device lookup works

4. Test existing exporters
   - Run clab export with enhanced graph
   - Run cml export with enhanced graph
   - Run cyjs export with enhanced graph
   - Verify outputs unchanged

**Implementation location:** `tests/unit/test_enhanced_graph.py` (new file)

## Phase B: Infragraph Export Implementation

### Objectives

1. Use infragraph Python SDK to create Infrastructure objects
2. Leverage enhanced graph data for accurate mapping
3. Validate output using InfraGraphService
4. Support standard nrx CLI patterns

### B1: Dependencies

**Add to requirements.txt:**
```
infragraph>=0.6.1
```

### B2: InterfaceMapper Class

Purpose: Map NetBox interface names to infragraph component indices (0-based, sequential)

```python
class InterfaceMapper:
    """Maps NetBox interfaces to infragraph component indices"""

    def __init__(self, nb_net):
        self.nb_net = nb_net
        # "device_name.interface_name" → (component_name, idx)
        # Using device_name (not ID) for portability across NetBox instances
        self.interface_to_component = {}

    def build_mappings(self):
        """Build interface→component mapping with 0-based sequential indices"""
        # For each device type, create consistent component index mapping
        for device_type_key, interfaces in self.nb_net.device_type_interfaces.items():
            # CRITICAL: Sort interfaces by name for consistent 0-based indexing
            # This ensures port.0, port.1, port.2... are always the same interfaces
            sorted_interfaces = sorted(interfaces, key=lambda x: x['name'])

            # Apply mapping to ALL devices of this type
            for device in self.nb_net.devices:
                if (device['vendor'], device['model']) == device_type_key:
                    # Map each interface: device_name.interface_name → (component, idx)
                    for idx, iface_template in enumerate(sorted_interfaces):
                        mapping_key = f"{device['name']}.{iface_template['name']}"
                        # idx is 0-based sequential, as required by infragraph
                        self.interface_to_component[mapping_key] = ("port", idx)

    def get_component_index(self, device_name, interface_name):
        """Get (component_name, component_idx) for an interface

        Args:
            device_name: NetBox device name (portable identifier)
            interface_name: NetBox interface name

        Returns:
            Tuple of (component_name, component_idx) where idx is 0-based
        """
        key = f"{device_name}.{interface_name}"
        return self.interface_to_component.get(key, ("port", 0))
```

**Key design decisions:**
- Use device **names** not IDs (portable across NetBox instances)
- Sort interfaces by name for consistent ordering
- Generate 0-based sequential indices (infragraph requirement)
- Same device type always has same component indices

### B3: InfragraphExporter Class

```python
from infragraph import Device, Infrastructure, Component, InfrastructureEdge

class InfragraphExporter:
    """Export NetBox topology to infragraph format"""

    def __init__(self, network_graph, nb_net, topology_name, config):
        self.G = network_graph
        self.nb_net = nb_net
        self.topology_name = topology_name
        self.config = config
        self.mapper = InterfaceMapper(nb_net)
        self.device_templates = {}  # (vendor, model) → Device object

    def build_infrastructure(self):
        """Main export method"""
        # Build interface mappings
        self.mapper.build_mappings()

        # Create Infrastructure
        infra = Infrastructure(
            name=self.topology_name,
            description=f"Network topology exported from NetBox"
        )

        # Build all components
        self._build_device_templates(infra)
        self._build_instances(infra)
        self._build_links(infra)
        self._build_edges(infra)

        return infra

    def _sanitize_name(self, name):
        """Sanitize names for infragraph (alphanumeric + underscore)"""
        name = str(name).lower()
        name = name.replace('-', '_').replace(' ', '_').replace('.', '_')
        return ''.join(c for c in name if c.isalnum() or c == '_')
```

### B4: Device Template Creation

```python
def _build_device_templates(self, infra):
    """Create Device objects from cached device types"""
    for device_type_key, device_type_info in self.nb_net.device_types.items():
        # Create Device using infragraph SDK
        device = Device()
        device.name = self._sanitize_name(
            f"{device_type_info['vendor']}_{device_type_info['model']}"
        )
        device.description = (
            f"{device_type_info['vendor_name']} {device_type_info['model_name']}"
        )

        # Add port components
        interfaces = self.nb_net.device_type_interfaces.get(device_type_key, [])
        if interfaces:
            port = device.components.add(
                name="port",
                description="Network interface port",
                count=len(interfaces)
            )
            port.choice = Component.PORT

        # Cache and add to infrastructure
        self.device_templates[device_type_key] = device
        infra.devices.append(device)
```

### B5: Instance Creation

```python
def _build_instances(self, infra):
    """Create Instance for each NetBox device using cached data"""
    for device in self.nb_net.devices:
        device_type_key = (device['vendor'], device['model'])
        device_template = self.device_templates[device_type_key]

        instance = infra.instances.add(
            name=self._sanitize_name(device['name']),
            description=f"{device['role_name']} - {device['site']}",
            device=device_template.name,
            count=1
        )
```

### B6: Link Creation

```python
def _build_links(self, infra):
    """Create link definitions with bandwidth from interface speeds"""
    # Analyze interface speeds to determine link types needed
    speeds_used = set()
    for iface in self.nb_net.interfaces:
        if iface.get('speed', 0) > 0:
            speeds_used.add(iface['speed'])

    # Create links for each speed
    # Convert Kbps to Gbps
    for speed_kbps in speeds_used:
        speed_gbps = speed_kbps / 1_000_000
        link_name = f"ethernet_{int(speed_gbps)}g"

        link = infra.links.add(
            name=link_name,
            description=f"{speed_gbps}G Ethernet connection"
        )
        link.physical.bandwidth.gigabits_per_second = speed_gbps

    # Add default link for interfaces without speed
    default_link = infra.links.add(
        name="ethernet",
        description="Ethernet connection (unknown speed)"
    )
    default_link.physical.bandwidth.gigabits_per_second = 10  # Default
```

### B7: Edge Creation

```python
def _build_edges(self, infra):
    """Convert cables to Infrastructure edges using device names"""
    for edge in self.G.edges(data=True):
        node_a_name, node_b_name, edge_data = edge

        # Get node data
        node_a = self.G.nodes[node_a_name]
        node_b = self.G.nodes[node_b_name]

        # Only interface-to-interface connections
        if node_a.get('type') != 'interface' or node_b.get('type') != 'interface':
            continue

        # Get interface data (now with device_name!)
        iface_a = node_a['interface']
        iface_b = node_b['interface']

        # Get device names directly from interface data
        device_name_a = iface_a['device_name']
        device_name_b = iface_b['device_name']

        # Map to component indices using device names
        component_a, idx_a = self.mapper.get_component_index(
            device_name_a, iface_a['name']
        )
        component_b, idx_b = self.mapper.get_component_index(
            device_name_b, iface_b['name']
        )

        # Determine link type from interface speed
        link_name = self._get_link_name(iface_a.get('speed', 0))

        # Create edge using ONE2ONE scheme (point-to-point cable)
        infra_edge = infra.edges.add(
            scheme=InfrastructureEdge.ONE2ONE,
            link=link_name
        )

        # Set endpoints: instance[device_idx].component[component_idx]
        # device_idx is always 0 since each NetBox device maps to instance with count=1
        instance_a = self._sanitize_name(device_name_a)
        instance_b = self._sanitize_name(device_name_b)

        infra_edge.ep1.instance = f"{instance_a}[0]"
        infra_edge.ep1.component = f"{component_a}[{idx_a}]"
        infra_edge.ep2.instance = f"{instance_b}[0]"
        infra_edge.ep2.component = f"{component_b}[{idx_b}]"

def _get_link_name(self, speed_kbps):
    """Determine link name from interface speed"""
    if speed_kbps > 0:
        speed_gbps = speed_kbps / 1_000_000
        return f"ethernet_{int(speed_gbps)}g"
    return "ethernet"
```

**Key improvements:**
- Use `device_name` from interface data (portable identifier)
- No need for device lookup by ID
- Clearer endpoint notation with comments
- Component indices are 0-based sequential from InterfaceMapper

### B8: Export Method in NBFactory

```python
def export_graph_infragraph(self):
    """Export network topology in infragraph format"""
    print(f"Exporting topology to infragraph format...")

    # Create exporter
    exporter = InfragraphExporter(
        self.G,
        self.nb_net,
        self.topology_name,
        self.config
    )

    # Build infrastructure
    infrastructure = exporter.build_infrastructure()

    # Serialize to JSON
    json_output = infrastructure.serialize(encoding=Infrastructure.JSON)

    # Optional: Validate using InfraGraphService
    if self.config.get('validate_infragraph', False):
        try:
            from infragraph import InfraGraphService
            service = InfraGraphService()
            service.set_graph(json_output)
            print("✓ Infragraph validation passed")
        except Exception as e:
            print(f"⚠ Infragraph validation warning: {e}")

    # Write to file
    dir_path = create_output_directory(self.topology_name, self.config['output_dir'])
    export_file = f"{self.topology_name}.infragraph.json"
    export_path = f"{dir_path}/{export_file}"

    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"Infragraph JSON saved to: {export_path}")
    except OSError as e:
        error(f"Writing to {export_path}:", e)
```

### B9: CLI Integration

```python
# In cli() function around line 1333
if config['output_format'] == 'infragraph':
    nb_network.export_graph_infragraph()
    return 0
```

### B10: Testing

**Unit tests:**

1. `test_interface_mapper.py`
   - Test interface→component index mapping
   - Test consistent ordering
   - Test mapping retrieval

2. `test_infragraph_exporter.py`
   - Test device template creation
   - Test instance creation
   - Test link creation with speeds
   - Test edge creation

3. `test_infragraph_validation.py`
   - Test output validates with InfraGraphService
   - Test generated graph has correct nodes
   - Test edge connectivity

**System tests:**

1. Export real NetBox topology
2. Validate JSON with infragraph schema
3. Load with InfraGraphService
4. Verify graph structure

## Implementation Checklist

### Phase A: Enhance NetworkX Graph

- [ ] A1: Enhance interface node data
  - [ ] Update `_get_nb_interfaces()` to store all fields
  - [ ] Add device_id, speed, tags, etc.
  - [ ] Test field population

- [ ] A2: Add cable edge attributes
  - [ ] Update `_add_cable_to_graph()` to store cable metadata
  - [ ] Test edge attributes

- [ ] A3: Add device type caching
  - [ ] Add fields to NBNetwork class
  - [ ] Update `_get_nb_devices()` to build cache
  - [ ] Update `_get_nb_interfaces()` to build interface inventory
  - [ ] Add `_find_device_by_id()` helper

- [ ] A4: Test enhanced graph
  - [ ] Create `test_enhanced_graph.py`
  - [ ] Test all existing exporters still work
  - [ ] Run system tests

### Phase B: Infragraph Export

- [ ] B1: Add infragraph dependency
  - [ ] Add to requirements.txt
  - [ ] Update documentation

- [ ] B2: Create InterfaceMapper class
  - [ ] Implement mapping logic
  - [ ] Unit tests

- [ ] B3: Create InfragraphExporter class skeleton
  - [ ] Basic structure
  - [ ] Sanitization helper

- [ ] B4: Implement device template creation
  - [ ] Build from cached device types
  - [ ] Add components

- [ ] B5: Implement instance creation
  - [ ] Map NetBox devices to instances

- [ ] B6: Implement link creation
  - [ ] Extract speeds
  - [ ] Create link types

- [ ] B7: Implement edge creation
  - [ ] Map cables to edges
  - [ ] Use interface mapper
  - [ ] Set endpoints correctly

- [ ] B8: Add export method to NBFactory
  - [ ] Implement `export_graph_infragraph()`
  - [ ] Add validation option

- [ ] B9: Update CLI
  - [ ] Support `--output infragraph`

- [ ] B10: Testing
  - [ ] Unit tests for all components
  - [ ] System tests with real data
  - [ ] Validation with InfraGraphService

### Documentation

- [ ] Update README.md
  - [ ] Add infragraph to supported formats
  - [ ] Add usage example

- [ ] Update CLAUDE.md
  - [ ] Add infragraph development notes

- [ ] Create infragraph mapping documentation
  - [ ] Document NetBox → infragraph mapping decisions
  - [ ] Include examples

## Benefits Summary

### Single Code Path
- One place to collect NetBox data
- All exporters benefit from enhancements
- Easier to maintain

### No Data Loss
- Complete NetBox data preserved in graph
- Interface speeds for bandwidth
- Cable metadata for validation
- Tags for filtering

### Better Performance
- Cached device type inventory
- Direct device_id lookups (no graph traversal)
- Pre-built interface lists

### Maintainability
- Backward compatible with existing exporters
- Clear separation: data collection vs export
- Testable components

### Accuracy
- Use actual NetBox interface speeds for link bandwidth
- Proper component indexing
- Validated output using InfraGraphService

## Questions & Decisions

### Q1: Component granularity
**Question:** Should we support other component types (CPU, XPU, Memory)?

**Decision:** Start with Port/NIC only. NetBox primarily tracks network connectivity. Future enhancement could map device modules to components.

### Q2: Interface ordering
**Question:** How to ensure consistent interface→component index mapping?

**Decision:** Sort interfaces by name when building component list. Ensures same device type always has same component indices.

### Q3: Link types
**Question:** Create links per speed or use generic?

**Decision:** Create per-speed links (1G, 10G, 25G, etc.) from actual interface speeds. More accurate for infragraph.

### Q4: Validation
**Question:** Always validate or make it optional?

**Decision:** Make validation optional via config flag. Useful for testing but adds dependency on InfraGraphService.

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| A1-A2 | Enhance interface/cable data | 2-3 hours |
| A3 | Add device type caching | 2-3 hours |
| A4 | Test enhanced graph | 2-3 hours |
| B1-B3 | Setup & skeleton | 1-2 hours |
| B4-B7 | Core export logic | 4-5 hours |
| B8-B9 | Integration | 1-2 hours |
| B10 | Testing & validation | 3-4 hours |
| Docs | Documentation updates | 2 hours |
| **Total** | | **17-24 hours** |

## References

- [Infragraph Website](https://infragraph.dev/)
- [Infragraph Schema](https://infragraph.dev/schema/)
- [Infragraph OpenAPI Spec](https://infragraph.dev/openapi.html)
- [Infragraph PyPI](https://pypi.org/project/infragraph/)
- [Infragraph GitHub](https://github.com/Keysight/infragraph)
- [InfraGraphService Source](https://github.com/Keysight/infragraph/blob/main/src/infragraph/infragraph_service.py)
