from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController

net = Mininet()

net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

net.addHost('H1')
net.addHost('H2')
net.addHost('H3')

net.addSwitch('S1')
net.addSwitch('S2')
net.addSwitch('S3')

net.addSwitch('S4')

net.addLink('H1', 'S1')
net.addLink('H2', 'S2')
net.addLink('H3', 'S3')

net.addLink('S1', 'S4')
net.addLink('S2', 'S4')
net.addLink('S3', 'S4')

net.start()

CLI(net)

net.stop()