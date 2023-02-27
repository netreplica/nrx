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

# Export network topology from NetBox as a graph

import os
import sys
import argparse
import json
import toml
import pynetbox
import networkx as nx

# DEFINE GLOBAL VARs HERE

debug_on = False

def errlog(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
  
def error(*args, **kwargs):
    errlog("Error:", *args, **kwargs)
    sys.exit(1)

def warning(*args, **kwargs):
    errlog("Warning:", *args, **kwargs)

def debug(*args, **kwargs):
    if debug_on:
        errlog("Debug:", *args, **kwargs)

class NB_Network:
    def __init__(self):
        self.config = {}
        self.nodes = []
        self.devices = []
        self.cable_ids = []
        self.interfaces = []
        self.device_ids = []
        self.interface_ids = []


class NB_Factory:
    def __init__(self, config):
        self.config = config
        self.nb_net = NB_Network()
        self.G = nx.Graph(name=config['export_site'])
        self.nb_session = pynetbox.api(self.config['nb_api_url'], token=self.config['nb_api_token'], threading=True)
        try:
            self.nb_site = self.nb_session.dcim.sites.get(name=config['export_site'])
        except pynetbox.core.query.RequestError as e:
            error("NetBox API failure at get sites:", e)
        debug(f"returned site data {self.nb_site}")
        if self.nb_site is None:
            print(f"No data found for a site {config['export_site']}")
        else:
            print(f"Exporting {config['export_site']} site from NetBox at {config['nb_api_url']}")
            try:
                self._get_nb_device_info()
            except pynetbox.core.query.RequestError as e:
                error("NetBox API failure at get devices or interfaces:", e)

            try:
                self._build_network_graph()
            except pynetbox.core.query.RequestError as e:
                error("NetBox API failure at get cables:", e)


    def graph(self):
        return self.G
    
    def _get_nb_device_info(self):
        for device in list(self.nb_session.dcim.devices.filter(site_id=self.nb_site.id, role=self.config['export_device_roles'])):
            d = {
                "id": device.id,
                "type": "device",
                "name": device.name,
                "node_id": -1,
            }
            debug("Adding device:", d)
            self.nb_net.nodes.append(d)
            d["node_id"] = len(self.nb_net.nodes) - 1
            self.nb_net.devices.append(d)
            self.nb_net.device_ids.append(
                device.id)  # index of the device in the devices list will match its ID index in device_ids list

            debug(f"{d['name']} Ethernet interfaces:")
            for interface in list(self.nb_session.dcim.interfaces.filter(device_id=device.id)):
                if "base" in interface.type.value and interface.cable:  # only connected ethernet interfaces
                    debug(device.name, ":", interface, ":", interface.type.value)
                    i = {
                        "id": interface.id,
                        "type": "interface",
                        "name": interface.name,
                        "node_id": -1,
                    }
                    self.nb_net.nodes.append(i)
                    i["node_id"] = len(self.nb_net.nodes) - 1
                    self.nb_net.interfaces.append(i)
                    self.nb_net.interface_ids.append(
                        interface.id)  # index of the interface in the interfaces list will match its ID index in interface_ids list
                    self.nb_net.cable_ids.append(interface.cable.id)

    def _build_network_graph(self):
        if len(self.nb_net.cable_ids) > 0:
            # Making sure there will be a non-empty filter for cables, as otherwise all cables would be returned
            for cable in list(self.nb_session.dcim.cables.filter(id=self.nb_net.cable_ids)):
                if len(cable.a_terminations) == 1 and len(cable.b_terminations) == 1:
                    int_a = cable.a_terminations[0]
                    int_b = cable.b_terminations[0]
                    if isinstance(int_a, pynetbox.models.dcim.Interfaces) and isinstance(int_b, pynetbox.models.dcim.Interfaces):
                        debug("{}:{} <> {}:{}".format(int_a.device, int_a, int_b.device, int_b))
                        try:
                            d_a = self.nb_net.devices[self.nb_net.device_ids.index(int_a.device.id)]
                            d_b = self.nb_net.devices[self.nb_net.device_ids.index(int_b.device.id)]
                            self.G.add_nodes_from([
                                (d_a["node_id"], {"side": "a", "type": "device", "device": d_a}),
                                (d_b["node_id"], {"side": "b", "type": "device", "device": d_b}),
                            ])
                            i_a = self.nb_net.interfaces[self.nb_net.interface_ids.index(int_a.id)]
                            i_b = self.nb_net.interfaces[self.nb_net.interface_ids.index(int_b.id)]
                            self.G.add_nodes_from([
                                (i_a["node_id"], {"side": "a", "type": "interface", "interface": i_a}),
                                (i_b["node_id"], {"side": "b", "type": "interface", "interface": i_b}),
                            ])
                            self.G.add_edges_from([
                                (d_a["node_id"], i_a["node_id"]),
                                (d_b["node_id"], i_b["node_id"]),
                            ])
                            self.G.add_edges_from([
                                (i_a["node_id"], i_b["node_id"]),
                            ])
                        except ValueError as e:
                            debug("One or both devices for this connection are not in the export graph")

    def export_graph_gml(self):
        nx.write_gml(self.G, self.config['export_site'] + ".gml")
        print(f'GML graph saved to {self.config["export_site"]}.gml')

    def export_graph_json(self):
        cyjs = nx.cytoscape_data(self.G)
        with open(self.config['export_site'] + ".cyjs", 'w', encoding='utf-8') as f:
            json.dump(cyjs, f, indent=4)
        print(f'CYJS graph saved to {self.config["export_site"]}.cyjs')

class NetworkTopology:
    def __init__(self):
        self.topology_name = None

    def build_from_file(self, file):
        self.graph_file = file
        self._read_network_graph()
        self.topology_name = self.G.graph["name"]
        self._build_topology()

    def build_from_graph(self, graph):
        self.G = graph
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

        if self.topology_name is None:
            error("cannot export an empty topology")

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

def load_config(filename):
    config = {
        'nb_api_url': '',
        'nb_api_token': '',
        'output_format': 'cyjs',
        'export_device_roles': ["router", "core-switch", "access-switch", "distribution-switch", "tor-switch"],
        'export_site': '',
    }
    if filename is not None and len(filename) > 0:
        try:
            with open(filename, 'r') as f:
                nb_config = toml.load(f)
                for k in config.keys():
                    if k.upper() in nb_config:
                        config[k] = nb_config[k.upper()]
                if len(config['output_format']) > 0:
                        arg_output_check(config['output_format'])
        except OSError as e:
            error(f"Unable to open configuration file {filename}: {e}")
        except toml.decoder.TomlDecodeError as e:
            error(f"Unable to parse configuration file {filename}: {e}")

    config['nb_api_url'] = os.getenv('NB_API_URL', config['nb_api_url'])
    config['nb_api_token'] = os.getenv('NB_API_TOKEN', config['nb_api_token'])

    return config

def arg_input_check(s):
    allowed_values = ['netbox', 'cyjs']
    if s in allowed_values:
        return s
    else:
        raise argparse.ArgumentTypeError(f"input source has to be one of {allowed_values}")

def arg_output_check(s):
    allowed_values = ['gml', 'cyjs', 'clab']
    if s in allowed_values:
        return s
    else:
        raise argparse.ArgumentTypeError(f"output format has to be one of {allowed_values}")

def main():

    # CLI arguments parser
    parser = argparse.ArgumentParser(prog='ntopex.py', description='Network Topology Exporter')
    parser.add_argument('-c', '--config', required=False, help='configuration file')
    parser.add_argument('-i', '--input',  required=False, default='netbox', type=arg_input_check,  help='input source: netbox (default) | cyjs')
    parser.add_argument('-o', '--output', required=False, default='cyjs',   type=arg_output_check, help='output format: cyjs (default) | gml | clab')
    parser.add_argument('-a', '--api',    required=False, help='NetBox API URL')
    parser.add_argument('-s', '--site',   required=False, help='NetBox Site to export')
    parser.add_argument('-d', '--debug',  required=False, help='enable debug output', action=argparse.BooleanOptionalAction)
    parser.add_argument('-f', '--file',   required=False, help='file with the network graph to import')

    # Common parameters
    args = parser.parse_args()

    global debug_on
    debug_on = (args.debug == True)
    debug(f"arguments {args}")

    try:
        config = load_config(args.config)
    except argparse.ArgumentTypeError as e:
        error(f"Unsupported configuration: {e}")

    if args.input is not None and len(args.input) > 0:
        config['input_source'] = args.input

    if args.output is not None and len(args.output) > 0:
        config['output_format'] = args.output

    nb_network = None
    topo = NetworkTopology()

    if config['input_source'] == 'cyjs':
        if config['output_format'] == 'cyjs':
            error("Specify export format different from CYJS with --output")
        elif args.file is not None and len(args.file) > 0:
            # Load graph from file
            topo.build_from_file(args.file)
        else:
            error("Provide a path to CYJS graph using --file")
    elif config['input_source'] == 'netbox':
        if args.api is not None and len(args.api) > 0:
            config['nb_api_url'] = args.api
        if len(config['nb_api_url']) == 0:
            error(f"Need an API URL to connect to NetBox. Use --api argument, NB_API_URL environment variable or key in --config file")
        
        if len(config['nb_api_token']) == 0:
            error(f"Need an API token to connect to NetBox. Use NB_API_TOKEN environment variable or key in --config file")

        if args.site is not None and len(args.site) > 0:
            config['export_site'] = args.site
        elif len(config['export_site']) == 0:
            error(f"Need a Site name to export. Use --site argument, or EXPORT_SITE key in --config file")

        nb_network = NB_Factory(config)
        topo.build_from_graph(nb_network.graph())

    if config['output_format'] == 'clab':
        topo.export_clab()
    else:
        if nb_network is None:
            error(f"Only --input netbox is supported for this type of export format: {config['output_format']}")
        if config['output_format'] == 'gml':
            nb_network.export_graph_gml()
        else:
            nb_network.export_graph_json()

    return 0


if __name__ == '__main__':
    sys.exit(main())
