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
import math
import ast
import toml
import pynetbox
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, Timeout, HTTPError
import urllib3
import networkx as nx
import jinja2
import yaml

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

def create_output_directory(topology_name, config_dir):
    dir_name = "."
    if len(topology_name) > 0:
        dir_name = topology_name
    if len(config_dir) > 0:
        dir_name = config_dir
    if dir_name != ".":
        create_dirs(dir_name)
    return dir_name

def create_dirs(dir_path):
    try:
        os.makedirs(dir_path)
        abs_path = os.path.abspath(dir_path)
        debug(f"Created directory '{dir_path}'")
        return abs_path
    except FileExistsError:
        abs_path = os.path.abspath(dir_path)
        debug(f"Directory '{dir_path}' already exists, will reuse")
        return abs_path
    except OSError as e:
        error(f"An error occurred while creating the directory: {str(e)}")
    return None

class TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter with custom API timeout"""
    def __init__(self, timeout, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        if timeout is None:
            timeout = self.timeout
        return super().send(request, stream, timeout, verify, cert, proxies)

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
        if len(config['export_site']) > 0:
            self.topology_name = config['export_site']
        elif len(config['export_tags']) > 0:
            self.topology_name = "-".join(config['export_tags'])
        self.G = nx.Graph(name=self.topology_name)
        self.nb_session = pynetbox.api(self.config['nb_api_url'],
                                       token=self.config['nb_api_token'],
                                       threading=True)
        self.nb_site = None
        if not config['tls_validate']:
            self.nb_session.http_session.verify = False
            urllib3.disable_warnings()
        if config['api_timeout'] > 0:
            adapter = TimeoutHTTPAdapter(config['api_timeout'])
            self.nb_session.http_session.mount("http://", adapter)
            self.nb_session.http_session.mount("https://", adapter)
        print(f"Connecting to NetBox at: {config['nb_api_url']}")
        if len(config['export_site']) > 0:
            debug(f"Fetching site: {config['export_site']}")
            try:
                self.nb_site = self.nb_session.dcim.sites.get(name=config['export_site'])
            except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
                error("NetBox API failure at get site:", e)
            if self.nb_site is None:
                error(f"Site not found: {config['export_site']}")
            else:
                print(f"Fetching devices from site: {config['export_site']}")
        else:
            print(f"Fetching devices with tags: {','.join(config['export_tags'])}")

        try:
            self._get_nb_devices()
            self._get_nb_interfaces()
        except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
            error("NetBox API failure at get devices or interfaces:", e)

        self._build_graph()


    def graph(self):
        return self.G

    def _get_nb_devices(self):
        """Get device list from NetBox filtered by site, tags and device roles"""
        devices = None
        if self.nb_site is None:
            devices = self.nb_session.dcim.devices.filter(tag=self.config['export_tags'],
                                                          role=self.config['export_device_roles'])
        else:
            devices = self.nb_session.dcim.devices.filter(site_id=self.nb_site.id,
                                                          tag=self.config['export_tags'],
                                                          role=self.config['export_device_roles'])
        for device in list(devices):
            d = self._init_device(device)
            self.nb_net.nodes.append(d)
            d["node_id"] = len(self.nb_net.nodes) - 1
            self.nb_net.devices.append(d)
            d["device_index"] = len(self.nb_net.devices) - 1 # do not use insert with self.nb_net.devices!
            # index of the device in the devices list will match its ID index in device_ids list
            self.nb_net.device_ids.append(device.id)
            debug("Added device:", d)


    def _get_nb_interfaces(self, block_size = 4):
        """Get interfaces from NetBox filtered by devices we already have in the network topology"""
        size = len(self.nb_net.device_ids)
        debug(f"Exporting interfaces from with {size} devices, in blocks of {block_size}")
        for i in range(0, size, block_size):
            device_block = self.nb_net.device_ids[i:i + block_size]
            for interface in list(self.nb_session.dcim.interfaces.filter(device_id=device_block,
                                                                         kind="physical",
                                                                         cabled=True,
                                                                         connected=True)):
                if "base" in interface.type.value and interface.cable:  # only connected ethernet interfaces
                    #debug(device.name, ":", interface, ":", interface.type.value)
                    i = {
                        "id": interface.id,
                        "type": "interface",
                        "name": interface.name,
                        "node_id": -1,
                    }
                    self.nb_net.nodes.append(i)
                    i["node_id"] = len(self.nb_net.nodes) - 1
                    self.nb_net.interfaces.append(i)
                    i["interface_index"] = len(self.nb_net.interfaces) - 1 # do not use insert with self.nb_net.interfaces!
                    # index of the interface in the interfaces list will match its ID index in interface_ids list
                    self.nb_net.interface_ids.append(interface.id)
                    self.nb_net.cable_ids.append(interface.cable.id)


    def _init_device(self, device):
        """Initialize device data"""
        d = {
            "id": device.id,
            "type": "device",
            "name": None,
            "node_id": -1,
            "site": "",
            "platform": "unknown",
            "platform_name": "unknown",
            "vendor": "unknown",
            "vendor_name": "unknown",
            "model": "unknown",
            "model_name": "unknown",
            "role": "unknown",
            "role_name": "unknown",
            "primary_ip4": "",
            "primary_ip6": "",
            "config": "",
        }

        if device.name is not None and len(device.name) > 0:
            d["name"] = device.name
        if device.site is not None:
            d["site"] = device.site.name
        if device.platform is not None:
            d["platform"] = device.platform.slug
            d["platform_name"] = device.platform.name
        if device.device_type is not None:
            d["model"] = device.device_type.slug
            d["model_name"] = device.device_type.model
            if device.device_type.manufacturer is not None:
                d["vendor"] = device.device_type.manufacturer.slug
                d["vendor_name"] = device.device_type.manufacturer.name
        if device.device_role is not None:
            d["role"] = device.device_role.slug
            d["role_name"] = device.device_role.name
            if d["name"] is None:
                d["name"] = f"{d['role']}-{device.id}"
        if device.primary_ip4 is not None:
            d["primary_ip4"] = device.primary_ip4.address
        if device.primary_ip6 is not None:
            d["primary_ip6"] = device.primary_ip6.address
        if self.config["export_configs"]:
            d["config"] = self._get_device_config(device)
        return d

    def _get_device_config(self, device):
        """Get device config from NetBox"""
        headers = {
            'Authorization': f"Token {self.config['nb_api_token']}",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        url = f"{self.config['nb_api_url']}/api/dcim/devices/{device.id}/render-config/"
        try:
            response = requests.post(url, headers=headers, timeout=self.config['api_timeout'], verify=self.config['tls_validate'])
            response.raise_for_status()  # Raises an HTTPError if the response status is an error
            config_response = ast.literal_eval(response.text)
            if "content" in config_response:
                return config_response["content"]
        except HTTPError as e:
            debug(f"{device.name}: Get device configuration request failed: {e}")
        except (Timeout, RequestException) as e:
            debug(f"{device.name}: Get device configuration failed: {e}")
        except SyntaxError as e:
            debug(f"{device.name}: Get device configuration failed: can't parse rendered configuration - {e}")
        return ""

    def _trace_cable(self, cable):
        if len(cable.a_terminations) == 1 and len(cable.b_terminations) == 1:
            term_a = cable.a_terminations[0]
            term_b = cable.b_terminations[0]
            if isinstance(term_a, pynetbox.models.dcim.Interfaces) and \
               isinstance(term_b, pynetbox.models.dcim.Interfaces):
                return [term_a, term_b]
            interface = None
            if isinstance(term_a, pynetbox.models.dcim.Interfaces):
                interface = term_a
            elif isinstance(term_b, pynetbox.models.dcim.Interfaces):
                interface = term_b
            if interface is not None:
                trace = interface.trace()
                if len(trace) > 0:
                    if len(trace[0]) == 1 and len(trace[-1]) == 1:
                        side_a = trace[0][0]
                        side_b = trace[-1][0]
                        if isinstance(side_a, pynetbox.models.dcim.Interfaces) and isinstance(side_b, pynetbox.models.dcim.Interfaces):
                            debug(f"Traced {side_a.device} {side_a.name} <-> {side_b.device} {side_b.name}: {trace}")
                            return [side_a, side_b]
            debug(f"Skipping {cable} as both terminations are not interfaces or cannot be traced")
            return []
        if len(cable.a_terminations) < 1 or len(cable.b_terminations) < 1:
            debug(f"Skipping {cable} as one or both sides are not connected")
            return []
        debug(f"Skipping {cable} as it has more than one termination on one or both sides")
        return []

    def _add_cable_to_graph(self, cable):
        edge = self._trace_cable(cable)
        if len(edge) == 2:
            int_a = edge[0]
            int_b = edge[1]
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

    def _build_graph_edges(self, block_size):
        size = len(self.nb_net.cable_ids)
        debug(f"Exporting {size} cables to build the network graph, in blocks of {block_size}")
        for i in range(0, size, block_size):
            cables_block = self.nb_net.cable_ids[i:i + block_size]
            for cable in list(self.nb_session.dcim.cables.filter(id=cables_block)):
                self._add_cable_to_graph(cable)

    def _build_graph(self):
        attempts, max_attempts = 0, 3
        block_size = 64
        while attempts < max_attempts:
            try:
                self._build_graph_edges(block_size)
                break # success, break out of while loop
            except (requests.Timeout, requests.exceptions.HTTPError) as e:
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code != 414:
                    error("NetBox API failure at get cables:", e)
                else:
                    warning("NetBox API failure at get cables, will reduce cables block size and retry:", e)
                    attempts += 1
                    block_size = block_size // 2
            except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
                error("NetBox API failure at get cables:", e)
        if attempts == max_attempts:
            error("NetBox API failure at get cables, max attempts reached")

    def export_graph_gml(self):
        export_file = self.topology_name + ".gml"
        dir_path = create_output_directory(self.topology_name, self.config['output_dir'])
        export_path = f"{dir_path}/{export_file}"
        try:
            nx.write_gml(self.G, export_path)
        except OSError as e:
            error(f"Writing to {export_path}:", e)
        except nx.exception.NetworkXError as e:
            error("Can't export as GML:", e)
        print(f"GML graph saved to: {export_path}")

    def export_graph_json(self):
        cyjs = nx.cytoscape_data(self.G)
        dir_path = create_output_directory(self.topology_name, self.config['output_dir'])
        export_file = self.topology_name + ".cyjs"
        export_path = f"{dir_path}/{export_file}"
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(cyjs, f, indent=4)
        except OSError as e:
            error(f"Writing to {export_path}:", e)
        except TypeError as e:
            error("Can't export as JSON:", e)
        print(f"CYJS graph saved to: {export_path}")

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
            # lists of device_index values grouped by role (e.g. {'spine': [1, 2], 'leaf': [3, 4]})
            'roles': {},
        }
        self.j2env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(self.config['templates_path'], followlinks=True),
                    extensions=['jinja2.ext.do'],
                    trim_blocks=True, lstrip_blocks=True
                )
        self.j2env.filters['ceil'] = math.ceil
        self.templates = {
            'interface_names': {'_path_': f"{self.config['output_format']}/interface_names", '_description_': 'interface name'},
            'interface_maps':  {'_path_': 'interface_maps',  '_description_': 'interface map'},
            'kinds':           {'_path_': f"{self.config['output_format']}/kinds", '_description_': 'node kind'}
        }
        self.files_path = '.'

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
        print(f"Reading CYJS topology graph: {file}")
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
            if 'role' in dev:
                role = dev['role']
                if role in self.topology['roles']:
                    self.topology['roles'][role].append(dev['device_index'])
                else:
                    self.topology['roles'][role] = [dev['device_index']]
                if role in self.config['device_role_levels']:
                    dev['level'] = self.config['device_role_levels'][role]
            if 'level' not in dev:
                dev['level'] = 0

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
                    dev_index = self.G.nodes[a_adj[0]]['device']['device_index']
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
                            peer_dev_index = self.G.nodes[b_adj[0]]['device']['device_index']
            if self.G.nodes[n]['side'] == 'a':
                self.topology['links'].append({
                    'a': {
                        'node': dev_name,
                        'node_id': dev_node_id,
                        'device_index': dev_index,
                        'interface': int_name,
                    },
                    'b': {
                        'node': peer_dev_name,
                        'node_id': peer_dev_node_id,
                        'device_index': peer_dev_index,
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

    def _rank_nodes(self):
        for device_indexes in self.topology['roles'].values():
            device_indexes.sort()
        for n in self.topology['nodes']:
            if 'role' in n:
                role = n['role']
                if role in self.topology['roles']:
                    role_size = len(self.topology['roles'][role])
                    if role_size > 1:
                        n['rank'] = self.topology['roles'][role].index(n['device_index']) / (role_size - 1)
            if 'rank' not in n:
                n['rank'] = 0.5

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

        self._rank_nodes()

    def export_topology(self):
        if self.topology['name'] is None or len(self.topology['name']) == 0:
            error("Cannot export a topology: missing a name")

        debug(f"Exporting topology. Device role groups: {self.topology['roles']}")
        # Create a directory for output files
        self.files_path = create_output_directory(self.topology['name'], self.config['output_dir'])
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
                        if platform == 'default':
                            error(m)
                        else:
                            # Render a default template
                            debug(f"{m}. Rendering a default template instead.")
                            return self._get_template(ttype, "default", True)
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

                node_config = self._save_node_configuration(n)
                if node_config is not None:
                    n['configuration_file'] = node_config

                template = self._get_template('kinds', p, True)
                if template is not None:
                    try:
                        topo_nodes.append(template.render(n))
                    except jinja2.TemplateError as e:
                        error(f"Rendering {self.templates['kinds']['_description_']} template for platform '{p}': {e}")

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

        self._write_topology(topo)
        self._print_motd(topo)

    def _write_topology(self, topo):
        if self.config['output_format'] == 'graphite':
            # <topology-name>.graphite.json
            topo_file = f"{self.topology['name']}.{self.config['output_format']}.json"
        elif self.config['output_format'] == 'd2':
            # <topology-name>.d2
            topo_file = f"{self.topology['name']}.{self.config['output_format']}"
        else:
            # <topology-name>.clab.yaml or <topology-name>.cml.yaml
            topo_file = f"{self.topology['name']}.{self.config['output_format']}.yaml"
        try:
            topo_path = f"{self.files_path}/{topo_file}"
            with open(topo_path, "w", encoding="utf-8") as f:
                f.write(topo)
        except OSError as e:
            error(f"Can't write into {topo_path}", e)

        print(f"Created {self.config['output_format']} topology: {topo_path}")

    def _print_motd(self, topo):
        topo_dict = {}
        try:
            if self.config['output_format'] == 'graphite':
                topo_dict = ast.literal_eval(topo)
            elif self.config['output_format'] == 'cml':
                topo_dict = yaml.safe_load(topo)
                if 'lab' in topo_dict and 'notes' in topo_dict['lab'] and 'motd' not in topo_dict:
                    topo_dict['motd'] = topo_dict['lab']['notes']
        except (SyntaxError, yaml.scanner.ScannerError) as e:
            debug("Can't parse topology as a dictionary:", e)
        if 'motd' in topo_dict:
            print(f"{topo_dict['motd']}")
        elif self.config['output_format'] == 'clab':
            print(f"To deploy this topology, run: sudo -E clab dep -t {self.files_path}/{self.topology['name']}.clab.yaml")
        elif self.config['output_format'] == 'd2':
            print(f"To visualize this D2 topology, open https://play.d2lang.com and paste content of the file: {self.files_path}/{self.topology['name']}.d2")

    def _render_interface_map(self, node):
        """Render interface mapping file for a node"""
        if self.config['output_format'] in ['graphite', 'd2']:
            # No need to render interface maps
            return None
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
                int_map_path = f"{self.files_path}/{int_map_file}"
                try:
                    with open(int_map_path, "w", encoding="utf-8") as f:
                        f.write(interface_map)
                except OSError as e:
                    error(f"Can't write into {int_map_path}", e)
                print(f"Created '{p}' interface map: {int_map_path}")
                return int_map_file
        return None

    def _save_node_configuration(self, node):
        """Save node configuration to a file"""
        if 'name' in node and len(node['name']) > 0:
            name = node['name']
        else:
            return None
        if 'config' in node and len(node['config']) > 0:
            config = node['config']
        else:
            return None
        if self.config['output_format'] == 'clab':
            # Support for Containerlab startup configurations
            config_file = f"{name}.config"
            config_path = f"{self.files_path}/{config_file}"
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(config)
            except OSError as e:
                error(f"Can't write into {config_path}", e)
            print(f"Created device configuration file: {config_path}")
            return config_file
        return None

def arg_input_check(s):
    """Check if input source is supported"""
    allowed_values = ['netbox', 'cyjs']
    if s in allowed_values:
        return s
    raise argparse.ArgumentTypeError(f"input source has to be one of {allowed_values}")

def arg_output_check(s):
    """Check if output format is supported"""
    allowed_values = ['gml', 'cyjs', 'clab', 'cml', 'graphite', 'd2']
    if s in allowed_values:
        return s
    raise argparse.ArgumentTypeError(f"output format has to be one of {allowed_values}")

def parse_args():
    """CLI arguments parser"""
    parser = argparse.ArgumentParser(prog='nrx', description="nrx - network topology exporter by netreplica")
    parser.add_argument('-c', '--config',    required=False, help='configuration file')
    parser.add_argument('-i', '--input',     required=False, help='input source: netbox (default) | cyjs',
                                             default='netbox', type=arg_input_check,)
    parser.add_argument('-o', '--output',    required=False, help='output format: cyjs | gml | clab | cml | graphite | d2',
                                             type=arg_output_check, )
    parser.add_argument('-a', '--api',       required=False, help='netbox API URL')
    parser.add_argument('-s', '--site',      required=False, help='netbox site to export')
    parser.add_argument('-t', '--tags',      required=False, help='netbox tags to export, for multiple tags use a comma-separated list: tag1,tag2,tag3 (uses AND logic)')
    parser.add_argument('-n', '--noconfigs', required=False, help='disable device configuration export (enabled by default)',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-k', '--insecure',  required=False, help='allow insecure server connections when using TLS',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-d', '--debug',     required=False, help='enable debug output',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-f', '--file',      required=False, help='file with the network graph to import')
    parser.add_argument('-T', '--templates', required=False, help='directory with template files, \
                                                                   will be prepended to TEMPLATES_PATH list \
                                                                   in the configuration file')
    parser.add_argument('-D', '--dir',       required=False, help='save files into specified directory. \
                                                                   nested relative and absolute paths are OK \
                                                                   (topology name is used by default)')

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
        'api_timeout': 10,
        'output_format': 'cyjs',
        'export_device_roles': ["router", "core-switch", "access-switch", "distribution-switch", "tor-switch"],
        'device_role_levels': {
            'unknown':              0,
            'server':               0,
            'tor-switch':           1,
            'access-switch':        1,
            'leaf':                 1,
            'distribution-switch':  2,
            'spine':                2,
            'core-switch':          3,
            'super-spine':          3,
            'router':               4,
        },
        'export_site': '',
        'export_tags': [],
        'export_configs': True,
        'templates_path': ['.'],
        'output_dir': '',
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

def config_apply_netbox_args(config, args):
    """Apply netbox-related arguments to the configuration and validate it"""
    if args.api is not None and len(args.api) > 0:
        config['nb_api_url'] = args.api
    if len(config['nb_api_url']) == 0:
        error("Need an API URL to connect to NetBox.\nUse --api argument, NB_API_URL environment variable or key in --config file")
    if len(config['nb_api_token']) == 0:
        error("Need an API token to connect to NetBox.\nUse NB_API_TOKEN environment variable or key in --config file")
    if args.site is not None and len(args.site) > 0:
        config['export_site'] = args.site
    if args.tags is not None and len(args.tags) > 0:
        config['export_tags'] = args.tags.split(',')
        debug(f"List of tags to filter devices for export: {config['export_tags']}")
    if len(config['export_site']) == 0 and len(config['export_tags']) == 0:
        error("Need a Site name or Tags to export. Use --site/--tags arguments, or EXPORT_SITE/EXPORT_TAGS key in --config file")
    if args.noconfigs is not None:
        if args.noconfigs:
            config['export_configs'] = False
        else:
            config['export_configs'] = True

    return config

def load_config(args):
    """Load, consolidate and validate configuration"""
    config = load_toml_config(args.config)
    config['nb_api_url'] = os.getenv('NB_API_URL', config['nb_api_url'])
    config['nb_api_token'] = os.getenv('NB_API_TOKEN', config['nb_api_token'])

    # Override config values with arguments and validate
    if args.input is not None and len(args.input) > 0:
        config['input_source'] = args.input
        if config['input_source'] == 'cyjs' and (args.file is None or len(args.file) == 0):
            error("Provide a path to CYJS graph using --file")
        if config['input_source'] == 'netbox':
            config = config_apply_netbox_args(config, args)

    if args.insecure:
        config['tls_validate'] = False

    if args.output is not None and len(args.output) > 0:
        config['output_format'] = args.output

    if config['input_source'] == config['output_format']:
        error(f"Input and output formats must be different, got '{config['output_format']}'")

    if args.templates is not None and len(args.templates) > 0:
        config['templates_path'].insert(0, args.templates)

    if args.dir is not None and len(args.dir) > 0:
        config['output_dir'] = args.dir

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

    if config['output_format'] in ['clab', 'cml', 'graphite', 'd2']:
        topo.export_topology()
    else:
        if nb_network is None:
            error(f"Only --input netbox is supported for this type of export format: {config['output_format']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
