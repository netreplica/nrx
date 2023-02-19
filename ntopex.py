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
        self.nb_site = self.nb_session.dcim.sites.get(name=config['export_site'])
        debug(f"returned site data {self.nb_site}")
        if self.nb_site is None:
            print(f"No data found for a site {config['export_site']}")
        else:
            print(f"Exporting {config['export_site']} site from NetBox at {config['nb_api_url']}")
            self._get_nb_device_info()
            self._build_network_graph()


    def _get_nb_device_info(self):
        for device in list(self.nb_session.dcim.devices.filter(site_id=self.nb_site.id, role=self.config['export_device_roles'])):
            d = {
                "id": device.id,
                "type": "device",
                "name": device.name,
                "node_id": -1,
            }
            self.nb_net.nodes.append(d)
            d["node_id"] = len(self.nb_net.nodes) - 1
            self.nb_net.devices.append(d)
            self.nb_net.device_ids.append(
                device.id)  # index of the device in the devices list will match its ID index in device_ids list

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
        for cable in list(self.nb_session.dcim.cables.filter(id=self.nb_net.cable_ids)):
            if len(cable.a_terminations) == 1 and len(cable.b_terminations) == 1:
                int_a = cable.a_terminations[0]
                int_b = cable.b_terminations[0]
                if isinstance(int_a, pynetbox.models.dcim.Interfaces) and isinstance(int_b,
                                                                                     pynetbox.models.dcim.Interfaces):
                    debug("{}:{} <> {}:{}".format(int_a.device, int_a, int_b.device, int_b))
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

    def export_graph_gml(self):
        nx.write_gml(self.G, self.config['export_site'] + ".gml")
        print(f'Graph GML saved to {self.config["export_site"]}.gml')

    def export_graph_json(self):
        cyjs = nx.cytoscape_data(self.G)
        with open(self.config['export_site'] + ".cyjs", 'w', encoding='utf-8') as f:
            json.dump(cyjs, f, indent=4)
        print(f'Graph JSON saved to {self.config["export_site"]}.cyjs')


def load_config(filename):
    config = {
        'nb_api_url': '',
        'nb_api_token': '',
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
        except OSError as e:
            error(f"Unable to open configuration file {filename}: {e}")
        except toml.decoder.TomlDecodeError as e:
            error(f"Unable to parse configuration file {filename}: {e}")

    config['nb_api_url'] = os.getenv('NB_API_URL', config['nb_api_url'])
    config['nb_api_token'] = os.getenv('NB_API_TOKEN', config['nb_api_token'])

    return config

def main():

    # CLI arguments parser
    parser = argparse.ArgumentParser(prog='netopex.py', description='Network Topology Exporter')
    parser.add_argument('-c', '--config', required=False, help=f"configuration file")
    parser.add_argument('-a', '--api', required=False, help='NetBox API URL')
    parser.add_argument('-s', '--site', required=False, help='NetBox Site to export')
    parser.add_argument('-d', '--debug', required=False, help='enable debug output', action=argparse.BooleanOptionalAction)

    # Common parameters
    args = parser.parse_args()

    global debug_on
    debug_on = (args.debug == True)
    debug(f"arguments {args}")

    config = load_config(args.config)

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
    nb_network.export_graph_gml()
    nb_network.export_graph_json()

    return 0


if __name__ == '__main__':
    sys.exit(main())
