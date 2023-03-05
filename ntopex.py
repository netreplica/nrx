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
import jinja2

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
        except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
            error("NetBox API failure at get sites:", e)
        debug(f"returned site data {self.nb_site}")
        if self.nb_site is None:
            print(f"No data found for a site {config['export_site']}")
        else:
            print(f"Exporting NetBox '{config['export_site']}' site from:\t\t{config['nb_api_url']}")
            try:
                self._get_nb_device_info()
            except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
                error("NetBox API failure at get devices or interfaces:", e)

            try:
                self._build_network_graph()
            except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
                error("NetBox API failure at get cables:", e)


    def graph(self):
        return self.G
    
    def _get_nb_device_info(self):
        for device in list(self.nb_session.dcim.devices.filter(site_id=self.nb_site.id, role=self.config['export_device_roles'])):
            platform, platform_name = "unknown", "unknown"
            vendor, vendor_name = "unknown", "unknown"
            model, model_name = "unknown", "unknown"
            if device.platform is not None:
                platform = device.platform.slug
                platform_name = device.platform.name
                if device.platform.manufacturer is not None:
                    vendor = device.platform.manufacturer.slug
                    vendor_name = device.platform.manufacturer.name
            if device.device_type is not None:
                model = device.device_type.slug
                model_name = device.device_type.model
            d = {
                "id": device.id,
                "type": "device",
                "name": device.name,
                "node_id": -1,
                "platform": platform,
                "platform_name": platform_name,
                "vendor": vendor,
                "vendor_name": vendor_name,
                "model": model,
                "model_name": model_name,
            }
            self.nb_net.nodes.append(d)
            d["node_id"] = len(self.nb_net.nodes) - 1
            self.nb_net.devices.append(d)
            self.nb_net.device_ids.append(
                device.id)  # index of the device in the devices list will match its ID index in device_ids list
            debug("Added device:", d)

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
        export_file = self.config['export_site'] + ".gml"
        try:
            nx.write_gml(self.G, export_file)
        except OSError as e:
            error(f"Writing to {export_file}:", e)
        except nx.exception.NetworkXError as e:
            error("Can't export as GML:", e)
        print(f"GML graph saved to:\t\t\t{export_file}")

    def export_graph_json(self):
        cyjs = nx.cytoscape_data(self.G)
        export_file = self.config['export_site'] + ".cyjs"
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(cyjs, f, indent=4)
        except OSError as e:
            error(f"Writing to {export_file}:", e)
        except TypeError as e:
            error("Can't export as JSON:", e)
        print(f"CYJS graph saved to:\t\t\t{export_file}")

class NetworkTopology:
    def __init__(self, config):
        self.topology_name = None
        self.config = config
        self.j2env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(self.config['templates_path'], followlinks=True),
                    line_statement_prefix='#'
                )

    def build_from_file(self, file):
        self.graph_file = file
        self._read_network_graph()
        if "name" in self.G.graph.keys():
            self.topology_name = self.G.graph["name"]
        self._build_topology()

    def build_from_graph(self, graph):
        self.G = graph
        if "name" in self.G.graph.keys():
            self.topology_name = self.G.graph["name"]
        self._build_topology()

    def _read_network_graph(self):
        print(f"Reading CYJS topology graph:\t\t\t{self.graph_file}")
        cyjs = {}
        try:
            with open(self.graph_file, 'r', encoding='utf-8') as f:
                cyjs = json.load(f)
        except OSError as e:
            error("Can't read CYJS topology graph:", e)
        except json.decoder.JSONDecodeError as e:
            error("Can't parse CYJS topology graph:", e)
        self.G = nx.cytoscape_graph(cyjs)

    def _build_topology(self):
        # Parse graph G into lists of: nodes and links. Keep a list of interfaces per device in `device_interfaces_map`.
        self.nodes, self.links = [], []
        self.device_interfaces_map = {}
        try:
            for n in self.G.nodes:
                if self.G.nodes[n]['type'] == 'device':
                    dev = self.G.nodes[n]['device']
                    self.nodes.append(dev)
                    if dev['name'] not in self.device_interfaces_map:
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
        except KeyError as e:
            error(f"Incomplete data to build topology, {e} key is missing")

    def export_clab(self):
        if self.topology_name is None or len(self.topology_name) == 0:
            error("Cannot export a topology: missing a name")

        # Generate topology data structure for clab
        self.topology = {
            'name': self.G.name,
            'links': self._render_clab_links(), # render links first, to complete device_interfaces_map
            'nodes': self._render_clab_nodes(),
        }

        self._render_clab_topology()

    def _render_clab_links(self):
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

        return [f"[\"{l['a']['node']}:{l['a']['c_interface']}\", \"{l['b']['node']}:{l['b']['c_interface']}\"]" for l in self.links]

    def _render_clab_nodes(self):
        # Load Jinja2 template for Containerlab kinds
        topo_nodes = []
        for n in self.nodes:
            if 'platform' in n.keys():
                p = n['platform']
                if 'platform_name' in n.keys():
                    pn = n['platform_name']
                else:
                    pn = p
                try:
                    templ = self.j2env.get_template(f"clab/kinds/{p}.j2")
                except (OSError, jinja2.TemplateError) as e:
                    error(f"Opening Containerlab J2 template '{e}' for platform '{pn}' with path {self.config['templates_path']}")
                # Run the topology through jinja2 template to get the final result
                try:
                    topo_nodes.append(templ.render(n))
                except jinja2.TemplateError as e:
                    error(f"Rendering Containerlab J2 template '{e}' for platform '{pn}'")

                self._create_interface_map(n)

        return topo_nodes


    def _render_clab_topology(self):
        debug("Topology data to render:", json.dumps(self.topology))
        # Load Jinja2 template for Containerlab to run the topology through
        try:
            templ = self.j2env.get_template(f"clab/topology.j2")
        except (OSError, jinja2.TemplateError) as e:
            error(f"Opening Containerlab J2 template '{e}' with path {self.config['templates_path']}")

        # Run the topology through jinja2 template to get the final result
        try:
            topo = templ.render(self.topology)
        except jinja2.TemplateError as e:
            error("Rendering Containerlab J2 template:", e)

        clab_file = f"{self.topology_name}.clab.yml"
        try:
            with open(clab_file, "w") as f:
                f.write(topo)
        except OSError as e:
            error(f"Can't write into {clab_file}", e)

        print(f"Created Containerlab topology:\t\t\t{clab_file}")

    def _create_interface_map(self, node):
        if 'name' in node.keys() and node['name'] in self.device_interfaces_map.keys():
            d = node['name']
        else:
            return
        if 'platform' in node.keys() and node['platform'] == 'ceos': # replace by patten matching
            if 'platform_name' in node.keys():
                pn = node['platform_name']
            else:
                pn = node['platform']
            debug(f"Creating interface map for {node}")
            # Interface mapping file for cEOS
            try:
                ceos_interfaces_templ = self.j2env.get_template(f"interface_maps/ceos.j2")
            except jinja2.TemplateError as e:
                error(f"Opening interface map J2 template '{e}' with path {self.config['templates_path']}")
            m = self.device_interfaces_map[node['name']]
            debug(f"{d} inteface map:", m)
            try:
                ceos_interface_map = ceos_interfaces_templ.render({'map': m})
            except jinja2.TemplateError as e:
                error("Rendering interface map J2 template:", e)
            int_map_file = f"{d}_interface_map.json"
            try:
                with open(int_map_file, "w") as f:
                    f.write(ceos_interface_map)
            except OSError as e:
                error(f"Can't write into {int_map_file}", e)
            print(f"Created '{pn}' interface map:\t\t{int_map_file}")

def load_config(filename):
    config = {
        'nb_api_url': '',
        'nb_api_token': '',
        'output_format': 'cyjs',
        'export_device_roles': ["router", "core-switch", "access-switch", "distribution-switch", "tor-switch"],
        'export_site': '',
        'templates_path': ['.'],
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
    parser.add_argument('-c', '--config',    required=False, help='configuration file')
    parser.add_argument('-i', '--input',     required=False, default='netbox', type=arg_input_check,  help='input source: netbox (default) | cyjs')
    parser.add_argument('-o', '--output',    required=False, type=arg_output_check, help='output format: cyjs | gml | clab')
    parser.add_argument('-a', '--api',       required=False, help='NetBox API URL')
    parser.add_argument('-s', '--site',      required=False, help='NetBox Site to export')
    parser.add_argument('-d', '--debug',     required=False, help='enable debug output', action=argparse.BooleanOptionalAction)
    parser.add_argument('-f', '--file',      required=False, help='file with the network graph to import')
    parser.add_argument('-t', '--templates', required=False, help='directory with template files, will be prepended to TEMPLATES_PATH list in the configuration file')

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

    if args.templates is not None and len(args.templates) > 0:
        config['templates_path'].insert(0, args.templates)

    nb_network = None
    topo = NetworkTopology(config)

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

        try:
            nb_network = NB_Factory(config)
        except Exception as e:
            error("Exporting from NetBox:", e)
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
