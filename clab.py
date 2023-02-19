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

# Read CYJS graph data into a dictionary and initialize networkx graph from it
import sys
import argparse
import json
import networkx as nx

# DEFINE GLOBAL VARs HERE

debug_on = False

def errlog(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

def debug(*args, **kwargs):
  if debug_on:
    errlog(*args, **kwargs)

class NetworkGraph:
    def __init__(self, file):
        self.graph_file = file
        self._read_network_graph()
        self.topology_name = self.G.graph["name"]
        self._build_topology()

    def _read_network_graph(self):
        print(f"Reading CYJS topology graph:\t{self.graph_file}")
        cyjs = {}
        with open(self.graph_file, 'r', encoding='utf-8') as f:
            cyjs = json.load(f)
        self.G = nx.cytoscape_graph(cyjs)

    def _build_topology(self):
        # Parse graph G into lists of: nodes and links. Keep a list of interfaces per device in `device_interfaces_map`.
        self.nodes, self.links = [], []
        self.device_interfaces_map = {}
        for n in self.G.nodes:
            if self.G.nodes[n]['type'] == 'device':
                dev = self.G.nodes[n]['device']
                self.nodes.append(dev)
                self.device_interfaces_map[dev['name']] = {}
            elif self.G.nodes[n]['type'] == 'interface':
                int_name = self.G.nodes[n]['interface']['name']
                dev_name, dev_node_id = None, None
                peer_name, peer_dev_name, peer_dev_node_id = None, None, None
                for a_adj in self.G.adj[n].items():
                    if self.G.nodes[a_adj[0]]['type'] == 'device':
                        dev_name = self.G.nodes[a_adj[0]]['device']['name']
                        dev_node_id = self.G.nodes[a_adj[0]]['device']['node_id']
                        self.device_interfaces_map[dev_name][int_name] = ""
                    elif self.G.nodes[a_adj[0]]['type'] == 'interface' and self.G.nodes[n]['side'] == 'a':
                        peer_name = self.G.nodes[a_adj[0]]['interface']['name']
                        for b_adj in self.G.adj[a_adj[0]].items():
                            if self.G.nodes[b_adj[0]]['type'] == 'device':
                                peer_dev_name = self.G.nodes[b_adj[0]]['device']['name']
                                peer_dev_node_id = self.G.nodes[b_adj[0]]['device']['node_id']
                if self.G.nodes[n]['side'] == 'a':
                    self.links.append({
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

    def export_clab(self):

        # Create container-compatible interface names for each device. We assume interface with index `0` is reserved for management, and start with `1`
        for node, map in self.device_interfaces_map.items():
            # sort keys (interface names) in the map
            map_keys = list(map.keys())
            map_keys.sort()
            sorted_map = {k: f"eth{map_keys.index(k)+1}" for k in map_keys}
            self.device_interfaces_map[node] = sorted_map

        for l in self.links:
            l['a']['c_interface'] = self.device_interfaces_map[l['a']['node']][l['a']['interface']]
            l['b']['c_interface'] = self.device_interfaces_map[l['b']['node']][l['b']['interface']]

        # Generate topology data structure for clab
        self.topology = {
            'name': self.G.name,
            'nodes': [f"{n['name']}" for n in self.nodes],
            'links': [f"[\"{l['a']['node']}:{l['a']['c_interface']}\", \"{l['b']['node']}:{l['b']['c_interface']}\"]" for l in self.links],
        }

        # Load Jinja2 template for Containerlab to run the topology through
        from jinja2 import Environment, FileSystemLoader
        env = Environment(
                    loader=FileSystemLoader(f"."),
                    line_statement_prefix='#'
                )
        templ = env.get_template(f"clab.j2")

        # Run the topology through jinja2 template to get the final result
        topo = templ.render(self.topology)
        with open(self.topology_name + ".clab.yml", "w") as f:
            f.write(topo)
            print(f"Created Containerlab topology:\t{self.topology_name}.clab.yml")

        # Interface mapping file for cEOS
        ceos_interfaces_templ = env.get_template(f"interface_maps/ceos.j2")
        for d, m in self.device_interfaces_map.items():
            ceos_interface_map = ceos_interfaces_templ.render({'map': m})
            with open(d + "_interface_map.json", "w") as f:
                f.write(ceos_interface_map)
                print(f"Created interface map file:\t{d}_interface_map.json")


def main():

    # CLI arguments parser
    parser = argparse.ArgumentParser(prog='clab.py', description='Network Topology Exporter')
    parser.add_argument('-f', '--file', required=True, help='file with the network graph in CYJS format to import')
    parser.add_argument('-d', '--debug', required=False, help='enable debug output', action=argparse.BooleanOptionalAction)

    # Common parameters
    args = parser.parse_args()

    global debug_on
    debug_on = (args.debug == True)
    debug(f"DEBUG: arguments {args}")

    graph_file = args.file

    ng = NetworkGraph(graph_file)
    ng.export_clab()

    return 0

if __name__ == '__main__':
    sys.exit(main())
