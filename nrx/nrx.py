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

__version__ = 'v0.4.0-rc3'
__author__ = 'Alex Bortok and Netreplica Team'

import os
import sys
import argparse
import json
import math
import ast
import zipfile
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
NRX_CONFIG_DIR = ".nr"
NRX_DEFAULT_CONFIG_NAME = "nrx.conf"
NRX_VERSIONS_NAME = "versions.yaml"
NRX_FORMATS_NAME = "formats.yaml"
NRX_MAP_NAME = "platform_map.yaml"
NRX_REPOSITORY = "https://github.com/netreplica/nrx"
NRX_TEMPLATES_REPOSITORY = "https://github.com/netreplica/templates"
NRX_REPOSITORY_TIMEOUT = 10


def nrx_config_dir():
    """Return path to the nrx configuration directory"""
    return f"{os.getenv('HOME', os.getcwd())}/{NRX_CONFIG_DIR}"

def nrx_default_config_path():
    """Return path to the default nrx configuration file"""
    return f"{nrx_config_dir()}/{NRX_DEFAULT_CONFIG_NAME}"

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
        debug(f"[CREATE_DIRS] Created directory '{dir_path}'")
        return abs_path
    except FileExistsError:
        abs_path = os.path.abspath(dir_path)
        debug(f"[CREATE_DIRS] Directory '{dir_path}' already exists, will reuse")
        return abs_path
    except OSError as e:
        error(f"[CREATE_DIRS] An error occurred while creating the directory: {str(e)}")
    return None


def update_symlink(link_path, target_path, log_context="[SYMLINK]"):
    """Create a symlink to a target_path if it doesn't exist yet, or update it if it points to a different target_path"""
    # Remove an existing symlink
    if os.path.exists(link_path):
        if os.path.islink(link_path):
            try:
                os.remove(link_path)
                debug(f"{log_context} Deleted existing symlink {link_path}")
            except OSError as e:
                warning(f"{log_context} Can't delete existing symlink {link_path}: {e}, skipping.")
        else:
            warning(f"{log_context} {link_path} exists and is not a symlink, skipping.")
    # Create a symlink
    if not os.path.exists(link_path):
        try:
            os.symlink(target_path, link_path)
            debug(f"{log_context} Created a symlink: {link_path}")
        except OSError as e:
            error(f"{log_context} Can't create a symlink: {e}")


def remove_file(file_path, log_context="[REMOVE]"):
    """Remove a file"""
    try:
        os.remove(file_path)
        debug(f"{log_context} Deleted {file_path}")
    except OSError as e:
        error(f"{log_context} Can't delete {file_path}: {e}")


def unzip_file(zip_path, dir_path, log_context="[UNZIP]"):
    """Unzip a file to a directory"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dir_path)
            debug(f"{log_context} Unzipped templates to {dir_path}")
    except (zipfile.BadZipFile, FileNotFoundError, Exception) as e:
        error(f"{log_context} Can't unzip {zip_path}: {e}")

def load_yaml_from_file(file, log_context="[LOAD_YAML]"):
    """Load YAML from a file"""
    yaml_data = None
    try:
        with open(file, 'r', encoding='utf-8') as f:
            try:
                yaml_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                warning(f"{log_context} Can't parse {file}: {e}")
            f.close()
    except OSError as e:
        debug(f"{log_context} Can't read {file}: {e}")
    return yaml_data

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
            self._get_nb_objects("interfaces", self.config['nb_api_params']['interfaces_block_size'])
            self._get_nb_objects("cables", self.config['nb_api_params']['cables_block_size'])
        except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
            error("NetBox API failure", e)


    def graph(self):
        return self.G


    def _get_nb_objects(self, kind, block_size):
        attempts, max_attempts = 0, 3
        while attempts < max_attempts:
            try:
                if kind == "interfaces":
                    self._get_nb_interfaces(block_size)
                elif kind == "cables":
                    self._get_nb_cables(block_size)
                break # success, break out of while loop
            except (requests.Timeout, requests.exceptions.HTTPError) as e:
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code != 414:
                    error(f"NetBox API failure at get {kind}:", e)
                else:
                    warning(f"NetBox API failure at get {kind}, will reduce block size and retry:", e)
                    attempts += 1
                    block_size = block_size // 2
            except (pynetbox.core.query.RequestError, pynetbox.core.query.ContentError) as e:
                error(f"NetBox API failure at get {kind}:", e)
        if attempts == max_attempts:
            error(f"NetBox API failure at get {kind}, max attempts reached")


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
                if "base" in interface.type.value: # only ethernet interfaces
                    debug(interface.device, ":", interface, ":", interface.type.value)
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

    def _get_nb_cables(self, block_size):
        size = len(self.nb_net.cable_ids)
        debug(f"Exporting {size} cables to build the network graph, in blocks of {block_size}")
        for i in range(0, size, block_size):
            cables_block = self.nb_net.cable_ids[i:i + block_size]
            for cable in list(self.nb_session.dcim.cables.filter(id=cables_block)):
                self._add_cable_to_graph(cable)


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
        self.platform_map = self._read_platform_map(self.config['platform_map'])
        self.templates = {
            # if _require_map_ is False, attempt to load a template from _path_/<platform>.j2 even if the template is not defined in the platform_map
            'interface_names': {'_path_': f"{self.config['output_format']}/interface_names", '_description_': 'interface name', '_require_map_': False},
            'interface_maps':  {'_path_': f"{self.config['output_format']}/interface_maps",  '_description_': 'interface map', '_require_map_': True},
            'nodes':           {'_path_': f"{self.config['output_format']}/nodes", '_description_': 'node', '_require_map_': False}
        }
        self.files_path = '.'
        if self.config['output_format'] != 'cyjs':
            self.config['format'] = self._read_formats_map(config['formats_map'])


    def _read_platform_map(self, file):
        """Read platform_map from a YAML file to locate template parameters for a range of platforms"""
        print(f"Reading platform map from: {file}")
        # First try to open the file directly
        platform_map = load_yaml_from_file(file, "[PLATFORM]")
        if platform_map is None:
            # Use templates to load the map
            platform_map = self._load_yaml_from_template_file(file, "[PLATFORM]")
        if 'type' in platform_map and platform_map['type'] == 'platform_map' and 'version' in platform_map:
            if platform_map['version'] not in ['v1']:
                error(f"[PLATFORM] Unsupported version of {file} as platform map")
            return platform_map
        error(f"[PLATFORM] Unsupported 'type' in {file}, has to be a 'platform_map' with a compatible 'version'")
        return {}


    def build_from_file(self, file):
        """Build network topology from a CYJS file"""
        self._read_network_graph(file)
        if "name" in self.G.graph.keys():
            self.topology['name'] = self.G.graph["name"]
        self._build_topology()

    def build_from_graph(self, graph):
        """Build network topology from a NetworkX graph"""
        self.G = graph
        if "name" in self.G.graph.keys():
            self.topology['name'] = self.G.graph["name"]
        self._build_topology()


    def _read_formats_map(self, file):
        """Read format_map from a YAML file to initialize output parameters"""
        debug(f"[FORMAT] Reading format map from: {file}")
        formats_map = self._load_yaml_from_template_file(file, "[FORMAT]")
        if 'type' in formats_map and formats_map['type'] == 'formats_map' and 'version' in formats_map:
            if formats_map['version'] not in ['v1']:
                error(f"[FORMAT] Unsupported version of {file} as format map")
            if self.config['output_format'] not in formats_map['formats']:
                error(f"[FORMAT] Output format '{self.config['output_format']}' is not found in {file} under {self.config['templates_path']}")
            return formats_map['formats'][self.config['output_format']]
        error(f"[FORMAT] Unsupported 'type' in {file} under {self.config['templates_path']}, has to be a 'formats_map' with a 'version'")
        return None


    def _read_network_graph(self, file):
        """Read network topology graph from a CYJS file"""
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
        """Append a device node to the topology"""
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
        """Append an interface node to the topology"""
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
        """Initialize emulated interface names for each NOS interface name"""
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
        """Rank nodes by their role and device_index"""
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
        """ Parse graph G into lists of: nodes and links.
        Keep list of interfaces per device in `device_interfaces_map`, and then add them to each device"""
        try:
            for n in self.G.nodes:
                if not self._append_if_node_is_device(n):
                    self._append_if_node_is_interface(n)
            self._initialize_emulated_interface_names()
        except KeyError as e:
            error(f"Incomplete data to build topology, {e} key is missing")

        self._rank_nodes()

    def export_topology(self):
        """Export network topology through Jinja2 templates"""
        if self.topology['name'] is None or len(self.topology['name']) == 0:
            error("Cannot export a topology: missing a name")

        debug(f"Exporting topology. Device role groups: {self.topology['roles']}")
        # Create a directory for output files
        self.files_path = create_output_directory(self.topology['name'], self.config['output_dir'])
        # Generate topology data structure
        self.topology['name'] = self.G.name
        self.topology['rendered_nodes'] = self._render_emulated_nodes()
        self._initialize_emulated_links()
        self._render_topology()

    def _initialize_emulated_links(self):
        """Initialize emulated links"""
        link_id = 0
        for l in self.topology['links']:
            l['id'] = link_id
            l['a']['e_interface'] = self.device_interfaces_map[l['a']['node']][l['a']['interface']]['name']
            l['b']['e_interface'] = self.device_interfaces_map[l['b']['node']][l['b']['interface']]['name']
            l['a']['index'] = self.device_interfaces_map[l['a']['node']][l['a']['interface']]['index']
            l['b']['index'] = self.device_interfaces_map[l['b']['node']][l['b']['interface']]['index']
            link_id += 1


    def _get_platform_template(self, ttype, platform, is_required = False):
        """Get a Jinja2 template for a given type and platform, as well as initialize template params"""
        template = None
        if ttype in self.templates and '_description_' in self.templates[ttype]:
            desc = self.templates[ttype]['_description_']
            params = self._get_platform_template_params(ttype, platform)
            if (params is None or 'template' not in params) and is_required:
                error(f"[TEMPLATE] No mandatory template for {desc} was found for platform '{platform}'")
            if platform in self.templates[ttype]:
                if 'template' not in self.templates[ttype][platform] and 'template' in params:
                    if params['template'] is not None:
                        # Params were just initialized but not the j2 template
                        try:
                            j2file = params['template']
                            template = self.j2env.get_template(j2file)
                            debug(f"[TEMPLATE] Found {desc} template '{j2file}' for platform '{platform}'")
                            self.templates[ttype][platform]['template'] = template
                        except (OSError, jinja2.TemplateError) as e:
                            m = f"[TEMPLATE] Unable to open {desc} template '{j2file}' for platform '{platform}' with path {self.config['templates_path']}."
                            m += f" Reason: {e}"
                            if is_required:
                                if platform == 'default':
                                    error(m)
                                # Render a default template
                                debug(f"{m}. Rendering a default template instead.")
                                template = self._get_platform_template(ttype, "default", True)
                                # Save the default template for this platform
                                self.templates[ttype][platform]['template'] = template
                            else:
                                debug(m)
                else:
                    template = self.templates[ttype][platform]['template']
            elif is_required:
                error(f"[TEMPLATE] Unable to map mandatory {desc} template for platform '{platform}'")
        elif is_required:
            error(f"[TEMPLATE] No such template type as {ttype}")
        return template


    def _get_platform_template_params(self, ttype, platform):
        """Return template parameters for a given type and platform."""
        params = None
        if ttype in self.templates:
            if platform not in self.templates[ttype]:
                params = self._map_platform_to_params(ttype, platform)
                self.templates[ttype][platform] = {
                    'params': params
                }
            else:
                params = self.templates[ttype][platform]['params']
        return params


    def _map_platform_to_params(self, ttype, platform):
        """Map platform name to a node kind and then return a template file path for that kind"""
        default_map = None
        if ttype in self.templates and '_path_' in self.templates[ttype]:
            default_map = {}
            if not self.templates[ttype]['_require_map_']:
                default_map = {
                    'template': f"{self.templates[ttype]['_path_']}/{platform}.j2"
                }
            kind = platform
            if platform in self.platform_map['platforms'] and 'kinds' in self.platform_map['platforms'][platform]:
                platform_kinds = self.platform_map['platforms'][platform]['kinds']
                if self.config['output_format'] in platform_kinds:
                    kind = platform_kinds[self.config['output_format']]
                    debug(f"[MAP] Mapped platform '{platform}' to '{kind}' for {ttype} template")
            else:
                debug(f"[MAP] No mapping for platform '{platform}' was found for '{self.config['output_format']}' output format, will use '{platform}' for {ttype} template")
            return self._map_kind_to_params(ttype, kind)
        return default_map


    def _map_kind_to_params(self, ttype, kind):
        """Map node kind to template parameters"""
        if len(kind) == 0:
            kind = "default"
        kind_map = None
        if ttype in self.templates and '_path_' in self.templates[ttype]:
            desc = self.templates[ttype]['_description_']
            kind_map = {
                'template': None
            }
            if not self.templates[ttype]['_require_map_']:
                kind_map = {
                    'template': f"{self.templates[ttype]['_path_']}/{kind}.j2"
                }
            if self.config['output_format'] in self.platform_map['kinds'] and \
                kind in self.platform_map['kinds'][self.config['output_format']] and \
                ttype in self.platform_map['kinds'][self.config['output_format']][kind]:
                kind_map.update(self.platform_map['kinds'][self.config['output_format']][kind][ttype])
                debug(f"[MAP] Mapped kind '{kind}' to '{kind_map}'")
                return kind_map
            debug(f"[MAP] No {desc} template for kind '{kind}' was found for '{self.config['output_format']}' output format, will use '{kind_map['template']}'")
        return kind_map


    def _get_template_with_file(self, j2file):
        template = None
        try:
            template = self.j2env.get_template(j2file)
            debug(f"Found template {template.filename}")
        except OSError:
            m = f"Unable to open template '{j2file}' with path {self.config['templates_path']}."
            m += " Make sure you have a compatible version of the templates repository."
            error(m)
        except jinja2.TemplateError as e:
            m = f"Unable to open use '{j2file}' with path {self.config['templates_path']}."
            m += f" Reason: {e}."
            error(m)
        return template


    def _load_yaml_from_template_file(self, file, log_context = "[LOAD_YAML]"):
        template = self._get_template_with_file(file)
        try:
            return yaml.load(template.render(self.config), Loader=yaml.SafeLoader)
        except jinja2.TemplateError as e:
            error(f"{log_context} Rendering {file} template as format map: {e}")
        except yaml.scanner.ScannerError as e:
            error(f"{log_context} Can't parse {file} as YAML:", e)
        return None


    def _render_emulated_nodes(self):
        """Render device nodes via Jinja2 templates"""
        topo_nodes = []
        for n in self.topology['nodes']:
            if 'platform' in n.keys():
                p = n['platform']
                params = self._get_platform_template_params('nodes', p)
                if params is not None:
                    n.update(params)

                int_map = self._render_interface_map(n)
                if int_map is not None:
                    n['interface_map'] = int_map

                node_config = self._save_node_configuration(n)
                if node_config is not None:
                    n['startup_config'] = node_config

                template = self._get_platform_template('nodes', p, True)
                if template is not None:
                    try:
                        topo_nodes.append(template.render(n))
                    except jinja2.TemplateError as e:
                        error(f"Rendering {self.templates['nodes']['_description_']} template for platform '{p}': {e}")

        return topo_nodes

    def _render_emulated_interface_name(self, platform, interface, index):
        """Render emulated interface name via Jinja2 templates"""
        # We assume interface with index `0` is reserved for management, and start with `1`
        default_name = f"eth{index+1}"
        template = self._get_platform_template('interface_names', platform, True)
        if template is not None:
            try:
                return template.render({'interface': interface, 'index': index})
            except jinja2.TemplateError as e:
                error("Rendering interface naming J2 template:", e)
        return default_name

    def _render_topology(self):
        """Render network topology via Jinja2 templates"""
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
        """Write network topology to a file"""
        topo_file = f"{self.topology['name']}"
        format_params = self.config['format']
        if 'file_extension' in format_params:
            topo_file += f".{format_params['file_extension']}"
        elif 'file_format' in format_params:
            topo_file += f".{self.config['output_format']}.{format_params['file_format']}"
        try:
            topo_path = f"{self.files_path}/{topo_file}"
            with open(topo_path, "w", encoding="utf-8") as f:
                f.write(topo)
                f.close()
        except OSError as e:
            error(f"Can't write into {topo_path}", e)

        print(f"Created {self.config['output_format']} topology: {topo_path}")

    def _print_motd(self, topo):
        """Print a message on how to use the exported topology"""
        topo_dict = {}
        try:
            f = self.config['format']['file_format'].lower()
            if f == 'json':
                topo_dict = ast.literal_eval(topo)
            elif f == 'yaml':
                topo_dict = yaml.safe_load(topo)
                if 'lab' in topo_dict and 'notes' in topo_dict['lab'] and 'motd' not in topo_dict:
                    # CML
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
        if 'name' in node and node['name'] in self.device_interfaces_map:
            d = node['name']
        else:
            return None
        if 'platform' in node.keys():
            p = node['platform']
            # Interface mapping file for cEOS
            template = self._get_platform_template('interface_maps', p)
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
                        f.close()
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
        if 'startup_config_mode' in self.config['format'] and self.config['format']['startup_config_mode'] == 'file':
            config_file = f"{name}.config"
            config_path = f"{self.files_path}/{config_file}"
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(config)
                    f.close()
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

def parse_args():
    """CLI arguments parser"""
    parser = argparse.ArgumentParser(prog='nrx', description="nrx - network topology exporter by netreplica")
    parser.add_argument('-v', '--version',   action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-d', '--debug',     nargs=0, action=NrxDebugAction, help='enable debug output')
    parser.add_argument('-I', '--init',      nargs=0, action=NrxInitAction, help=f"initialize configuration directory in $HOME/{NRX_CONFIG_DIR} and exit")
    parser.add_argument('-c', '--config',    required=False, help=f"configuration file, default: $HOME/{NRX_CONFIG_DIR}/{NRX_DEFAULT_CONFIG_NAME}",
                                             default=nrx_default_config_path())
    parser.add_argument('-i', '--input',     required=False, help='input source: netbox (default) | cyjs',
                                             default='netbox', type=arg_input_check,)
    parser.add_argument('-o', '--output',    required=False, help='output format: cyjs | clab | cml | graphite | d2 or any other format supported by provided templates')
    parser.add_argument('-a', '--api',       required=False, help='netbox API URL')
    parser.add_argument('-s', '--site',      required=False, help='netbox site to export')
    parser.add_argument('-t', '--tags',      required=False, help='netbox tags to export, for multiple tags use a comma-separated list: tag1,tag2,tag3 (uses AND logic)')
    parser.add_argument('-n', '--noconfigs', required=False, help='disable device configuration export (enabled by default)',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-k', '--insecure',  required=False, help='allow insecure server connections when using TLS',
                                             action=argparse.BooleanOptionalAction)
    parser.add_argument('-f', '--file',      required=False, help='file with the network graph to import')
    parser.add_argument('-M', '--map',       required=False, help=f"file with platform mappings to node parameters (default: {NRX_MAP_NAME} in templates folder)")
    parser.add_argument('-T', '--templates', required=False, help='directory with template files, \
                                                                   will be prepended to TEMPLATES_PATH list \
                                                                   in the configuration file')
    parser.add_argument('-D', '--dir',       required=False, help='save files into specified directory. \
                                                                   nested relative and absolute paths are OK \
                                                                   (topology name is used by default)')

    args = parser.parse_args()
    debug(f"arguments {args}")

    return args


class NrxDebugAction(argparse.Action):
    """Argparse action to turn on debug output"""
    def __call__(self, parser, namespace, values, option_string=None):
        global DEBUG_ON
        DEBUG_ON = True


class NrxInitAction(argparse.Action):
    """Argparse action to initialize configuration directory"""
    def __call__(self, parser, namespace, values, option_string=None):
        # Create a NRX_CONFIG_DIR directory in the user's home directory, or in the current directory if HOME is not set
        config_dir_path = nrx_config_dir()
        print(f"[INIT] Initializing configuration directory in {config_dir_path}")
        config_dir = create_dirs(config_dir_path)
        # Get asset NRX_VERSIONS_NAME with versions compatibility matrix
        versions = get_versions(__version__)
        templates_path = get_templates(versions, config_dir)
        if templates_path is not None:
            print(f"[INIT] Saved templates to: {templates_path}")
        else:
            error("[INIT] Can't download templates")
        default_config_path = get_default_config(versions, config_dir)
        if default_config_path is not None:
            print(f"[INIT] Saved default config to: {default_config_path}. Rename it as {NRX_DEFAULT_CONFIG_NAME} and edit as needed")
        else:
            error("[INIT] Can't download default config")
        sys.exit(0)


def get_versions(nrx_version):
    """Download and parse NRX_VERSIONS_NAME asset file for a specific nrx version"""
    versions_url = f"{NRX_REPOSITORY}/releases/download/{nrx_version}/{NRX_VERSIONS_NAME}"
    try:
        r = requests.get(versions_url, timeout=NRX_REPOSITORY_TIMEOUT)
    except (HTTPError, Timeout, RequestException) as e:
        error(f"[VERSIONS] Downloading versions map from {versions_url} failed: {e}")
    if r.status_code == 200:
        versions = yaml.safe_load(r.text)
        debug(f"[VERSIONS] Retrieved versions map for {nrx_version}:", versions)
        return versions
    error(f"[VERSIONS] Can't download versions map from {versions_url}, status code: {r.status_code}")
    return None


def get_templates(versions, dir_path):
    """Download netreplica/templates version from the versions dict provided as a parameter"""
    if versions is not None and 'templates' in versions:
        templates_version = versions['templates']
        templates_url = f"{NRX_TEMPLATES_REPOSITORY}/archive/refs/tags/{templates_version}.zip"
        try:
            r = requests.get(templates_url, timeout=NRX_REPOSITORY_TIMEOUT)
        except (HTTPError, Timeout, RequestException) as e:
            error(f"[TEMPLATES] Downloading templates from {templates_url} failed: {e}")
        if r.status_code == 200:
            zip_file = f"templates_{templates_version}.zip"
            zip_path = f"{dir_path}/{zip_file}"
            templates_file = f"templates-{templates_version.lstrip('v')}"
            templates_path = f"{dir_path}/{templates_file}"
            try:
                with open(zip_path, 'wb') as f:
                    # Save
                    f.write(r.content)
                    debug(f"[TEMPLATES] Downloaded templates from {templates_url}")
                    # Unzip
                    unzip_file(zip_path, dir_path, "[TEMPLATES]")
                    # Create or replace a symlink to the templates directory
                    update_symlink(f"{dir_path}/templates", templates_file, "[TEMPLATES]")
                    # Remove zip file
                    remove_file(zip_path, "[TEMPLATES]")
                    return templates_path
            except OSError as e:
                error(f"[TEMPLATES] Can't write into {zip_path}", e)
        else:
            error(f"[TEMPLATES] Can't download templates from {templates_url}, status code: {r.status_code}")
    return None


def get_default_config(versions, dir_path):
    """Download NRX_DEFAULT_CONFIG_NAME from the assets of the provided release"""
    if versions is not None and 'nrx' in versions:
        asset_version = versions['nrx']
        asset_url = f"{NRX_REPOSITORY}/releases/download/{asset_version}/{NRX_DEFAULT_CONFIG_NAME}"
        try:
            r = requests.get(asset_url, timeout=NRX_REPOSITORY_TIMEOUT)
        except (HTTPError, Timeout, RequestException) as e:
            error(f"[DEFAULT_CONFIG] Downloading default config from {asset_url} failed: {e}")
        if r.status_code == 200:
            asset_file = f"{NRX_DEFAULT_CONFIG_NAME}-{asset_version.lstrip('v')}"
            asset_path = f"{dir_path}/{asset_file}"
            try:
                with open(asset_path, 'wb') as f:
                    # Save
                    f.write(r.content)
                    debug(f"[DEFAULT_CONFIG] Downloaded default config from {asset_url}")
                    return asset_path
            except OSError as e:
                error(f"[DEFAULT_CONFIG] Can't write into {asset_path}", e)
        else:
            error(f"[DEFAULT_CONFIG] Can't download default config from {asset_url}, status code: {r.status_code}")
    return None


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
        'templates_path': ["./templates", f"{nrx_config_dir()}/templates"],
        'formats_map': NRX_FORMATS_NAME,
        'platform_map': NRX_MAP_NAME,
        'output_dir': '',
        'nb_api_params': {
            'interfaces_block_size':    4,
            'cables_block_size':        64,
        },
    }
    if filename is not None and len(filename) > 0:
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                nb_config = toml.load(f)
                for k in config:
                    if k.upper() in nb_config:
                        config[k] = nb_config[k.upper()]
        except OSError as e:
            if filename == nrx_default_config_path():
                debug("Can't open default configuration file, ignoring.", e)
            else:
                error("Unable to open configuration file:", e)
        except toml.decoder.TomlDecodeError as e:
            error(f"Unable to parse configuration file {filename}: {e}")
        except argparse.ArgumentTypeError as e:
            error(f"Unsupported configuration: {e}")
    path_config_keys = ['templates_path', 'platform_map', 'output_dir']
    for k in path_config_keys:
        if isinstance(config[k], str):
            config[k] = os.path.expandvars(config[k])
        elif isinstance(config[k], list):
            config[k] = [os.path.expandvars(p) for p in config[k]]
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

    if args.map is not None and len(args.map) > 0:
        config['platform_map'] = args.map

    if args.templates is not None and len(args.templates) > 0:
        config['templates_path'].insert(0, args.templates)

    if args.dir is not None and len(args.dir) > 0:
        config['output_dir'] = args.dir

    # Do not export configs for formats that do not support it TODO use startup_config_mode parameter
    if config['output_format'] in ['graphite', 'd2']:
        config['export_configs'] = False

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

    if config['output_format'] != 'cyjs':
        topo.export_topology()
    else:
        if nb_network is None:
            error(f"Only --input netbox is supported for this type of export format: {config['output_format']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
