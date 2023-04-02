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

"""
netreplica exporter

nrx reads a network topology graph from NetBox DCIM system and exports it in one of the following formats:

* Topology file for one of the supported network emulation tools
* Graph data as a JSON file in Cytoscape format CYJS

It can also read the topology graph previously saved as a CYJS file to convert it into the one of supported network emulation formats.
"""

import os
import sys
import argparse
import json
import toml
import pynetbox
import requests
import urllib3
import networkx as nx
import jinja2

#from rich import inspect

# DEFINE GLOBAL VARs HERE

DEBUG_ON = False

def errlog(*args, **kwargs):
    """print message on STDERR"""
    print(*args, file=sys.stderr, **kwargs)

def error(*args, **kwargs):
    """log as error and exit"""
    errlog("Error:", *args, **kwargs)
    sys.exit(1)

def warning(*args, **kwargs):
    """log as warning"""
    errlog("Warning:", *args, **kwargs)

def debug(*args, **kwargs):
    """log as debug"""
    if DEBUG_ON:
        errlog("Debug:", *args, **kwargs)

def error_debug(err, d):
    if not DEBUG_ON:
        err += " Use --debug to see the full error message."
    debug(d)
    error(err)

class NBNetwork:
    """Class to hold network topology data exported from NetBox"""
    def __init__(self):
        self.config = {}
        self.nodes = []
        self.devices = []
        self.cable_ids = []
        self.interfaces = []
        self.device_ids = []
        self.interface_ids = []


class NBFactory:
    """Class to export network topology data from NetBox"""
    def __init__(self, config):
        self.config = config
        self.nb_net = NBNetwork()
        self.G = nx.Graph(name=config['export_site'])
        self.nb_session = pynetbox.api(self.config['nb_api_url'],
                                       token=self.config['nb_api_token'],
                                       threading=True)
        if not config['tls_validate']:
            self.nb_session.http_session.verify = False
            urllib3.disable_warnings()
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
        for device in list(self.nb_session.dcim.devices.filter(site_id=self.nb_site.id,
                                                               role=self.config['export_device_roles'])):
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
                    # index of the interface in the interfaces list will match its ID index in interface_ids list
                    self.nb_net.interface_ids.append(interface.id)
                    self.nb_net.cable_ids.append(interface.cable.id)

    def _build_network_graph(self):
        if len(self.nb_net.cable_ids) > 0:
            # Making sure there will be a non-empty filter for cables, as otherwise all cables would be returned
            for cable in list(self.nb_session.dcim.cables.filter(id=self.nb_net.cable_ids)):
                if len(cable.a_terminations) == 1 and len(cable.b_terminations) == 1:
                    int_a = cable.a_terminations[0]
                    int_b = cable.b_terminations[0]
                    if isinstance(int_a, pynetbox.models.dcim.Interfaces) and \
                        isinstance(int_b, pynetbox.models.dcim.Interfaces):
                        debug(f"{int_a.device}:{int_a} <> {int_b.device}:{int_b}")
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
                        except ValueError:
                            debug("One or both devices for this connection are not in the export graph")

    def export_graph_gml(self):
        export_file = self.config['export_site'] + ".gml"
        try:
            nx.write_gml(self.G, export_file)
        except OSError as e:
            error(f"Writing to {export_file}:", e)
        except nx.exception.NetworkXError as e:
            error("Can't export as GML:", e)
        print(f"GML graph saved to:\t\t\t\t{export_file}")

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
        print(f"CYJS graph saved to:\t\t\t\t{export_file}")

class NetworkTopology:
    """Class to create network topology artifacts"""
    def __init__(self, config):
        self.config = config
        self.G = None
        # For each device we will store a list of {'nos_interface_name': 'emulated_interface_name'} tuples here
        self.device_interfaces_map = {}
        self.topology = {
            'name': None,
            'links': [],
            'nodes': [],
        }
        self.j2env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(self.config['templates_path'], followlinks=True),
                    #line_statement_prefix='#'
                )
        self.templates = {
            'interface_names': {'_path_': 'interface_names', '_description_': 'interface name'},
            'interface_maps':  {'_path_': 'interface_maps',  '_description_': 'interface map'},
            'kinds':           {'_path_': f"{self.config['output_format']}/kinds", '_description_': 'node kind'}
        }

    def build_from_file(self, file):
        self._read_network_graph(file)
        if "name" in self.G.graph.keys():
            self.topology['name'] = self.G.graph["name"]
        self._build_topology()

    def build_from_graph(self, graph):
        self.G = graph
        if "name" in self.G.graph.keys():
            self.topology['name'] = self.G.graph["name"]
        self._build_topology()

    def _read_network_graph(self, file):
        print(f"Reading CYJS topology graph:\t\t\t{file}")
        cyjs = {}
        try:
            with open(file, 'r', encoding='utf-8') as f:
                cyjs = json.load(f)
        except OSError as e:
            error("Can't read CYJS topology graph:", e)
        except json.decoder.JSONDecodeError as e:
            error("Can't parse CYJS topology graph:", e)
        self.G = nx.cytoscape_graph(cyjs)

    def _append_if_node_is_device(self, n):
        if self.G.nodes[n]['type'] == 'device':
            dev = self.G.nodes[n]['device']
            self.topology['nodes'].append(dev)
            if dev['name'] not in self.device_interfaces_map:
                # Initialize an empty map. There is a similar initialization in _append_if_node_is_interface,
                # but we need one here in case the device has no interfaces
                self.device_interfaces_map[dev['name']] = {}
            return True
        return False

    def _append_if_node_is_interface(self, n):
        if self.G.nodes[n]['type'] == 'interface':
            int_name = self.G.nodes[n]['interface']['name']
            dev_name, dev_node_id = None, None
            peer_name, peer_dev_name, peer_dev_node_id = None, None, None
            for a_adj in self.G.adj[n].items():
                if self.G.nodes[a_adj[0]]['type'] == 'device':
                    dev_name = self.G.nodes[a_adj[0]]['device']['name']
                    dev_node_id = self.G.nodes[a_adj[0]]['device']['node_id']
                    if dev_name not in self.device_interfaces_map:
                        # Initialize an empty map if we don't have one yet for this device
                        self.device_interfaces_map[dev_name] = {}
                    self.device_interfaces_map[dev_name][int_name] = {}
                elif self.G.nodes[a_adj[0]]['type'] == 'interface' and self.G.nodes[n]['side'] == 'a':
                    peer_name = self.G.nodes[a_adj[0]]['interface']['name']
                    for b_adj in self.G.adj[a_adj[0]].items():
                        if self.G.nodes[b_adj[0]]['type'] == 'device':
                            peer_dev_name = self.G.nodes[b_adj[0]]['device']['name']
                            peer_dev_node_id = self.G.nodes[b_adj[0]]['device']['node_id']
            if self.G.nodes[n]['side'] == 'a':
                self.topology['links'].append({
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
            return True
        return False

    def _initialize_emulated_interface_names(self):
        # Initialize emulated interface names for each NOS interface name
        for node in self.topology['nodes']:
            if 'name' in node.keys():
                name = node['name']
                if name in self.device_interfaces_map:
                    int_map = self.device_interfaces_map[name]
                    # Sort nos interface names in the map
                    int_list = list(int_map.keys())
                    int_list.sort()
                    # Add emulated interface name for each nos interface name we got from the imported graph.
                    sorted_map = {i: {'name': f"{self._render_emulated_interface_name(node['platform'], i, int_list.index(i))}",
                                      'index': int_list.index(i)} for i in int_list}
                    self.device_interfaces_map[name] = sorted_map
                    # Append entries from device_interfaces_map to each device under self.topology['nodes']
                    node['interfaces'] = self.device_interfaces_map[name]

    def _build_topology(self):
        # Parse graph G into lists of: nodes and links.
        # Keep list of interfaces per device in `device_interfaces_map`, and then add them to each device
        try:
            for n in self.G.nodes:
                if not self._append_if_node_is_device(n):
                    self._append_if_node_is_interface(n)
            self._initialize_emulated_interface_names()
        except KeyError as e:
            error(f"Incomplete data to build topology, {e} key is missing")

    def export_topology(self):
        if self.topology['name'] is None or len(self.topology['name']) == 0:
            error("Cannot export a topology: missing a name")

        # Generate topology data structure
        self.topology['name'] = self.G.name
        self.topology['nodes'] = self._render_emulated_nodes()
        self._initialize_emulated_links()
        self._render_topology()

    def _initialize_emulated_links(self):
        link_id = 0
        for l in self.topology['links']:
            l['id'] = link_id
            l['a']['e_interface'] = self.device_interfaces_map[l['a']['node']][l['a']['interface']]['name']
            l['b']['e_interface'] = self.device_interfaces_map[l['b']['node']][l['b']['interface']]['name']
            l['a']['index'] = self.device_interfaces_map[l['a']['node']][l['a']['interface']]['index']
            l['b']['index'] = self.device_interfaces_map[l['b']['node']][l['b']['interface']]['index']
            l['a']['kind'] = self.G.nodes[l['a']['node_id']]['device']['platform']
            l['b']['kind'] = self.G.nodes[l['b']['node_id']]['device']['platform']
            link_id += 1

    def _get_template(self, ttype, platform, is_required = False):
        template = None
        if ttype in self.templates and '_path_' in self.templates[ttype]:
            desc = self.templates[ttype]['_description_']
            if platform not in self.templates[ttype]:
                try:
                    j2file = f"{self.templates[ttype]['_path_']}/{platform}.j2"
                    template = self.j2env.get_template(j2file)
                    debug(f"Found {desc} template {j2file} for platform {platform}")
                except (OSError, jinja2.TemplateError) as e:
                    m = f"Unable to open {desc} template '{j2file}' for platform '{platform}' with path {self.config['templates_path']}."
                    m += f" Reason: {e}"
                    if is_required:
                        error(m)
                    else:
                        debug(m)
                self.templates[ttype][platform] = template
            else:
                template = self.templates[ttype][platform]
        elif is_required:
            error(f"No such template type as {ttype}")
        return template

    def _render_emulated_nodes(self):
        topo_nodes = []
        for n in self.topology['nodes']:
            if 'platform' in n.keys():
                p = n['platform']
                int_map = self._render_interface_map(n)
                if int_map is not None:
                    n['interface_map'] = int_map

                template = self._get_template('kinds', p, True)
                if template is not None:
                    try:
                        topo_nodes.append(template.render(n))
                    except jinja2.TemplateError as e:
                        error(f"Rendering {self.templates[type]['_description_']} template '{e}' for platform '{p}'")

        return topo_nodes

    def _render_emulated_interface_name(self, platform, interface, index):
        # We assume interface with index `0` is reserved for management, and start with `1`
        default_name = f"eth{index+1}"
        template = self._get_template('interface_names', platform)
        if template is not None:
            try:
                return template.render({'interface': interface, 'index': index})
            except jinja2.TemplateError as e:
                error("Rendering interface naming J2 template:", e)
        return default_name

    def _render_topology(self):
        #debug("Topology data to render:", json.dumps(self.topology))
        # Load Jinja2 template to run the topology through
        try:
            j2file = f"{self.config['output_format']}/topology.j2"
            template = self.j2env.get_template(j2file)
        except (OSError, jinja2.TemplateError) as e:
            error(f"Opening topology template '{j2file}' with path {self.config['templates_path']}. Reason: {e}")

        # Run the topology through jinja2 template to get the final result
        try:
            topo = template.render(self.topology)
        except jinja2.TemplateError as e:
            error("Rendering topology J2 template:", e)

        topo_file = f"{self.topology['name']}.{self.config['output_format']}.yaml"
        try:
            with open(topo_file, "w", encoding="utf-8") as f:
                f.write(topo)
        except OSError as e:
            error(f"Can't write into {topo_file}", e)

        print(f"Created {self.config['output_format']} topology:\t\t\t{topo_file}")

    def _render_interface_map(self, node):
        if 'name' in node and node['name'] in self.device_interfaces_map:
            d = node['name']
        else:
            return None
        if 'platform' in node.keys():
            p = node['platform']
            # Interface mapping file for cEOS
            template = self._get_template('interface_maps', p)
            if template is not None:
                m = self.device_interfaces_map[node['name']]
                try:
                    interface_map = template.render({'map': m})
                except jinja2.TemplateError as e:
                    error("Rendering interface map J2 template:", e)
                int_map_file = f"{d}_interface_map.json"
                try:
                    with open(int_map_file, "w", encoding="utf-8") as f:
                        f.write(interface_map)
                except OSError as e:
                    error(f"Can't write into {int_map_file}", e)
                print(f"Created '{p}' interface map:\t\t\t{int_map_file}")
                return int_map_file
        return None

def arg_input_check(s):
    allowed_values = ['netbox', 'cyjs']
    if s in allowed_values:
        return s
    raise argparse.ArgumentTypeError(f"input source has to be one of {allowed_values}")

def arg_output_check(s):
    allowed_values = ['gml', 'cyjs', 'clab', 'cml']
    if s in allowed_values:
        return s
    raise argparse.ArgumentTypeError(f"output format has to be one of {allowed_values}")

def parse_args():
    """CLI arguments parser"""
    parser = argparse.ArgumentParser(prog='nrx', description="nrx - network topology exporter by netreplica")
    parser.add_argument('-c', '--config',    required=False, help='configuration file')
    parser.add_argument('-i', '--input',     required=False, help='input source: netbox (default) | cyjs',
                                             default='netbox', type=arg_input_check,)
    parser.add_argument('-o', '--output',    required=False, help='output format: cyjs | gml | clab | cml',
                                             type=arg_output_check, )
    parser.add_argument('-a', '--api',       required=False, help='netbox API URL')
    parser.add_argument('-s', '--site',      required=False, help='netbox site to export')
    parser.add_argument('-k', '--insecure',  required=False, help='allow insecure server connections when using TLS',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-d', '--debug',     required=False, help='enable debug output',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-f', '--file',      required=False, help='file with the network graph to import')
    parser.add_argument('-t', '--templates', required=False, help='directory with template files, \
                                                                   will be prepended to TEMPLATES_PATH list \
                                                                   in the configuration file')

    args = parser.parse_args()
    global DEBUG_ON
    DEBUG_ON = args.debug is True
    debug(f"arguments {args}")

    return args

def load_toml_config(filename):
    """Load configuration from a config file in TOML format"""
    config = {
        'nb_api_url': '',
        'nb_api_token': '',
        'tls_validate': True,
        'output_format': 'cyjs',
        'export_device_roles': ["router", "core-switch", "access-switch", "distribution-switch", "tor-switch"],
        'export_site': '',
        'templates_path': ['.'],
    }
    if filename is not None and len(filename) > 0:
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                nb_config = toml.load(f)
                for k in config:
                    if k.upper() in nb_config:
                        config[k] = nb_config[k.upper()]
                if len(config['output_format']) > 0:
                    arg_output_check(config['output_format'])
        except OSError as e:
            error(f"Unable to open configuration file {filename}: {e}")
        except toml.decoder.TomlDecodeError as e:
            error(f"Unable to parse configuration file {filename}: {e}")
        except argparse.ArgumentTypeError as e:
            # config['output_format'] has unsupported value
            error(f"Unsupported configuration: {e}")
    return config

def load_config(args):
    """Load, consolidate and validate configuration"""
    config = load_toml_config(args.config)
    config['nb_api_url'] = os.getenv('NB_API_URL', config['nb_api_url'])
    config['nb_api_token'] = os.getenv('NB_API_TOKEN', config['nb_api_token'])

    # Override config values with arguments
    if args.input is not None and len(args.input) > 0:
        config['input_source'] = args.input
        if config['input_source'] == 'cyjs' and (args.file is None or len(args.file) == 0):
            error("Provide a path to CYJS graph using --file")

        if config['input_source'] == 'netbox':
            if args.api is not None and len(args.api) > 0:
                config['nb_api_url'] = args.api
            if len(config['nb_api_url']) == 0:
                error("Need an API URL to connect to NetBox.\nUse --api argument, NB_API_URL environment variable or key in --config file")
            if len(config['nb_api_token']) == 0:
                error("Need an API token to connect to NetBox.\nUse NB_API_TOKEN environment variable or key in --config file")
            if args.site is not None and len(args.site) > 0:
                config['export_site'] = args.site
            if len(config['export_site']) == 0:
                error("Need a Site name to export. Use --site argument, or EXPORT_SITE key in --config file")

    if args.insecure:
        config['tls_validate'] = False

    if args.output is not None and len(args.output) > 0:
        config['output_format'] = args.output

    if config['input_source'] == config['output_format']:
        error(f"Input and output formats must be different, got '{config['output_format']}'")

    if args.templates is not None and len(args.templates) > 0:
        config['templates_path'].insert(0, args.templates)

    return config

def main():
    """Main"""
    # Parameters
    args = parse_args()
    config = load_config(args)

    nb_network = None
    topo = NetworkTopology(config)

    if config['input_source'] == 'netbox':
        try:
            nb_network = NBFactory(config)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if "SSL: WRONG_VERSION_NUMBER" in str(e):
                error_debug(f"Unable to negotiate TLS version when connecting to {config['nb_api_url']}. "
                             "Could the server be using unencrypted HTTP?", e)
            elif "SSL: CERTIFICATE_VERIFY_FAILED" in str(e):
                error_debug(f"Server certificate validation failed when connecting to {config['nb_api_url']}. "
                             "To skip validation, use --insecure.", e)
            else:
                error_debug(f"Can't connect to {config['nb_api_url']}.", e)
        except Exception as e:
            error("Exporting from NetBox:", e)
        if config['output_format'] == 'gml':
            nb_network.export_graph_gml()
            return 0
        if config['output_format'] == 'cyjs':
            nb_network.export_graph_json()
            return 0

    if config['input_source'] == 'cyjs':
        topo.build_from_file(args.file)
    else:
        topo.build_from_graph(nb_network.graph())

    if config['output_format'] in ['clab', 'cml']:
        topo.export_topology()
    else:
        if nb_network is None:
            error(f"Only --input netbox is supported for this type of export format: {config['output_format']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
