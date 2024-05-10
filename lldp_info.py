"""
This program displays a graphical representation of a given network.

Functionality:
1. Enables and runs LLDP (Link-Layer Discovery Protocol) over input routers.
2. Gathers LLDP connectivity information from the pre-configured routers.
3. Displays the network graph including the routers and their connections.

Author:
- Diego Guzman <dguzman1@terpmail.umd.edu>
"""

import json as js
import argparse
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from graphviz import Graph

DEFAULT_JSON_PATH = 'Json_files/default_network_config.json'

def enable_lldp(device):
    """
    Enables LLDP on the device.

    Args:
        device (Device): Juniper device object.
    
    Raises:
        Exception: If LLDP cannot be enabled successfully.
    """
    device.bind(conf=Config)
    device.conf.load('set protocols lldp interface all')
    success = device.conf.commit()
    if success is True:
        print("Successfully enabled LLDP!")
    else:
        raise Exception("LLDP could not get enabled")

def gather_lldp_info(device,lldp_prev):
    """
    Gathers LLDP information from the device.

    Args:
        device (Device): Juniper device object.
        lldp_prev (set): Set containing previously gathered LLDP information.
    
    Returns:
        list: List of tuples containing LLDP information.
    """
    lldp_neighbors = device.rpc.get_lldp_neighbors_information()
    lldp_info = []
    for neighbor in lldp_neighbors.findall(".//lldp-neighbor-information"):
        local_interface = neighbor.findtext("lldp-local-interface")
        ip = device.rpc.get_interface_information(interface_name=local_interface).\
        findtext(".//ifa-destination").strip()
        local_device = device.rpc.get_software_information().findtext(".//host-name")
        neighbor_device = neighbor.findtext("lldp-remote-system-name")
        neighbor_interface = neighbor.findtext("lldp-remote-port-description")
        if (neighbor_device, local_device, neighbor_interface, ip, local_interface) in lldp_prev:
            # connection has already been accounted for so we skip (avoids redundant connections)
            continue
        lldp_info.append((local_device, neighbor_device, local_interface, ip, neighbor_interface))
        lldp_prev.add((local_device, neighbor_device, local_interface, ip, neighbor_interface))
    return lldp_info

def draw_network_graph(lldp_info):
    """
    Draws network graph using LLDP information.

    Args:
        lldp_info (list): List of tuples containing LLDP information.
    """
    graph = Graph()

    for local_device, neighbor_device, local_interface, ip, neighbor_interface in lldp_info:
        graph.node(local_device)
        graph.node(neighbor_device)
        graph.edge(local_device, neighbor_device, \
                   label=f"{local_interface}\n{ip}\n{neighbor_interface}")

    graph.render("network_graph", format="png", view=True)

def load_json(file_path):
    """
    Loads JSON file.

    Args:
        file_path (str): Path to the JSON file.
    
    Returns:
        dict: Dictionary containing the loaded JSON data.
    """
    with open(file_path, "r") as file:
        document = js.load(file)
    return document

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        Namespace: Namespace containing parsed arguments.
    """
    parser=argparse.ArgumentParser(
           description='''This program displays a graphical representation of a given network.''',
           epilog='''Author: Diego Guzman''')
    parser.add_argument('-f', '--file', type=str, default=DEFAULT_JSON_PATH, \
                        help='specify json file path where router information is stored')
    return parser.parse_args()

def main():
    """
    Main function.
    """
    lldp_info = []
    lldp_prev = set()
    router_ips_file_path = parse_arguments().file
    print("Initializing execution...")

    try:
        router_ips = load_json(router_ips_file_path)

        for router in router_ips:
            print(f"\n\nEstablishing connection with ip {router['ip']}...")

            with Device(host=router["ip"], user=router["user"], password=router["password"]) as dev:
                dev.open()
                print("Connection successful!\nEnabling LLDP (Link-Layer Discovery Protocol)...")
                enable_lldp(dev)
                print("Gathering LLDP connectivity information...")
                lldp_info.extend(gather_lldp_info(dev, lldp_prev))
                print("Successfully gathered LLDP connectivity information!")
    except Exception as err:
        print("An error has occurred: ", err)
        exit()

    print("\nDisplaying network graph...")
    draw_network_graph(lldp_info)
    print("Finalizing successful execution...")

if __name__ == "__main__":
    main()
