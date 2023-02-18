#!/usr/bin/env python3

# Copyright 2023 Netreplica Team
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Create Containerlab topology from CYJS graph

# Initialize parameters   
topology_name = "DM-Akron"

# Read CYJS graph data into a dictonary and initialize networkx graph from it
import json
import networkx as nx

print(f"Reading CYJS topology graph:\t{topology_name}.cyjs")
cyjs = {}
with open(topology_name + ".cyjs", 'r', encoding='utf-8') as f:
    cyjs = json.load(f)
G = nx.cytoscape_graph(cyjs)

# Parse graph G into lists of: nodes and links. Keep a list of interfaces per device in `device_interfaces_map`.
nodes, links = [], []
device_interfaces_map = {}
for n in G.nodes:
    if G.nodes[n]['type'] == 'device':
        dev = G.nodes[n]['device']
        nodes.append(dev)
        device_interfaces_map[dev['name']] = {}
    elif G.nodes[n]['type'] == 'interface':
        int_name = G.nodes[n]['interface']['name']
        dev_name, dev_node_id = None, None
        peer_name, peer_dev_name, peer_dev_node_id = None, None, None
        for a_adj in G.adj[n].items():
            if G.nodes[a_adj[0]]['type'] == 'device':
                dev_name = G.nodes[a_adj[0]]['device']['name']
                dev_node_id = G.nodes[a_adj[0]]['device']['node_id']
                device_interfaces_map[dev_name][int_name] = ""
            elif G.nodes[a_adj[0]]['type'] == 'interface' and G.nodes[n]['side'] == 'a':
                peer_name = G.nodes[a_adj[0]]['interface']['name']
                for b_adj in G.adj[a_adj[0]].items():
                    if G.nodes[b_adj[0]]['type'] == 'device':
                        peer_dev_name = G.nodes[b_adj[0]]['device']['name']
                        peer_dev_node_id = G.nodes[b_adj[0]]['device']['node_id']
        if G.nodes[n]['side'] == 'a':
            links.append({
                'a': {
                    'node': dev_name,
                    'node_id': dev_node_id,
                    'interface': int_name,
                },
                'b': {
                    'node': peer_dev_name,
                    'node_id': peer_dev_node_id,
                    'interface': peer_name,
                },
            })

# Create container-compatible interface names for each device. We assume interface with index `0` is reserved for management, and start with `1`
for node, map in device_interfaces_map.items():
    # sort keys (interface names) in the map
    map_keys = list(map.keys())
    map_keys.sort()
    sorted_map = {k: f"eth{map_keys.index(k)+1}" for k in map_keys}
    device_interfaces_map[node] = sorted_map

for l in links:
    l['a']['c_interface'] = device_interfaces_map[l['a']['node']][l['a']['interface']]
    l['b']['c_interface'] = device_interfaces_map[l['b']['node']][l['b']['interface']]

# Generate clab topology. Using this gist as inspiration https://gist.github.com/renatoalmeidaoliveira/fdb772a5a02f3cfc0b5fbe7e8b7586a2
topology = {
    'name': G.name,
    'nodes': [f"{n['name']}" for n in nodes],
    'links': [f"[\"{l['a']['node']}:{l['a']['c_interface']}\", \"{l['b']['node']}:{l['b']['c_interface']}\"]" for l in links],
}

# Load Jinja2 template for Containerlab to run the topology through
from jinja2 import Environment, FileSystemLoader
env = Environment(
            loader=FileSystemLoader(f"."),
            line_statement_prefix='#'
        )
templ = env.get_template(f"clab.j2")


# Run the topology through jinja2 template to get the final result
topo = templ.render(topology)
with open(topology_name + ".clab.yml", "w") as f:
    f.write(topo)
    print(f"Created Containerlab topology:\t{topology_name}.clab.yml")


# Interface mapping file for cEOS
ceos_interfaces_templ = env.get_template(f"interface_maps/ceos.j2")
for d, m in device_interfaces_map.items():
    ceos_interface_map = ceos_interfaces_templ.render({'map': m})
    with open(d + "_interface_map.json", "w") as f:
        f.write(ceos_interface_map)
        print(f"Created interface map file:\t{d}_interface_map.json")


