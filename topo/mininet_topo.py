from topo.topo_read import TopologyRepr
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node

import typing

class Topology(Topo):
    def __init__(self, topo):
        Topo.__init__(self)
        self.load_config(topo)
        self.ip_map: typing.Dict[str, str] = {}

    def load_config(self, topo: TopologyRepr):
        self.addHost(topo.server.name)
        for host in topo.hosts:
            self.addHost(host.name)
        for switch in topo.switches:
            self.addSwitch(switch.name)
        for link in topo.links:
            self.addLink(link.h1, link.h2)
        return self
    
    def create_ip_map(self, net: Mininet):
        for node_name in self.nodes():
            node: Node = net.getNodeByName(node_name)
            if type(node).__name__ == "Host":
                self.ip_map[node_name] = node.IP()