# Infragraph Instance Indexing Strategy

## Problem Statement

NetBox and Infragraph have fundamentally different models for representing device instances:

### NetBox Model
- **Device name**: Unique identifier (e.g., `leaf01`, `leaf02`, `spine01`)
- **Device type**: Template reference (manufacturer + model)
- **Device names can be changed** without affecting the physical topology

### Infragraph Model
- **Device**: Reusable template (e.g., `arista_dcs_7050`)
- **Instance**: Named group of devices with count (e.g., `leaf_switch` with count=4)
- **Actual nodes**: Instance name + index (e.g., `leaf_switch.0`, `leaf_switch.1`, `leaf_switch.2`, `leaf_switch.3`)

### The Mismatch

```python
# NetBox: Each device has a unique name
devices = [
    "leaf01" (Arista DCS-7050, role=leaf),
    "leaf02" (Arista DCS-7050, role=leaf),
    "spine01" (Arista DCS-7280, role=spine)
]

# Infragraph: Instances with indices
instances = [
    Instance(name="leaf", device="arista_7050", count=2),  # → leaf.0, leaf.1
    Instance(name="spine", device="arista_7280", count=1)  # → spine.0
]

# CANNOT map: leaf01 → leaf01.0
# Because there is no "leaf01" device template in infragraph!
```

### Critical Requirements

1. **Stable indexing**: Device indices must not change if NetBox device names change
2. **Reversible mapping**: Must be able to map back from infragraph to NetBox
3. **Type consistency**: Each instance must use exactly one device template
4. **Future input support**: nrx should be able to import infragraph as input format
5. **Preserve NetBox metadata**: Device names, sites, etc. must be preserved somehow

## Instance Grouping Strategies

### Option A: Role-Based Grouping (Simple)

**Strategy:** Use device role as instance name

```python
# Grouping logic
instance_key = (role)
instance_name = role

# Example
NetBox devices:
  leaf01 (role=leaf, type=Arista-7050)
  leaf02 (role=leaf, type=Arista-7050)
  spine01 (role=spine, type=Arista-7280)

Infragraph instances:
  Instance(name="leaf", device="arista_7050", count=2)
  Instance(name="spine", device="arista_7280", count=1)
```

**Pros:**
- Simple and intuitive
- Matches common network design patterns
- Short instance names

**Cons:**
- ❌ **FAILS if same role has multiple device types!**
  ```python
  leaf01 (role=leaf, type=Arista-7050)
  leaf02 (role=leaf, type=Arista-7280)  # Different type!
  # Cannot both be in instance "leaf" - need different devices!
  ```

**Verdict:** ❌ Not viable - breaks type consistency requirement

### Option B: Role + Device Type Grouping (Recommended)

**Strategy:** Use role + model as instance name

```python
# Grouping logic
instance_key = (role, vendor, model)
instance_name = f"{role}_{model_short}"

# Example
NetBox devices:
  leaf01 (role=leaf, vendor=arista, model=dcs-7050sx-64)
  leaf02 (role=leaf, vendor=arista, model=dcs-7050sx-64)
  leaf03 (role=leaf, vendor=arista, model=dcs-7280sr-48c6)
  spine01 (role=spine, vendor=arista, model=dcs-7280sr-48c6)

Infragraph instances:
  Instance(name="leaf_7050", device="arista_dcs_7050sx_64", count=2)
  Instance(name="leaf_7280", device="arista_dcs_7280sr_48c6", count=1)
  Instance(name="spine_7280", device="arista_dcs_7280sr_48c6", count=1)
```

**Pros:**
- ✅ Ensures type consistency (each instance has exactly one device type)
- ✅ Stable even if device names change
- ✅ Groups logically by role + hardware
- ✅ Deterministic ordering (sort by device name within group)

**Cons:**
- Longer instance names
- Multiple instances for same role if hardware varies

**Verdict:** ✅ **Recommended** - satisfies all requirements

### Option C: Site + Role + Type Grouping

**Strategy:** Include site in instance name

```python
# Grouping logic
instance_key = (site, role, vendor, model)
instance_name = f"{site}_{role}_{model_short}"

# Example
NetBox devices:
  leaf01 (site=dc1, role=leaf, type=Arista-7050)
  leaf02 (site=dc1, role=leaf, type=Arista-7050)
  leaf03 (site=dc2, role=leaf, type=Arista-7050)

Infragraph instances:
  Instance(name="dc1_leaf_7050", count=2)
  Instance(name="dc2_leaf_7050", count=1)
```

**Pros:**
- ✅ Separates by location
- ✅ Type consistency maintained
- ✅ Useful for multi-site topologies

**Cons:**
- More instances (multiplied by number of sites)
- Longer names
- Less useful if exporting single site

**Verdict:** ⚠️ Optional - use if multi-site separation needed

### Option D: User-Defined Custom Field

**Strategy:** Let users define instance grouping via NetBox custom field

```python
# NetBox custom field: "infragraph_instance"
leaf01 → custom_field["infragraph_instance"] = "access_layer"
leaf02 → custom_field["infragraph_instance"] = "access_layer"
spine01 → custom_field["infragraph_instance"] = "core_layer"

# Still need to combine with device type
instance_key = (custom_field_value, vendor, model)
```

**Pros:**
- ✅ Maximum flexibility
- ✅ Users control logical grouping

**Cons:**
- ❌ Requires NetBox configuration
- ❌ Complex setup for users
- ❌ Falls back to role if custom field not set

**Verdict:** ⚠️ Future enhancement - not for initial implementation

## Recommended Implementation: Role + Type Grouping

### Phase A3 Enhancement: Instance Indexing

**Add to NBNetwork class:**

```python
class NBNetwork:
    def __init__(self):
        # ... existing fields ...
        self.device_types = {}  # (vendor, model) → device_type_info
        self.device_type_interfaces = {}  # (vendor, model) → [interface_list]
        self.device_name_to_type = {}  # device_name → (vendor, model)

        # NEW: Instance grouping and indexing
        self.instances = {}  # instance_key → instance_info
        self.device_to_instance = {}  # device_name → (instance_name, instance_idx)
```

**Build instance index during device processing:**

```python
def _build_instance_index(self):
    """Build stable instance indexing based on role + device_type"""
    instance_groups = {}  # (role, vendor, model) → [device_list]

    # Group devices by role and type
    for device in self.nb_net.devices:
        instance_key = (device['role'], device['vendor'], device['model'])
        if instance_key not in instance_groups:
            instance_groups[instance_key] = []
        instance_groups[instance_key].append(device)

    # Sort devices within each group for stable, deterministic indexing
    for instance_key, devices in instance_groups.items():
        # CRITICAL: Sort by device name for consistent ordering
        # This ensures leaf.0, leaf.1, etc. always map to same devices
        devices.sort(key=lambda d: d['name'])

        role, vendor, model = instance_key

        # Generate instance name: role_model
        # Sanitize model for infragraph naming rules
        model_short = self._create_model_shortname(model)
        instance_name = f"{role}_{model_short}"

        # Create instance info
        self.nb_net.instances[instance_key] = {
            'name': instance_name,
            'role': role,
            'device_type_key': (vendor, model),
            'count': len(devices),
            'devices': []  # Ordered list of device names
        }

        # Assign 0-based index to each device within this instance
        for idx, device in enumerate(devices):
            self.nb_net.instances[instance_key]['devices'].append(device['name'])
            self.nb_net.device_to_instance[device['name']] = (instance_name, idx)

            # Add to device dict for easy access
            device['instance_name'] = instance_name
            device['instance_index'] = idx

def _create_model_shortname(self, model):
    """Create short model name for instance naming

    Examples:
        dcs-7050sx-64 → 7050sx
        dcs-7280sr-48c6 → 7280sr
        catalyst-9300-48p → 9300
    """
    # Remove common prefixes
    model = model.replace('dcs-', '').replace('catalyst-', '')

    # Take first meaningful part
    parts = model.split('-')
    if len(parts) > 0:
        # Take first part that contains numbers
        for part in parts:
            if any(c.isdigit() for c in part):
                # Include one more part if it's letters (e.g., "sr", "sx")
                idx = parts.index(part)
                if idx + 1 < len(parts) and parts[idx + 1].isalpha():
                    return f"{part}{parts[idx + 1]}"
                return part

    # Fallback: sanitize full model name
    return model.replace('-', '_').replace(' ', '_')[:10]
```

**Call during initialization:**

```python
def __init__(self, config):
    # ... existing initialization ...

    try:
        self._get_nb_devices()
        self._get_nb_objects("interfaces", ...)
        self._get_nb_objects("cables", ...)

        # NEW: Build instance index after all devices loaded
        self._build_instance_index()
    except Exception as e:
        error("NetBox API failure", e)
```

### Device Node Enhancement

**Enhanced device dict:**

```python
d = {
    "id": device.id,  # NetBox DB ID (internal use only)
    "name": device.name,  # NetBox device name
    "type": "device",

    # NEW: Instance indexing for infragraph
    "instance_name": "leaf_7050",  # Infragraph instance name
    "instance_index": 0,  # 0-based index within instance
    "instance_key": ("leaf", "arista", "dcs-7050sx-64"),  # Grouping key

    # Existing fields
    "site": device.site.name,
    "vendor": "arista",
    "model": "dcs-7050sx-64",
    "role": "leaf",
    "role_name": "Leaf Switch",
    # ... etc
}
```

### Interface Mapper Update

**Map by device name, lookup instance via device_to_instance:**

```python
class InterfaceMapper:
    def __init__(self, nb_net):
        self.nb_net = nb_net
        # Still map by device_name.interface_name
        # Device name is portable, even though not used as instance name
        self.interface_to_component = {}

    def get_component_index(self, device_name, interface_name):
        """Get (component_name, component_idx) for an interface"""
        key = f"{device_name}.{interface_name}"
        return self.interface_to_component.get(key, ("port", 0))
```

### Infragraph Export Updates

**B5: Instance Creation:**

```python
def _build_instances(self, infra):
    """Create Instances using role+type grouping"""
    for instance_key, instance_info in self.nb_net.instances.items():
        device_type_key = instance_info['device_type_key']
        device_template = self.device_templates[device_type_key]

        instance = infra.instances.add(
            name=instance_info['name'],  # "leaf_7050", "spine_7280", etc.
            description=f"{instance_info['role']} - {instance_info['count']} devices",
            device=device_template.name,
            count=instance_info['count']
        )
```

**B7: Edge Creation:**

```python
def _build_edges(self, infra):
    """Convert cables using instance indexing"""
    for edge in self.G.edges(data=True):
        node_a = self.G.nodes[node_a_name]
        node_b = self.G.nodes[node_b_name]

        if node_a.get('type') != 'interface' or node_b.get('type') != 'interface':
            continue

        iface_a = node_a['interface']
        iface_b = node_b['interface']

        device_name_a = iface_a['device_name']
        device_name_b = iface_b['device_name']

        # Get instance name and index from mapping
        instance_name_a, instance_idx_a = self.nb_net.device_to_instance[device_name_a]
        instance_name_b, instance_idx_b = self.nb_net.device_to_instance[device_name_b]

        # Get component indices
        component_a, comp_idx_a = self.mapper.get_component_index(
            device_name_a, iface_a['name']
        )
        component_b, comp_idx_b = self.mapper.get_component_index(
            device_name_b, iface_b['name']
        )

        # Create edge
        infra_edge = infra.edges.add(
            scheme=InfrastructureEdge.ONE2ONE,
            link=self._get_link_name(iface_a.get('speed', 0))
        )

        # Set endpoints with instance indices
        infra_edge.ep1.instance = f"{instance_name_a}[{instance_idx_a}]"
        infra_edge.ep1.component = f"{component_a}[{comp_idx_a}]"
        infra_edge.ep2.instance = f"{instance_name_b}[{instance_idx_b}]"
        infra_edge.ep2.component = f"{component_b}[{comp_idx_b}]"
```

## Preserving NetBox Device Names

NetBox device names must be preserved for reverse mapping and user reference.

### Strategy: Infragraph Annotations

Use infragraph's annotation capability to store NetBox metadata:

```python
def _add_annotations(self, infrastructure):
    """Add NetBox device names and metadata as annotations"""

    # Create annotation mapping
    annotations = {}

    for device in self.nb_net.devices:
        instance_name = device['instance_name']
        instance_idx = device['instance_index']

        # Infragraph node identifier
        node_id = f"{instance_name}.{instance_idx}"

        # Store device metadata
        annotations[node_id] = {
            'device_name': device['name'],
            'site': device['site'],
            'role': device['role'],
            'platform': device['platform'],
            'source_id': device['id']  # Optional, for reference to source system
        }

    # TODO: Determine how to include annotations in infragraph export
    # Option 1: Use InfraGraphService annotation API if available
    # Option 2: Include in custom section of JSON output
    # Option 3: Generate separate annotation file

    return annotations
```

### Example Output Structure

```json
{
  "name": "my_datacenter",
  "devices": [
    {"name": "arista_dcs_7050sx_64", "components": [...], ...}
  ],
  "instances": [
    {"name": "leaf_7050", "device": "arista_dcs_7050sx_64", "count": 2},
    {"name": "spine_7280", "device": "arista_dcs_7280sr_48c6", "count": 1}
  ],
  "edges": [
    {
      "ep1": {"instance": "leaf_7050[0]", "component": "port[0]"},
      "ep2": {"instance": "spine_7280[0]", "component": "port[12]"},
      "link": "ethernet_10g"
    }
  ],
  "annotations": {
    "leaf_7050.0": {
      "device_name": "leaf01",
      "site": "datacenter1",
      "role": "leaf"
    },
    "leaf_7050.1": {
      "device_name": "leaf02",
      "site": "datacenter1",
      "role": "leaf"
    },
    "spine_7280.0": {
      "device_name": "spine01",
      "site": "datacenter1",
      "role": "spine"
    }
  }
}
```

## Reverse Direction: Infragraph → nrx

When importing infragraph as input format:

```python
def build_from_infragraph(self, infragraph_file):
    """Import topology from infragraph JSON"""

    # Load infragraph
    with open(infragraph_file) as f:
        infra_data = json.load(f)

    # Reconstruct devices
    for instance in infra_data['instances']:
        instance_name = instance['name']
        device_type = instance['device']
        count = instance['count']

        for idx in range(count):
            # Try to get NetBox name from annotations
            node_id = f"{instance_name}.{idx}"
            if 'annotations' in infra_data and node_id in infra_data['annotations']:
                device_name = infra_data['annotations'][node_id]['device_name']
            else:
                # Generate name if no annotation
                device_name = f"{instance_name}_{idx}"

            # Create device in nrx graph
            # ... reconstruct device from device_type template
```

## Example Scenarios

### Scenario 1: Uniform Leaf/Spine Topology

**NetBox:**
```
leaf01 - Arista DCS-7050SX-64 - Role: leaf
leaf02 - Arista DCS-7050SX-64 - Role: leaf
leaf03 - Arista DCS-7050SX-64 - Role: leaf
spine01 - Arista DCS-7280SR-48C6 - Role: spine
spine02 - Arista DCS-7280SR-48C6 - Role: spine
```

**Infragraph:**
```json
{
  "instances": [
    {"name": "leaf_7050sx", "device": "arista_dcs_7050sx_64", "count": 3},
    {"name": "spine_7280sr", "device": "arista_dcs_7280sr_48c6", "count": 2}
  ],
  "annotations": {
    "leaf_7050sx.0": {"device_name": "leaf01"},
    "leaf_7050sx.1": {"device_name": "leaf02"},
    "leaf_7050sx.2": {"device_name": "leaf03"},
    "spine_7280sr.0": {"device_name": "spine01"},
    "spine_7280sr.1": {"device_name": "spine02"}
  }
}
```

### Scenario 2: Mixed Hardware in Same Role

**NetBox:**
```
leaf01 - Arista DCS-7050SX-64 - Role: leaf
leaf02 - Arista DCS-7050SX-64 - Role: leaf
leaf03 - Arista DCS-7280SR-48C6 - Role: leaf  ← Different hardware!
spine01 - Arista DCS-7280SR-48C6 - Role: spine
```

**Infragraph:**
```json
{
  "instances": [
    {"name": "leaf_7050sx", "device": "arista_dcs_7050sx_64", "count": 2},
    {"name": "leaf_7280sr", "device": "arista_dcs_7280sr_48c6", "count": 1},
    {"name": "spine_7280sr", "device": "arista_dcs_7280sr_48c6", "count": 1}
  ]
}
```

**Note:** Same role ("leaf") but different hardware creates separate instances.

### Scenario 3: Device Name Change in NetBox

**Before:**
```
NetBox: leaf01 → infragraph: leaf_7050sx.0 (annotation: "leaf01")
```

**After renaming in NetBox:**
```
NetBox: access-switch-01 → infragraph: leaf_7050sx.0 (annotation: "access-switch-01")
```

**Index remains stable** because sorting is by original device name at time of export.

**Question:** Should we preserve original sort order or re-sort on each export?

## User-Configurable Instance Grouping

### The Scoping Problem

Infragraph's compression via `count` only makes sense within a logical scope:

**Example - Multi-site topology:**
```
Site DC1:
  leaf01, leaf02, leaf03, leaf04 (role=leaf, same hardware)
Site DC2:
  leaf01, leaf02, leaf03, leaf04 (role=leaf, same hardware)

BAD grouping (no scope):
  Instance: leaf_7050, count=8  ❌
  Result: leaf_7050.0 through leaf_7050.7 (which is which site?)

GOOD grouping (site scope):
  Instance: dc1_leaf_7050, count=4  ✓
  Instance: dc2_leaf_7050, count=4  ✓
  Result: Clear separation by site
```

**Example - Pod-based topology:**
```
Pod1:
  leaf01, leaf02 (role=leaf)
  spine01 (role=spine)
Pod2:
  leaf03, leaf04 (role=leaf)
  spine02 (role=spine)

GOOD grouping (pod scope):
  Instance: pod1_leaf_7050, count=2
  Instance: pod1_spine_7280, count=1
  Instance: pod2_leaf_7050, count=2
  Instance: pod2_spine_7280, count=1
```

### Proposed Solution: Configuration-Based Grouping

**Add configuration parameter for instance grouping strategy:**

```toml
# nrx.conf
[INFRAGRAPH]
# Define how to group devices into instances
# Available fields: site, location, rack, role, tenant, custom_field_name
INSTANCE_GROUPING = "site,role"

# Or for pod-based architectures (using custom field):
# INSTANCE_GROUPING = "pod,role"

# Or rack-level granularity:
# INSTANCE_GROUPING = "site,rack,role"

# Or minimal (just role+type):
# INSTANCE_GROUPING = "role"
```

**Command-line override:**

```bash
nrx --output infragraph --sites DC1 \
    --infragraph-grouping site,role

# Or use environment variable
export NRX_INFRAGRAPH_GROUPING="pod,role"
```

### Implementation: Dynamic Instance Key Generation

```python
class NBFactory:
    def _build_instance_index(self):
        """Build instance indexing based on configured grouping"""

        # Get grouping fields from config (comma-separated)
        grouping_fields = self.config.get('infragraph_grouping', 'role').split(',')
        grouping_fields = [f.strip() for f in grouping_fields]

        # Always include device type (required for consistency)
        # Format: [user_fields..., vendor, model]

        instance_groups = {}  # instance_key → [device_list]

        for device in self.nb_net.devices:
            # Build instance key from configured fields
            key_parts = []

            for field in grouping_fields:
                value = self._get_device_field(device, field)
                if value:
                    key_parts.append(value)

            # Always append device type for template consistency
            key_parts.extend([device['vendor'], device['model']])

            instance_key = tuple(key_parts)

            if instance_key not in instance_groups:
                instance_groups[instance_key] = []
            instance_groups[instance_key].append(device)

        # Build instance metadata
        for instance_key, devices in instance_groups.items():
            # CRITICAL: Sort by NetBox device ID for stable, chronological ordering
            # This preserves indices across device renames and has high portability
            devices.sort(key=lambda d: d['id'])

            # Generate instance name from key parts
            instance_name = self._generate_instance_name(instance_key, grouping_fields)

            device_type_key = instance_key[-2:]  # Last two: (vendor, model)

            self.nb_net.instances[instance_key] = {
                'name': instance_name,
                'grouping_fields': grouping_fields,
                'device_type_key': device_type_key,
                'count': len(devices),
                'devices': [d['name'] for d in devices]
            }

            # Map devices to instances
            for idx, device in enumerate(devices):
                self.nb_net.device_to_instance[device['name']] = (instance_name, idx)
                device['instance_name'] = instance_name
                device['instance_index'] = idx
                device['instance_key'] = instance_key

    def _get_device_field(self, device, field_name):
        """Get device field value by name, supporting custom fields"""

        # Standard NetBox fields
        standard_fields = {
            'site': lambda d: d.get('site', ''),
            'role': lambda d: d.get('role', ''),
            'tenant': lambda d: d.get('tenant', ''),
            'location': lambda d: d.get('location', ''),
            'rack': lambda d: d.get('rack', ''),
        }

        if field_name in standard_fields:
            return standard_fields[field_name](device)

        # Custom fields (if stored in device dict)
        if 'custom_fields' in device and field_name in device['custom_fields']:
            return device['custom_fields'][field_name]

        return None

    def _generate_instance_name(self, instance_key, grouping_fields):
        """Generate instance name from key components

        Args:
            instance_key: Tuple of (field_values..., vendor, model)
            grouping_fields: List of field names used

        Returns:
            Sanitized instance name like "dc1_pod1_leaf_7050"
        """
        # Take all parts except vendor/model (last 2)
        name_parts = list(instance_key[:-2])

        # Add short model name
        model = instance_key[-1]
        model_short = self._create_model_shortname(model)
        name_parts.append(model_short)

        # Join and sanitize
        instance_name = '_'.join(str(p) for p in name_parts if p)
        instance_name = self._sanitize_name(instance_name)

        return instance_name
```

### Example Configurations

**1. Single site - role only:**
```toml
INSTANCE_GROUPING = "role"
```
Result: `leaf_7050`, `spine_7280`

**2. Multi-site - site + role:**
```toml
INSTANCE_GROUPING = "site,role"
```
Result: `dc1_leaf_7050`, `dc1_spine_7280`, `dc2_leaf_7050`, `dc2_spine_7280`

**3. Pod architecture - custom field + role:**
```toml
INSTANCE_GROUPING = "pod,role"
```
NetBox devices have custom field `pod` = `pod1`, `pod2`, etc.
Result: `pod1_leaf_7050`, `pod1_spine_7280`, `pod2_leaf_7050`

**4. Rack-level granularity:**
```toml
INSTANCE_GROUPING = "site,rack,role"
```
Result: `dc1_rack01_leaf_7050`, `dc1_rack01_spine_7280`, `dc1_rack02_leaf_7050`

**5. Tenant-based (MSP use case):**
```toml
INSTANCE_GROUPING = "tenant,role"
```
Result: `customer_a_leaf_7050`, `customer_b_leaf_7050`

### Default Configuration

**Recommended default:**
```toml
# Default to site,role for multi-site compatibility
INSTANCE_GROUPING = "site,role"
```

**Special handling for single-site exports:**
```python
def _build_instance_index(self):
    # Check if all devices are in same site
    sites = set(d.get('site', '') for d in self.nb_net.devices)

    if len(sites) == 1 and 'site' in self.config['infragraph_grouping'].split(','):
        # Single site - omit site from instance name
        # "dc1_leaf_7050" → "leaf_7050"
        # But still group by site to avoid cross-site mixing if topology expands
        pass
```

### Future: Hierarchical Grouping (Pods)

When infragraph adds support for reusable blocks/pods:

```python
# Future enhancement: Export pods as separate structures
INSTANCE_GROUPING = "pod,role"
INFRAGRAPH_USE_PODS = true

# Would generate:
{
  "pods": [
    {
      "name": "pod1",
      "instances": [
        {"name": "leaf_7050", "count": 2},
        {"name": "spine_7280", "count": 1}
      ]
    }
  ]
}
```

### Configuration Validation

```python
def validate_infragraph_config(config):
    """Validate infragraph configuration"""

    grouping = config.get('infragraph_grouping', 'role')
    fields = [f.strip() for f in grouping.split(',')]

    supported_fields = ['site', 'location', 'rack', 'role', 'tenant']

    for field in fields:
        if field not in supported_fields and not field.startswith('custom_'):
            warning(f"Infragraph grouping field '{field}' may not be supported. "
                   f"Supported fields: {', '.join(supported_fields)}, custom_*")

    # Warn if 'role' not included
    if 'role' not in fields:
        warning("Infragraph grouping does not include 'role'. "
               "This may result in unexpected instance grouping.")

    return fields
```

### Documentation for Users

**In README.md:**

```markdown
### Infragraph Instance Grouping

When exporting to infragraph format, devices are grouped into instances based on:
1. **User-configured grouping fields** (site, rack, role, etc.)
2. **Device type** (vendor + model) - always included automatically

Configure in `nrx.conf`:

    [INFRAGRAPH]
    # Group by site and role (recommended for multi-site)
    INSTANCE_GROUPING = "site,role"

    # Group by role only (single site)
    INSTANCE_GROUPING = "role"

    # Group by custom pod field and role
    INSTANCE_GROUPING = "pod,role"
```

Or via command line:
```bash
nrx --output infragraph --infragraph-grouping "site,role"
```

**Example:**
- NetBox devices: `dc1-leaf01`, `dc1-leaf02`, `dc2-leaf01`
- Grouping: `site,role`
- Infragraph instances: `dc1_leaf`, `dc2_leaf`
- Result: `dc1_leaf.0`, `dc1_leaf.1`, `dc2_leaf.0`

## Open Questions

### Q1: Sorting Stability ✅ DECIDED

**Decision:** Sort devices by NetBox device ID

**Rationale:**

NetBox device IDs provide the best balance of stability and portability:

1. **Stable across renames:**
   ```
   leaf01 (ID=42) → leaf_7050.0
   Rename to: access-sw-01 (ID=42) → leaf_7050.0 ✓ Same index
   ```

2. **Preserves deployment/creation order:**
   ```
   Day 1: leaf01 created → ID=100
   Day 2: leaf02 created → ID=101
   Sorted by ID = chronological deployment
   ```

3. **Consistent across multiple exports:**
   ```
   Export 1: ID sort → [42, 43, 44] → indices [0, 1, 2]
   Export 2: ID sort → [42, 43, 44] → indices [0, 1, 2] ✓
   ```

4. **High portability probability:**
   - Most NetBox imports preserve chronological order
   - Bulk imports typically maintain relative ID ordering
   - Even if absolute IDs differ, sort order usually matches

   ```python
   # Instance A
   leaf01 → ID 42, leaf02 → ID 43, leaf03 → ID 44
   Sorted: [42, 43, 44] → indices [0, 1, 2]

   # Instance B (imported from A)
   leaf01 → ID 108, leaf02 → ID 109, leaf03 → ID 110
   Sorted: [108, 109, 110] → indices [0, 1, 2] ✓ Same order!
   ```

5. **Annotations provide safety net:**
   - If indices do change between instances, annotations preserve mapping
   - `annotations.device_name` allows reconstruction

**Trade-off accepted:**
- ❌ Not alphabetically ordered (less predictable for humans)
- ❌ Could break if selective/out-of-order import to new instance
- ✅ But: annotations preserve device name mapping regardless

**Implementation:**
```python
# Sort by NetBox device ID
devices.sort(key=lambda d: d['id'])
```

### Q2: Instance Name Collisions ✅ DECIDED

**Decision:** Use smart compaction routine to find shortest conflict-free names

**Problem:** Different combinations could generate same short name

```
leaf_7050 (role=leaf, vendor=arista, model=dcs-7050sx-64)
leaf_7050 (role=leaf, vendor=cisco, model=catalyst-7050) ❌ Collision!
```

**Solution:** Progressive name expansion until conflicts resolved

**Algorithm:**

```python
def _compact_instance_names(self, instance_groups):
    """
    Generate shortest possible instance names that avoid collisions

    Strategy:
    1. Start with minimal name (grouping_fields + short_model)
    2. If collision detected, progressively expand:
       - Add vendor if not already included
       - Add more model detail (7050 → 7050sx → 7050sx64)
       - Add full model as last resort
    3. Return conflict-free mapping
    """

    name_attempts = {}  # instance_key → attempted_name
    name_usage = {}     # name → [instance_keys using this name]

    # Phase 1: Generate initial names (shortest form)
    for instance_key in instance_groups.keys():
        name = self._generate_minimal_name(instance_key)
        name_attempts[instance_key] = name

        if name not in name_usage:
            name_usage[name] = []
        name_usage[name].append(instance_key)

    # Phase 2: Resolve conflicts
    conflicts = {name: keys for name, keys in name_usage.items() if len(keys) > 1}

    for conflicting_name, conflicting_keys in conflicts.items():
        # Try progressive expansion for each conflicting key
        for instance_key in conflicting_keys:
            resolved_name = self._expand_name_to_resolve_conflict(
                instance_key,
                conflicting_keys,
                name_usage
            )
            name_attempts[instance_key] = resolved_name

            # Update usage tracking
            name_usage[conflicting_name].remove(instance_key)
            if resolved_name not in name_usage:
                name_usage[resolved_name] = []
            name_usage[resolved_name].append(instance_key)

    return name_attempts

def _generate_minimal_name(self, instance_key):
    """Generate shortest possible name from instance key

    Args:
        instance_key: (grouping_values..., vendor, model)

    Returns:
        Minimal name like "dc1_leaf_7050"
    """
    # Grouping fields (site, role, etc.)
    name_parts = list(instance_key[:-2])

    # Add shortest model identifier
    vendor, model = instance_key[-2:]
    model_short = self._extract_model_core(model)
    name_parts.append(model_short)

    return '_'.join(str(p) for p in name_parts if p)

def _extract_model_core(self, model):
    """Extract core model identifier (shortest meaningful part)

    Examples:
        dcs-7050sx-64 → 7050
        catalyst-9300-48p → 9300
        dcs-7280sr-48c6 → 7280
    """
    # Remove common prefixes
    model = model.lower()
    for prefix in ['dcs-', 'catalyst-', 'nexus-', 'ws-c']:
        if model.startswith(prefix):
            model = model[len(prefix):]

    # Extract first numeric part
    parts = model.split('-')
    for part in parts:
        if any(c.isdigit() for c in part):
            # Return just the numeric core
            return ''.join(c for c in part if c.isdigit() or c.isalpha())[:4]

    # Fallback: first part
    return parts[0][:8] if parts else model[:8]

def _expand_name_to_resolve_conflict(self, instance_key, conflicting_keys, name_usage):
    """Progressively expand name until conflict resolved

    Expansion levels:
    1. Add vendor (if not in grouping fields)
    2. Add extended model (7050 → 7050sx)
    3. Add full model detail (7050sx → 7050sx64)
    4. Add vendor + full model (last resort)

    Args:
        instance_key: The key we're finding a name for
        conflicting_keys: Other keys with the same current name
        name_usage: Current name → keys mapping

    Returns:
        Unique name for this instance_key
    """
    grouping_parts = instance_key[:-2]
    vendor, model = instance_key[-2:]

    # Level 1: Try adding vendor
    if not self._vendor_in_grouping(grouping_parts, vendor):
        candidate = self._build_name(grouping_parts, vendor,
                                     self._extract_model_core(model))
        if self._is_unique(candidate, instance_key, name_usage):
            return candidate

    # Level 2: Try extended model
    model_extended = self._extract_model_extended(model)
    candidate = self._build_name(grouping_parts, None, model_extended)
    if self._is_unique(candidate, instance_key, name_usage):
        return candidate

    # Level 3: Try vendor + extended model
    candidate = self._build_name(grouping_parts, vendor, model_extended)
    if self._is_unique(candidate, instance_key, name_usage):
        return candidate

    # Level 4: Full model detail
    model_full = self._extract_model_full(model)
    candidate = self._build_name(grouping_parts, None, model_full)
    if self._is_unique(candidate, instance_key, name_usage):
        return candidate

    # Level 5: Vendor + full model (guaranteed unique for same vendor+model)
    return self._build_name(grouping_parts, vendor, model_full)

def _extract_model_extended(self, model):
    """Extract extended model identifier

    Examples:
        dcs-7050sx-64 → 7050sx
        catalyst-9300-48p → 9300
    """
    model = model.lower()
    for prefix in ['dcs-', 'catalyst-', 'nexus-', 'ws-c']:
        if model.startswith(prefix):
            model = model[len(prefix):]

    parts = model.split('-')
    if len(parts) >= 2:
        # First part + first letter of second part if alphabetic
        first = parts[0]
        second = parts[1]
        if second and second[0].isalpha():
            return first + second[:2]
        return first
    return parts[0][:8] if parts else model[:8]

def _extract_model_full(self, model):
    """Extract full detailed model identifier

    Examples:
        dcs-7050sx-64 → 7050sx64
        catalyst-9300-48p → 9300_48p
    """
    model = model.lower()
    for prefix in ['dcs-', 'catalyst-', 'nexus-', 'ws-c']:
        if model.startswith(prefix):
            model = model[len(prefix):]

    # Replace hyphens with underscores, keep full detail
    return model.replace('-', '_')[:16]

def _build_name(self, grouping_parts, vendor, model_part):
    """Build instance name from components"""
    parts = list(grouping_parts)
    if vendor:
        parts.append(vendor)
    parts.append(model_part)
    return '_'.join(str(p) for p in parts if p)

def _is_unique(self, candidate_name, instance_key, name_usage):
    """Check if candidate name is unique or only used by this instance_key"""
    if candidate_name not in name_usage:
        return True
    existing_keys = name_usage[candidate_name]
    return len(existing_keys) == 0 or (len(existing_keys) == 1 and existing_keys[0] == instance_key)

def _vendor_in_grouping(self, grouping_parts, vendor):
    """Check if vendor already appears in grouping parts"""
    return vendor in grouping_parts
```

**Example: Collision Resolution**

**Scenario 1: Different vendors, same model number**
```python
Instance keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc1', 'leaf', 'cisco', 'catalyst-7050')

Minimal names (collision):
  dc1_leaf_7050  ❌ Collision!
  dc1_leaf_7050  ❌ Collision!

After expansion (add vendor):
  dc1_leaf_arista_7050  ✓ Unique
  dc1_leaf_cisco_7050   ✓ Unique
```

**Scenario 2: Same vendor, similar models**
```python
Instance keys:
  ('leaf', 'arista', 'dcs-7050sx-64')
  ('leaf', 'arista', 'dcs-7050tx-48')

Minimal names (collision):
  leaf_7050  ❌ Collision!
  leaf_7050  ❌ Collision!

After expansion (extended model):
  leaf_7050sx  ✓ Unique
  leaf_7050tx  ✓ Unique
```

**Scenario 3: Complex case**
```python
Instance keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-128')
  ('dc1', 'leaf', 'cisco', 'catalyst-7050')

Minimal names:
  dc1_leaf_7050  ❌ Collision (3-way)!

After expansion:
  dc1_leaf_arista_7050sx  → Still collision with 7050sx-128
  dc1_leaf_arista_7050sx64  ✓ Unique (full model detail)
  dc1_leaf_arista_7050sx128 ✓ Unique (full model detail)
  dc1_leaf_cisco_7050       ✓ Unique (vendor different)
```

**Benefits:**
- ✅ Shortest possible names (no unnecessary verbosity)
- ✅ Automatic conflict resolution
- ✅ Deterministic (same inputs → same outputs)
- ✅ Handles all collision scenarios
- ✅ No manual intervention required

**Updated Implementation:**

```python
def _build_instance_index(self):
    """Build instance indexing with smart name compaction"""

    # ... existing grouping logic ...

    # Generate optimal instance names (shortest conflict-free)
    optimal_names = self._compact_instance_names(instance_groups)

    for instance_key, devices in instance_groups.items():
        devices.sort(key=lambda d: d['id'])

        # Use optimal compacted name
        instance_name = optimal_names[instance_key]

        # ... rest of instance building ...
```

### Q3: Annotation Format ✅ DECIDED

**Decision:** Use infragraph's `annotate_graph` API after export

**How infragraph annotations work:**

Infragraph provides an `annotate_graph` API specifically designed to "separate the infrastructure model from specific use-case models." Annotations extend the graph with custom data without modifying the core infrastructure.

**API Pattern:**
```python
from infragraph import AnnotateRequest

# After creating infrastructure and calling set_graph()
annotate_request = AnnotateRequest()

# Add annotation for each node
annotate_request.nodes.add(
    name="leaf_7050.0",      # Node ID
    attribute="device_name",  # Attribute key
    value="leaf01"           # Attribute value (string)
)

# Apply annotations
service.annotate_graph(annotate_request)
```

**Implementation in nrx:**

```python
def export_graph_infragraph(self):
    """Export network topology in infragraph format with annotations"""

    # Phase 1: Create and export base infrastructure
    exporter = InfragraphExporter(self.G, self.nb_net, self.topology_name, self.config)
    infrastructure = exporter.build_infrastructure()
    json_output = infrastructure.serialize(encoding=Infrastructure.JSON)

    # Write base infragraph file
    dir_path = create_output_directory(self.topology_name, self.config['output_dir'])
    export_file = f"{self.topology_name}.infragraph.json"
    export_path = f"{dir_path}/{export_file}"

    with open(export_path, 'w', encoding='utf-8') as f:
        f.write(json_output)
    print(f"Infragraph JSON saved to: {export_path}")

    # Phase 2: Add NetBox annotations via InfraGraphService
    if self.config.get('infragraph_add_annotations', True):
        try:
            from infragraph import InfraGraphService, AnnotateRequest

            # Load the infrastructure into service
            service = InfraGraphService()
            service.set_graph(json_output)

            # Build annotation request
            annotate_request = AnnotateRequest()

            for device in self.nb_net.devices:
                instance_name = device['instance_name']
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

            # Apply annotations
            service.annotate_graph(annotate_request)

            # Export annotated graph
            annotated_output = service.get_graph()
            annotated_file = f"{self.topology_name}.infragraph.annotated.json"
            annotated_path = f"{dir_path}/{annotated_file}"

            with open(annotated_path, 'w', encoding='utf-8') as f:
                f.write(annotated_output)
            print(f"Annotated infragraph saved to: {annotated_path}")

        except ImportError:
            print("⚠ infragraph package not available, skipping annotations")
        except Exception as e:
            print(f"⚠ Annotation failed: {e}")
```

**Benefits of using infragraph API:**
- ✅ Standard infragraph pattern (not custom format)
- ✅ Annotations queryable via `query_graph` API
- ✅ Separates infrastructure from metadata (clean design)
- ✅ Two-file output:
  - `topology.infragraph.json` - Clean infrastructure
  - `topology.infragraph.annotated.json` - With NetBox metadata

**Querying annotations:**
```python
# Later, can query by NetBox device name
filter = QueryNodeFilter()
filter.choice = QueryNodeFilter.ATTRIBUTE_FILTER
filter.attribute_filter.name = "device_name"
filter.attribute_filter.operator = QueryNodeId.EQ
filter.attribute_filter.value = "leaf01"

matches = service.query_graph(filter)
# Returns: leaf_7050.0 (or whichever node has that annotation)
```

**Configuration option:**
```toml
[INFRAGRAPH]
# Add NetBox annotations to exported graph (default: true)
ADD_ANNOTATIONS = true

# Annotations to include (comma-separated)
ANNOTATION_FIELDS = "device_name,site,role,platform"
```

### Q4: Multi-site Handling ✅ DECIDED

**Decision:** Always start with maximal grouping (site included), then use compaction routine to automatically remove unnecessary parts

**Key Insight:** The compaction routine works in reverse - start with the longest, most detailed name, then progressively remove parts that don't add distinction. No user configuration needed!

**Algorithm:**

```python
def _build_instance_index_with_auto_grouping(self):
    """
    Build instance indexing with automatic site detection

    Strategy:
    1. Always group by (site, role, vendor, model) initially
    2. Compaction routine removes 'site' if it doesn't add distinction
    3. User gets shortest possible names automatically
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

    # Compaction routine automatically optimizes names
    optimal_names = self._compact_instance_names(instance_groups)

    # Assign instance names and indices
    for instance_key, devices in instance_groups.items():
        devices.sort(key=lambda d: d['id'])
        instance_name = optimal_names[instance_key]

        for idx, device in enumerate(devices):
            device['instance_name'] = instance_name
            device['instance_index'] = idx
```

**Compaction Logic (Updated):**

```python
def _compact_instance_names(self, instance_groups):
    """
    Generate shortest possible instance names by removing unnecessary parts

    Strategy:
    1. Start with full name: site_role_vendor_model
    2. Try removing site (if doesn't create conflict)
    3. Try removing vendor (if doesn't create conflict)
    4. Try compacting model (7050sx64 → 7050sx → 7050)
    5. Return shortest conflict-free names
    """

    final_names = {}

    # Try progressively shorter names for each instance_key
    for instance_key in instance_groups.keys():
        site, role, vendor, model = instance_key

        # Level 1: Try without site
        candidate = self._build_name_without_site(role, vendor, model)
        if self._is_unique_across_groups(candidate, instance_key, instance_groups):
            final_names[instance_key] = candidate
            continue

        # Level 2: Try without vendor (but with site)
        candidate = self._build_name_without_vendor(site, role, model)
        if self._is_unique_across_groups(candidate, instance_key, instance_groups):
            final_names[instance_key] = candidate
            continue

        # Level 3: Try compact model without site
        model_compact = self._extract_model_core(model)
        candidate = f"{role}_{model_compact}"
        if self._is_unique_across_groups(candidate, instance_key, instance_groups):
            final_names[instance_key] = candidate
            continue

        # Level 4: Try compact model with site (no vendor)
        candidate = f"{site}_{role}_{model_compact}"
        if self._is_unique_across_groups(candidate, instance_key, instance_groups):
            final_names[instance_key] = candidate
            continue

        # Level 5: Full detail (guaranteed unique)
        final_names[instance_key] = f"{site}_{role}_{vendor}_{model_compact}"

    return final_names

def _is_unique_across_groups(self, candidate_name, instance_key, instance_groups):
    """Check if candidate name would be unique across all instance groups"""

    # Count how many instance_keys would map to this candidate
    matches = 0
    for other_key in instance_groups.keys():
        # Try generating the same candidate for other_key
        if self._would_generate_same_name(candidate_name, other_key):
            matches += 1

    # Unique if only this instance_key generates this name
    return matches == 1
```

**Example Scenarios:**

**Scenario 1: Single-site export**
```python
# NetBox data (single site)
Site: dc1
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)
  - leaf02 (role=leaf, type=arista/dcs-7050sx-64)
  - spine01 (role=spine, type=arista/dcs-7280sr-48c6)

# Initial grouping (maximal):
instance_keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc1', 'spine', 'arista', 'dcs-7280sr-48c6')

# Compaction routine:
Try without site:
  leaf_7050  ✓ Unique! (no other site has leaf/arista/7050)
  spine_7280 ✓ Unique! (no other site has spine/arista/7280)

# Final result (site removed automatically):
leaf_7050: count=2
spine_7280: count=1
```

**Scenario 2: Multi-site with same devices**
```python
# NetBox data (two sites, same devices)
Site: dc1
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)
  - leaf02 (role=leaf, type=arista/dcs-7050sx-64)

Site: dc2
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)
  - leaf02 (role=leaf, type=arista/dcs-7050sx-64)

# Initial grouping (maximal):
instance_keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc2', 'leaf', 'arista', 'dcs-7050sx-64')

# Compaction routine:
Try without site:
  leaf_7050  ❌ Collision! (both dc1 and dc2 would map to this)

Try with site:
  dc1_leaf_7050  ✓ Unique!
  dc2_leaf_7050  ✓ Unique!

# Final result (site kept automatically):
dc1_leaf_7050: count=2
dc2_leaf_7050: count=2
```

**Scenario 3: Multi-site with different devices**
```python
# NetBox data (two sites, different devices)
Site: dc1
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)
  - leaf02 (role=leaf, type=arista/dcs-7050sx-64)

Site: dc2
  - leaf01 (role=leaf, type=cisco/nexus-9300)
  - leaf02 (role=leaf, type=cisco/nexus-9300)

# Initial grouping (maximal):
instance_keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc2', 'leaf', 'cisco', 'nexus-9300')

# Compaction routine:
Try without site:
  leaf_7050  ✓ Unique! (only dc1 has arista/7050)
  leaf_9300  ✓ Unique! (only dc2 has cisco/9300)

# Final result (site removed, vendor removed automatically):
leaf_7050: count=2
leaf_9300: count=2
```

**Scenario 4: Multi-site with partial overlap**
```python
# NetBox data (three sites, mixed)
Site: dc1
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)
  - spine01 (role=spine, type=arista/dcs-7280sr-48c6)

Site: dc2
  - leaf01 (role=leaf, type=arista/dcs-7050sx-64)  # Same as dc1!
  - spine01 (role=spine, type=cisco/nexus-9500)

Site: dc3
  - leaf01 (role=leaf, type=cisco/nexus-9300)
  - spine01 (role=spine, type=cisco/nexus-9500)

# Initial grouping (maximal):
instance_keys:
  ('dc1', 'leaf', 'arista', 'dcs-7050sx-64')
  ('dc1', 'spine', 'arista', 'dcs-7280sr-48c6')
  ('dc2', 'leaf', 'arista', 'dcs-7050sx-64')  # Collision with dc1!
  ('dc2', 'spine', 'cisco', 'nexus-9500')
  ('dc3', 'leaf', 'cisco', 'nexus-9300')
  ('dc3', 'spine', 'cisco', 'nexus-9500')  # Collision with dc2!

# Compaction routine:
leaf_7050  ❌ Collision (dc1 and dc2)
  → dc1_leaf_7050  ✓ Unique
  → dc2_leaf_7050  ✓ Unique

spine_7280  ✓ Unique (only dc1)
  → spine_7280  ✓ Keep short

spine_9500  ❌ Collision (dc2 and dc3)
  → dc2_spine_9500  ✓ Unique
  → dc3_spine_9500  ✓ Unique

leaf_9300  ✓ Unique (only dc3)
  → leaf_9300  ✓ Keep short

# Final result (mix of site-prefixed and non-prefixed):
dc1_leaf_7050: count=1   # Site needed (collision)
spine_7280: count=1      # Site not needed (unique)
dc2_leaf_7050: count=1   # Site needed (collision)
dc2_spine_9500: count=1  # Site needed (collision)
leaf_9300: count=1       # Site not needed (unique)
dc3_spine_9500: count=1  # Site needed (collision)
```

**Key Benefits:**

- ✅ **No user configuration required** - algorithm automatically optimizes
- ✅ **Always shortest possible names** - removes unnecessary parts
- ✅ **Handles all scenarios** - single-site, multi-site, partial overlap
- ✅ **Deterministic** - same input always produces same output
- ✅ **No false grouping** - devices from different sites never accidentally combined
- ✅ **Optimal readability** - site only included when needed for distinction

**Trade-offs:**

- ✅ Fully automatic (no decisions needed)
- ✅ Always produces shortest conflict-free names
- ✅ Handles complex multi-site scenarios transparently
- ⚠️ Users cannot force global grouping (devices always separated by site first)
  - If truly global view desired across sites, would need post-processing step

## Next Steps

1. **Validate approach** - Confirm instance grouping strategy
2. **Answer open questions** - Sorting, collisions, annotations
3. **Update implementation plan** - Integrate instance indexing
4. **Test with real data** - Verify stability and reversibility
5. **Document mapping** - Clear examples for users

## Summary

**Recommended Strategy: Role + Device Type Grouping**

- ✅ Ensures each instance has exactly one device template
- ✅ Stable indexing based on sorted device names
- ✅ NetBox device names preserved in annotations
- ✅ Reversible for future infragraph input support
- ⚠️ Need to resolve: sorting stability, name collisions, annotation format
