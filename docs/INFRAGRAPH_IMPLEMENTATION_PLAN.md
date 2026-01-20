# Infragraph Export Implementation Plan

## Overview

This document outlines the plan to add infragraph export capability to nrx. The implementation follows a two-phase approach:

1. **Phase A**: Enhance NetworkX graph structure to preserve NetBox data without loss
2. **Phase B**: Implement infragraph export using the enhanced graph data

This approach ensures a single code path for data collection that benefits all export formats.

## Critical Design Decision: Device Type Templates for Infragraph

**Problem:** Infragraph requires consistent, template-based device definitions. Using actual device interfaces (which may have per-device customizations like modules, subinterfaces, or missing interfaces) leads to:

- Inconsistent component indices across devices of the same type
- Unpredictable template structures
- Missing edges when device interfaces don't match the "sample" device

**Solution:** For infragraph export only, fetch interface templates directly from **NetBox Device Types API**:

- ✅ All devices of the same type get identical component indices
- ✅ Predictable, consistent templates regardless of device customizations
- ✅ Edges for non-template interfaces are skipped with clear warnings
- ✅ Users are directed to fix NetBox device type definitions (canonical source)

**Impact on Other Exporters:** None. Existing exporters (clab, cml, cyjs) continue to use actual device interfaces collected from individual devices. This change only affects infragraph export logic.

**Note:** For background on infragraph concepts and design rationale, see [INFRAGRAPH_EXPORT_SUMMARY.md](INFRAGRAPH_EXPORT_SUMMARY.md).

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
                'device_type_id': device.device_type.id,  # For fetching device type templates
            }
```

**Important:** Use device names, not IDs. NetBox IDs are instance-specific database keys that change when data is imported into different NetBox instances.

**Note on Interface Handling:**

- **For existing exporters (clab, cml, cyjs):** Continue using actual device interfaces collected via `_get_nb_interfaces()`. This preserves per-device customizations (modules, subinterfaces, etc.)
- **For infragraph export only:** Fetch canonical interface templates from NetBox Device Types API. This ensures consistent component indices across all devices of the same type.

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
- Device name-based lookups (portable across NetBox instances)
- Stores device_type_id for fetching canonical templates

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

Purpose: Map NetBox interface names to infragraph component indices (0-based, sequential) using NetBox Device Type templates

```python
class InterfaceMapper:
    """Maps NetBox interfaces to infragraph component indices using Device Type templates"""

    def __init__(self, nb_net, nb_session):
        self.nb_net = nb_net
        self.nb_session = nb_session
        # "device_name.interface_name" → (component_name, idx)
        # Using device_name (not ID) for portability across NetBox instances
        self.interface_to_component = {}
        self.device_type_templates = {}  # (vendor, model) → interface names in NetBox order

    def _fetch_device_type_templates(self):
        """Fetch canonical interface templates from NetBox Device Types API

        This ensures consistent component indices regardless of per-device customizations.
        Preserves NetBox's interface ordering as the canonical source of truth.
        """
        for device_type_key, device_type_info in self.nb_net.device_types.items():
            device_type_id = device_type_info['device_type_id']

            # Fetch device type object with interface templates
            device_type_obj = self.nb_session.dcim.device_types.get(id=device_type_id)

            # Get ALL interfaces defined in the device type (not from actual devices)
            type_interfaces = list(device_type_obj.interfaces.all())

            # Preserve NetBox's interface order (do NOT sort)
            # NetBox device type interface order is the canonical ordering
            # Users must ensure interfaces are ordered correctly in NetBox
            interface_names = [iface.name for iface in type_interfaces]

            self.device_type_templates[device_type_key] = interface_names

    def build_mappings(self):
        """Build interface→component mapping with 0-based sequential indices

        Uses Device Type templates to ensure all devices of the same type have
        identical component indices, even if individual devices have custom interfaces.
        """
        # First fetch canonical templates from NetBox Device Types
        self._fetch_device_type_templates()

        # For each device type, create consistent component index mapping
        for device_type_key, template_interfaces in self.device_type_templates.items():
            # Apply mapping to ALL devices of this type
            for device in self.nb_net.devices:
                if (device['vendor'], device['model']) == device_type_key:
                    # Map each interface from device type template
                    for idx, interface_name in enumerate(template_interfaces):
                        mapping_key = f"{device['name']}.{interface_name}"
                        # idx is 0-based sequential, as required by infragraph
                        self.interface_to_component[mapping_key] = ("port", idx)

    def get_component_index(self, device_name, interface_name):
        """Get (component_name, component_idx) for an interface

        Args:
            device_name: NetBox device name (portable identifier)
            interface_name: NetBox interface name

        Returns:
            Tuple of (component_name, component_idx) where idx is 0-based,
            or None if interface not in device type template
        """
        key = f"{device_name}.{interface_name}"
        return self.interface_to_component.get(key)
```

**Key design decisions:**

- Fetch interface templates from **NetBox Device Types API** (not from actual devices)
- Use device **names** not IDs (portable across NetBox instances)
- **Preserve NetBox's interface order** - Trust device type interface ordering from NetBox
  - Do NOT sort locally (no alphabetical, natural, or custom sorting)
  - NetBox device type order is canonical source of truth
  - Component indices match NetBox device type interface order exactly
  - Users must ensure device type interfaces are ordered correctly in NetBox UI

- Generate 0-based sequential indices (infragraph requirement)
- Same device type always has same component indices (if device type unchanged in NetBox)
- **Strict enforcement:** Interfaces not in device type template return None

### B3: InfragraphExporter Class

```python
from infragraph import Device, Infrastructure, Component, InfrastructureEdge

class InfragraphExporter:
    """Export NetBox topology to infragraph format"""

    def __init__(self, network_graph, nb_net, nb_session, topology_name, config):
        self.G = network_graph
        self.nb_net = nb_net
        self.nb_session = nb_session  # Need for fetching device type templates
        self.topology_name = topology_name
        self.config = config
        self.mapper = InterfaceMapper(nb_net, nb_session)
        self.device_templates = {}  # (vendor, model) → Device object

    def build_infrastructure(self):
        """Main export method"""
        # Build interface mappings from Device Type templates
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
    """Create Device objects from NetBox Device Type templates

    Uses interface templates from Device Types (not from actual devices),
    ensuring consistent component counts across all devices of the same type.
    """
    for device_type_key, device_type_info in self.nb_net.device_types.items():
        # Create Device using infragraph SDK
        device = Device()
        device.name = self._sanitize_name(
            f"{device_type_info['vendor']}_{device_type_info['model']}"
        )
        device.description = (
            f"{device_type_info['vendor_name']} {device_type_info['model_name']}"
        )

        # Get interface template from Device Type (already fetched by InterfaceMapper)
        template_interfaces = self.mapper.device_type_templates.get(device_type_key, [])
        if template_interfaces:
            port = device.components.add(
                name="port",
                description="Network interface port",
                count=len(template_interfaces)  # Count from device type, not actual devices
            )
            port.choice = Component.PORT

        # Cache and add to infrastructure
        self.device_templates[device_type_key] = device
        infra.devices.append(device)
```

**Key changes from original plan:**

- Uses `mapper.device_type_templates` instead of `nb_net.device_type_interfaces`
- Component count comes from Device Type definition, not from sample device
- Ensures all devices of same type have identical template structure

### B5: Instance Creation with Automatic Grouping

**Key Decision (from INFRAGRAPH_INSTANCE_INDEXING.md):**

- Group devices by (site, role, vendor, model) initially
- Use compaction routine to automatically remove unnecessary parts from names
- Devices with same (site, role, type) become instances with count > 1
- Preserve NetBox name-based ordering (requested via `ordering='name'` from API)

```python
def _build_instance_index(self):
    """
    Build instance indexing with automatic grouping and name optimization

    Strategy:
    1. Always group by (site, role, vendor, model) initially
    2. Compaction routine removes unnecessary parts (site, vendor) if they don't add distinction
    3. Assign sequential indices within each group preserving NetBox name-based ordering
       (devices already ordered by name from API via ordering='name')
    """
    instance_groups = {}

    for device in self.nb_net.devices:
        # Always start with maximal grouping
        instance_key = (
            device.get('site', ''),
            device.get('role', ''),
            device['vendor'],
            device['model']
        )

        if instance_key not in instance_groups:
            instance_groups[instance_key] = []
        instance_groups[instance_key].append(device)

    # Smart compaction: find shortest conflict-free names
    optimal_names = self._compact_instance_names(instance_groups)

    # Assign instance names and indices
    for instance_key, devices in instance_groups.items():
        # Preserve NetBox ordering as returned by the API
        # Note: Devices should be fetched with ordering='name' from NetBox API
        instance_name = optimal_names[instance_key]

        for idx, device in enumerate(devices):
            device['instance_name'] = instance_name
            device['instance_index'] = idx

def _compact_instance_names(self, instance_groups):
    """
    Generate shortest possible instance names by removing unnecessary parts

    **See INFRAGRAPH_INSTANCE_INDEXING.md Q4 for the complete authoritative
    algorithm.**

    Strategy:
    1. Start with maximal name: site_role_vendor_model_full
    2. Try removing site (if still unique)
    3. Try removing vendor (if still unique)
    4. Try compacting model (full → extended → core) only if still unique
    5. Stop at the shortest unique form

    Example:
    - Start: dc1_leaf_arista_7050sx64
    - Try without site: leaf_arista_7050sx64 → Unique? Yes → Keep
    - Try without vendor: leaf_7050sx64 → Unique? Yes → Keep
    - Try compact model: leaf_7050sx → Unique? Yes → Keep
    - Try compact model: leaf_7050 → Unique? Yes → Use it

    Returns: {instance_key → optimized_name}
    """
    # Implementation: See INFRAGRAPH_INSTANCE_INDEXING.md Q4 for complete code
    # Key helper functions needed:
    # - _build_name_without_site(role, vendor, model_part)
    # - _build_name_without_vendor(site, role, model_part)
    # - _build_name_without_site_vendor(role, model_part)
    # - _extract_model_core(model) → "7050"
    # - _extract_model_extended(model) → "7050sx"
    # - _extract_model_full(model) → "7050sx64"
    # - _is_unique_across_groups(candidate_name, instance_key, instance_groups)

def _build_instances(self, infra):
    """
    Create infragraph Instances from grouped NetBox devices

    After _build_instance_index() has assigned instance_name and instance_index
    to each device, group them and create Instance objects with proper count.
    """
    # Build instance index first
    self._build_instance_index()

    # Group devices by instance_name
    instances_map = {}  # instance_name → [devices]
    for device in self.nb_net.devices:
        instance_name = device['instance_name']
        if instance_name not in instances_map:
            instances_map[instance_name] = []
        instances_map[instance_name].append(device)

    # Create Instance objects
    for instance_name, devices in instances_map.items():
        # All devices in group have same type
        device_type_key = (devices[0]['vendor'], devices[0]['model'])
        device_template = self.device_templates[device_type_key]

        # Get representative site/role for description
        site = devices[0].get('site', 'unknown')
        role = devices[0].get('role_name', 'unknown')

        instance = infra.instances.add(
            name=self._sanitize_name(instance_name),
            description=f"{role} - {site} (count: {len(devices)})",
            device=device_template.name,
            count=len(devices)  # Multiple devices → count > 1!
        )

# Example Results:
# Single-site export:
#   leaf_7050: count=4  (site removed by compaction)
#   spine_7280: count=2
#
# Multi-site with same devices:
#   dc1_leaf_7050: count=4  (site kept - needed for distinction)
#   dc2_leaf_7050: count=4
#
# Multi-site with different devices:
#   leaf_7050: count=2  (site removed - arista unique to dc1)
#   leaf_9300: count=2  (site removed - cisco unique to dc2)
```

**Key Benefits:**

- ✅ Automatic grouping (no user configuration needed)
- ✅ Shortest possible names via compaction
- ✅ Stable indices via NetBox name-based ordering
- ✅ Handles single-site, multi-site, and mixed scenarios

### B6: Link Creation

```python
def _build_links(self, infra):
    """Create link definitions with bandwidth from interface speeds

    Handles fractional speeds (2.5G, 12.5G) and creates unique link names.
    """
    # Analyze interface speeds to determine link types needed
    speeds_used = set()
    for iface in self.nb_net.interfaces:
        if iface.get('speed', 0) > 0:
            speeds_used.add(iface['speed'])

    # Create links for each speed
    # Convert Kbps to Gbps, preserving fractional precision
    for speed_kbps in speeds_used:
        speed_gbps = speed_kbps / 1_000_000

        # Keep fractional precision for non-integer speeds (2.5G, 12.5G)
        if speed_gbps == int(speed_gbps):
            link_name = f"ethernet_{int(speed_gbps)}g"
        else:
            # Use underscore for decimal point (2.5G → ethernet_2_5g)
            link_name = f"ethernet_{str(speed_gbps).replace('.', '_')}g"

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

### B7: Edge Creation with Instance Indexing

**CRITICAL:** Validate that interfaces exist in device type templates before creating edges.

```python
def _build_edges(self, infra):
    """Convert cables to Infrastructure edges using instance names and indices

    Only creates edges for interfaces that exist in device type templates.
    Skips edges where interfaces are device-specific customizations.
    """
    skipped_edges = []
    created_edges = 0

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

        # Find device objects to get instance_name and instance_index
        device_a = self._find_device_by_name(device_name_a)
        device_b = self._find_device_by_name(device_name_b)

        # Map to component indices using device type templates
        mapping_a = self.mapper.get_component_index(device_name_a, iface_a['name'])
        mapping_b = self.mapper.get_component_index(device_name_b, iface_b['name'])

        # STRICT ENFORCEMENT: Skip edge if interface not in device type template
        if mapping_a is None:
            skipped_edges.append((device_name_a, iface_a['name'], "not in device type"))
            continue

        if mapping_b is None:
            skipped_edges.append((device_name_b, iface_b['name'], "not in device type"))
            continue

        component_a, idx_a = mapping_a
        component_b, idx_b = mapping_b

        # Validate and determine link type from interface speeds
        speed_a = iface_a.get('speed', 0)
        speed_b = iface_b.get('speed', 0)

        # Use minimum speed (conservative approach for mismatched speeds)
        # Log warning if speeds differ
        if speed_a != speed_b and speed_a > 0 and speed_b > 0:
            link_speed = min(speed_a, speed_b)
            print(f"⚠ Speed mismatch: {device_name_a}:{iface_a['name']} ({speed_a}Kbps) "
                  f"<-> {device_name_b}:{iface_b['name']} ({speed_b}Kbps), using {link_speed}Kbps")
        else:
            link_speed = speed_a or speed_b or 0

        link_name = self._get_link_name(link_speed)

        # Create edge using ONE2ONE scheme (point-to-point cable)
        infra_edge = infra.edges.add(
            scheme=InfrastructureEdge.ONE2ONE,
            link=link_name
        )

        # Set endpoints: instance[device_idx].component[component_idx]
        # CRITICAL: device_idx comes from instance_index (not always 0!)
        instance_name_a = self._sanitize_name(device_a['instance_name'])
        instance_name_b = self._sanitize_name(device_b['instance_name'])
        instance_idx_a = device_a['instance_index']
        instance_idx_b = device_b['instance_index']

        infra_edge.ep1.instance = f"{instance_name_a}[{instance_idx_a}]"
        infra_edge.ep1.component = f"{component_a}[{idx_a}]"
        infra_edge.ep2.instance = f"{instance_name_b}[{instance_idx_b}]"
        infra_edge.ep2.component = f"{component_b}[{idx_b}]"

        created_edges += 1

    # Report skipped edges
    if skipped_edges:
        print(f"\n⚠ Warning: Skipped {len(skipped_edges)} edges due to interfaces not in device type templates:")
        for device, iface, reason in skipped_edges:
            print(f"  - {device}:{iface} ({reason})")
        print(f"\n✓ Action: Update NetBox device type definitions to include these interfaces")
        print(f"  Created {created_edges} edges successfully\n")

def _find_device_by_name(self, device_name):
    """Find device in nb_net.devices by name"""
    for device in self.nb_net.devices:
        if device['name'] == device_name:
            return device
    raise ValueError(f"Device not found: {device_name}")

def _get_link_name(self, speed_kbps):
    """Determine link name from interface speed, preserving fractional precision

    Args:
        speed_kbps: Speed in kilobits per second

    Returns:
        Link name like "ethernet_25g", "ethernet_2_5g", or "ethernet"

    Examples:
        25000000 Kbps → "ethernet_25g"
        2500000 Kbps → "ethernet_2_5g"
        12500000 Kbps → "ethernet_12_5g"
        0 Kbps → "ethernet"
    """
    if speed_kbps > 0:
        speed_gbps = speed_kbps / 1_000_000

        # Keep fractional precision for non-integer speeds
        if speed_gbps == int(speed_gbps):
            return f"ethernet_{int(speed_gbps)}g"
        else:
            # Use underscore for decimal point (2.5G → ethernet_2_5g)
            return f"ethernet_{str(speed_gbps).replace('.', '_')}g"

    return "ethernet"
```

**Key improvements:**

- Use `device_name` from interface data (portable identifier)
- Use `instance_name` and `instance_index` from device (from grouping)
- Correctly reference devices within instance groups (not always [0])
- Component indices are 0-based sequential from InterfaceMapper
- **STRICT VALIDATION:** Interfaces not in device type templates are skipped with clear warnings
- **Speed validation:** Validates both endpoints and uses minimum speed for mismatched pairs
- **Fractional precision:** Link names preserve fractional speeds (2.5G → "ethernet_2_5g")
- **User guidance:** Clear warnings for skipped edges and speed mismatches

### B8: NetBox Metadata Annotations

**Key Decision (from INFRAGRAPH_INSTANCE_INDEXING.md Q3):**

- Use infragraph's standard `annotate_graph` API to preserve NetBox metadata
- Annotations separate infrastructure model from use-case-specific data
- Produces two files: clean infrastructure + annotated version

```python
def _add_netbox_annotations(self, json_output, output_dir):
    """
    Add NetBox metadata as annotations using infragraph API

    Annotations preserve the mapping between infragraph nodes and NetBox devices/interfaces,
    enabling reverse lookups and metadata queries.

    Annotates both:
    - Instance nodes (devices) with device metadata
    - Component nodes (interfaces) with interface metadata
    """
    try:
        from infragraph import InfraGraphService, AnnotateRequest

        # Load infrastructure into service
        service = InfraGraphService()
        service.set_graph(json_output)

        # Build annotation request
        annotate_request = AnnotateRequest()

        # Annotate device instance nodes
        for device in self.nb_net.devices:
            # Node ID format: instance_name.instance_index
            instance_name = self._sanitize_name(device['instance_name'])
            instance_idx = device['instance_index']
            node_id = f"{instance_name}.{instance_idx}"

            # Add device metadata as annotations
            annotate_request.nodes.add(
                name=node_id,
                attribute="device_name",
                value=device['name']
            )
            annotate_request.nodes.add(
                name=node_id,
                attribute="site",
                value=device.get('site', '')
            )
            annotate_request.nodes.add(
                name=node_id,
                attribute="role",
                value=device.get('role', '')
            )
            annotate_request.nodes.add(
                name=node_id,
                attribute="platform",
                value=device.get('platform', '')
            )
            # Optional: Add source_id for reference to original data source
            annotate_request.nodes.add(
                name=node_id,
                attribute="source_id",
                value=str(device['id'])
            )

        # Annotate Device component nodes (not instance components)
        self._annotate_device_components(annotate_request)

        # Apply annotations
        service.annotate_graph(annotate_request)

        # Export annotated graph
        annotated_output = service.get_graph()
        annotated_file = f"{self.topology_name}.infragraph.annotated.json"
        annotated_path = f"{output_dir}/{annotated_file}"

        with open(annotated_path, 'w', encoding='utf-8') as f:
            f.write(annotated_output)
        print(f"Annotated infragraph saved to: {annotated_path}")

        return True

    except ImportError:
        print("⚠ infragraph package not available, skipping annotations")
        return False
    except Exception as e:
        print(f"⚠ Annotation failed: {e}")
        return False

def _annotate_device_components(self, annotate_request):
    """
    Annotate Device component nodes with interface names

    Annotates at the Device level, not Instance level.
    This ensures interface names are defined once per device type, not per device instance.

    Component node ID format: device_name.port.component_idx
    (where device_name is like "arista_dcs_7050sx_64")
    """
    # For each device type that has been created as a Device
    for device_type_key, device in self.device_templates.items():
        # Get the device name
        device_name = device.name  # Already sanitized

        # Get interface template for this device type
        template_interfaces = self.mapper.device_type_templates.get(device_type_key, [])

        # Annotate each component in the Device
        for component_idx, interface_name in enumerate(template_interfaces):
            # Component node ID at Device level: device_name.port.component_idx
            # NOT at instance level (no instance_idx)
            component_node_id = f"{device_name}.port.{component_idx}"

            # Annotate with interface name (maps component_idx back to interface name)
            annotate_request.nodes.add(
                name=component_node_id,
                attribute="interface_name",
                value=interface_name
            )

# Example annotations usage:

# Query devices by original device name:
# filter = QueryNodeFilter()
# filter.choice = QueryNodeFilter.ATTRIBUTE_FILTER
# filter.attribute_filter.name = "device_name"
# filter.attribute_filter.operator = QueryNodeId.EQ
# filter.attribute_filter.value = "leaf01"
# matches = service.query_graph(filter)  # Returns: leaf_7050.0

# Query Device component nodes by interface name:
# filter = QueryNodeFilter()
# filter.choice = QueryNodeFilter.ATTRIBUTE_FILTER
# filter.attribute_filter.name = "interface_name"
# filter.attribute_filter.operator = QueryNodeId.EQ
# filter.attribute_filter.value = "Ethernet1"
# matches = service.query_graph(filter)  # Returns: Device components (e.g., "arista_dcs_7050sx_64.port.0")

# Reverse lookup: Given Device component, find interface name
# node = service.get_node("arista_dcs_7050sx_64.port.5")
# interface_name = node.annotations.get("interface_name")  # Returns: "Ethernet6"

# Note: Instance components (leaf_7050.0.port.5) are NOT annotated
# They reference Device (arista_dcs_7050sx_64) which has the interface names
```

**Benefits:**

- ✅ Preserves original device names for reverse lookup on Instance nodes
- ✅ Maps component indices back to interface names on Device components
- ✅ Annotations at Device level (not duplicated per instance)
- ✅ Queryable via infragraph `query_graph` API
- ✅ Standard infragraph pattern (not custom format)
- ✅ Two-file output: clean + annotated
- ✅ Site, role, platform metadata available on instances
- ✅ Interface names defined once per device type (not per instance)
- ✅ Clean attribute names (no vendor-specific prefixes)
- ✅ No per-device configuration data (MTU, descriptions) that can vary

**Configuration:**
```toml
[INFRAGRAPH]
# Add metadata annotations to exported graph (default: true)
ADD_ANNOTATIONS = true
```

### B9: Export Method in NBFactory

```python
def export_graph_infragraph(self):
    """Export network topology in infragraph format with annotations"""
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

    # Write base infrastructure file
    dir_path = create_output_directory(self.topology_name, self.config['output_dir'])
    export_file = f"{self.topology_name}.infragraph.json"
    export_path = f"{dir_path}/{export_file}"

    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"Infragraph JSON saved to: {export_path}")
    except OSError as e:
        error(f"Writing to {export_path}:", e)

    # Add NetBox annotations (optional, enabled by default)
    if self.config.get('infragraph_add_annotations', True):
        exporter._add_netbox_annotations(json_output, dir_path)
```

### B10: CLI Integration

```python
# In cli() function around line 1333
if config['output_format'] == 'infragraph':
    nb_network.export_graph_infragraph()
    return 0
```

### B11: Testing

**Unit tests:**

1. `test_interface_mapper.py`

    - Test device type template fetching from NetBox API
    - Test interface→component index mapping from device types
    - Test consistent ordering across all devices of same type
    - Test mapping retrieval
    - Test return None for interfaces not in device type
    - Test with mock NetBox API responses

2. `test_instance_grouping.py`

    - Test automatic grouping by (site, role, vendor, model)
    - Test name compaction algorithm
    - Test single-site exports (site removed)
    - Test multi-site exports (site kept when needed)
    - Test preservation of NetBox name-based ordering for stable indices

3. `test_infragraph_exporter.py`

    - Test device template creation from device types
    - Test component counts match device type interface counts
    - Test instance creation with proper count
    - Test instance indexing within groups
    - Test link creation with speeds
    - Test edge creation with correct instance indices
    - Test edge skipping for non-template interfaces
    - Test warning output for skipped edges

4. `test_infragraph_annotations.py`

    - Test device instance metadata annotation
    - Test Device component annotation (interface names)
    - Test `_annotate_device_components()` method
    - Test annotate_graph API integration
    - Test reverse lookup by NetBox device name (Instance level)
    - Test interface queries by name (Device level)
    - Test two-file output (clean + annotated)
    - Verify annotations only in annotated file (not in clean)
    - Verify instance components are NOT annotated (reference Device)

5. `test_infragraph_validation.py`

    - Test output validates with InfraGraphService
    - Test generated graph has correct nodes
    - Test edge connectivity
    - Test annotations queryable

**System tests:**

1. Export real NetBox topology (single-site)
2. Export real NetBox topology (multi-site)
3. Validate JSON with infragraph schema
4. Load with InfraGraphService
5. Verify graph structure and node naming
6. Test annotation queries

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

    - [ ] Add fields to NBNetwork class (`device_types`, `device_name_to_type`)
    - [ ] Update `_get_nb_devices()` to cache device types with `device_type_id`
    - [ ] ~~Update `_get_nb_interfaces()` to build interface inventory~~ (NOT NEEDED - infragraph fetches from Device Types API)
    - [ ] Add `_find_device_by_name()` helper

- [ ] A4: Test enhanced graph

    - [ ] Create `test_enhanced_graph.py`
    - [ ] Test all existing exporters still work
    - [ ] Run system tests

### Phase B: Infragraph Export

- [ ] B1: Add infragraph dependency

    - [ ] Add to requirements.txt
    - [ ] Update documentation

- [ ] B2: Create InterfaceMapper class

    - [ ] Implement `__init__` with `nb_net` and `nb_session` parameters
    - [ ] Implement `_fetch_device_type_templates()` - Fetch from NetBox Device Types API
    - [ ] Implement `build_mappings()` - Use device type templates (not actual devices)
    - [ ] Implement `get_component_index()` - Return None for non-template interfaces
    - [ ] Unit tests for device type template fetching
    - [ ] Unit tests for mapping with missing interfaces

- [ ] B3: Create InfragraphExporter class skeleton

    - [ ] Basic structure
    - [ ] Sanitization helper

- [ ] B4: Implement device template creation

    - [ ] Build from cached device types
    - [ ] Use `mapper.device_type_templates` for component counts
    - [ ] Add port components with counts from device type (not sample device)

- [ ] B5: Implement instance grouping and indexing

    - [ ] `_build_instance_index()` - Group by (site, role, vendor, model)
    - [ ] `_compact_instance_names()` - Optimize names by removing unnecessary parts
    - [ ] `_extract_model_core()` - Extract short model identifiers
    - [ ] `_is_unique_across_groups()` - Check name uniqueness
    - [ ] Preserve NetBox name-based ordering within groups (from API ordering='name')
    - [ ] Assign instance_name and instance_index to each device
    - [ ] Unit tests for grouping logic
    - [ ] Unit tests for name compaction

- [ ] B6: Implement instance creation

    - [ ] `_build_instances()` - Create Instance objects from grouped devices
    - [ ] Set proper count for each instance
    - [ ] Unit tests

- [ ] B7: Implement link creation

    - [ ] Extract speeds
    - [ ] Create link types

- [ ] B8: Implement edge creation

    - [ ] Map cables to edges using device type templates
    - [ ] Validate interfaces exist in device type templates (return None from mapper)
    - [ ] Skip edges with non-template interfaces
    - [ ] Collect and report skipped edges with clear warnings
    - [ ] Use interface mapper with None-checking
    - [ ] Use `instance_name` and `instance_index` from devices
    - [ ] Implement `_find_device_by_name()` helper
    - [ ] Set endpoints correctly with proper instance indices
    - [ ] Unit tests for edge skipping behavior

- [ ] B9: Implement NetBox annotations

    - [ ] `_add_netbox_annotations()` - Add metadata via annotate_graph API
    - [ ] Annotate Instance nodes with device_name, site, role, platform, source_id
    - [ ] Implement `_annotate_device_components()` - Annotate Device components
    - [ ] Annotate Device components (not instance components) with interface names
    - [ ] Interface names come from device type templates
    - [ ] Do NOT annotate instance components (they reference Device)
    - [ ] Write annotated output file (separate from clean file)
    - [ ] Unit tests for Instance annotation logic
    - [ ] Unit tests for Device component annotation logic
    - [ ] Verify instance components are NOT annotated

- [ ] B10: Add export method to NBFactory

    - [ ] Implement `export_graph_infragraph()`
    - [ ] Call `_add_netbox_annotations()` if enabled
    - [ ] Add validation option

- [ ] B11: Update CLI

    - [ ] Support `--output infragraph`

- [ ] B12: Testing

    - [ ] Unit tests for all components
    - [ ] System tests with single-site data
    - [ ] System tests with multi-site data
    - [ ] Validation with InfraGraphService
    - [ ] Test annotation queries

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

## Key Design Decisions

All design decisions have been finalized and documented in [INFRAGRAPH_INSTANCE_INDEXING.md](INFRAGRAPH_INSTANCE_INDEXING.md).

### Decision 1: Use Device Names, Not IDs ✅

**Problem:** NetBox database IDs change between instances
**Solution:** Use device names as portable identifiers
**Impact:** Exports from different NetBox instances produce consistent infragraph output

### Decision 2: Automatic Instance Grouping ✅

**Problem:** Need to map NetBox devices to infragraph instances with count
**Solution:** Always group by (site, role, vendor, model) initially
**Benefits:**

- Devices from different sites never accidentally combined
- Automatic name compaction removes unnecessary parts
- No user configuration required

### Decision 3: Smart Name Compaction ✅

**Problem:** Instance names can be verbose (dc1_leaf_arista_7050)
**Solution:** Progressive compaction removes unnecessary parts
**Examples:**

- Single-site: `leaf_7050` (site removed)
- Multi-site same devices: `dc1_leaf_7050`, `dc2_leaf_7050` (site needed)
- Multi-site different devices: `leaf_7050`, `leaf_9300` (site removed, vendor removed)

### Decision 4: Request and Preserve NetBox Name-Based Ordering ✅

**Problem:** Need stable instance indices across exports with user control
**Solution:** Request `ordering='name'` from NetBox API and preserve that ordering within groups
**Benefits:**

- Users have direct control via NetBox device naming
- Ordering depends on NetBox's implementation (typically case-sensitive alphabetical)
- Mirrors what users see in NetBox when sorted by name
- Portable across NetBox instances when names are preserved
- No local re-sorting ensures consistency with NetBox

**Implementation:**
```python
# In _get_nb_devices():
devices = nb_session.dcim.devices.filter(..., ordering='name')

# In _build_instance_index():
# Preserve API ordering (do not re-sort)
for instance_key, devices in instance_groups.items():
    # devices are already in NetBox name order
    ...
```

### Decision 5: Annotations for Metadata ✅

**Problem:** Need to preserve NetBox device names for reverse lookup
**Solution:** Use infragraph's `annotate_graph` API
**Benefits:**

- Standard infragraph pattern
- Queryable via `query_graph` API
- Two-file output: clean + annotated
- Separates infrastructure from metadata

**Reference:** See [INFRAGRAPH_INSTANCE_INDEXING.md](INFRAGRAPH_INSTANCE_INDEXING.md) for complete rationale and examples.

## Questions & Decisions (Legacy)

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
