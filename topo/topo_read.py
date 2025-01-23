from typing import List, Any, Optional
import sys
import re


def read_file(file_path) -> List[str]:
    """
    Reads the entire file and puts the lines
    in a list

    :param str file_path: Complete path to file
    """
    lines: List[str] = []
    with open(file_path) as open_file:
        lines.extend(list(map(lambda line: line.rstrip(), open_file.readlines())))
    return lines

class Host:
    def __init__(self):
        self.name: str = str()

    def __str__(self):
        return f'{self.name}'

class Switch:
    def __init__(self):
        self.name: str = str()

    def __str__(self):
        return f'{self.name}'

class Link:
    def __init__(self):
        self.h1: str = str()
        self.h2: str = str()

    def __str__(self):
        return f'{self.h1}-{self.h2}'
    
class Server:
    def __init__(self):
        self.name: str = str()

class TopologyRepr:
    def __init__(self):
        self.hosts: List[Host] = []
        self.switches: List[Switch] = []
        self.links: List[Link] = []
        self.server: Optional[Server] = None

    def __str__(self):
        return f'Hosts: {[str(host) for host in self.hosts]}\nSwitches: {[str(switch) for switch in self.switches]}\nLinks: {[str(link) for link in self.links]}'

def create_host(config) -> Host:
    if len(config) != 2:
        return None
    new_host = Host()
    new_host.name = config[1]
    return new_host

def create_switch(config) -> Switch:
    if len(config) != 2:
        return None
    new_switch = Switch()
    new_switch.name = config[1]
    return new_switch

def create_link(config) -> Link:
    if len(config) != 3:
        return None
    new_link = Link()
    new_link.h1 = config[1]
    new_link.h2 = config[2]
    return new_link

def create_server(config) -> Server:
    if len(config) != 2:
        return None 
    server = Server()
    server.name = config[1]
    return server

def parse_line(line) -> Any:
    components = re.split('\s+', line)

    if len(components) == 0:
        return None
    
    upper_name = components[0].upper().rstrip()

    if upper_name == "HOST":
        return create_host(components)
    if upper_name == "SWITCH":
        return create_switch(components)
    if upper_name == "LINK":
        return create_link(components)
    if upper_name == "SERVER":
        return create_server(components)
    
    return None

def parse_file(file_path) -> TopologyRepr:
    lines = read_file(file_path)
    my_topology = TopologyRepr()
    
    for line in lines:
        component = parse_line(line)
        type_name = type(component).__name__
        
        if type_name == "Host":
            my_topology.hosts.append(component)
        if type_name == "Switch":
            my_topology.switches.append(component)
        if type_name == "Link":
            my_topology.links.append(component)
        if type_name == "Server" and my_topology.server == None:
            my_topology.server = component

    return my_topology

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Missing file name")
        exit(1)
    topo = parse_file(sys.argv[1])
    print(topo)