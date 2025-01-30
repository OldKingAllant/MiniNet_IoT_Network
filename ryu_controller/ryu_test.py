from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.node import Node

import requests
import json

def send_server_ip(controller_url: str, ip):
    body = json.dumps( {'ip_address': ip} )
    res = requests.post(f'{controller_url}/set_server_address', headers={'ContentType': 'application/json'}, data=body)
    if res.status_code != 200:
        print(f'Set server ip failed: {res.json()}')
    return

def send_nat_ip(controller_url: str, ip):
    body = json.dumps( {'ip_address': ip} )
    res = requests.post(f'{controller_url}/set_nat_address', headers={'ContentType': 'application/json'}, data=body)
    if res.status_code != 200:
        print(f'Set server ip failed: {res.json()}')
    return

net = Mininet()

CONTROLLER_IP = '127.0.0.1'
CONTROLLER_HTTP_PORT = 8080

net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

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

net.addNAT(name='nat0')

net.start()

server_node: Node = net.getNodeByName('H1')
server_ip = server_node.IP()
nat_node: Node = net.getNodeByName('nat0')
nat_ip = nat_node.IP()

controller_url = f'http://{CONTROLLER_IP}:{CONTROLLER_HTTP_PORT}'

send_server_ip(controller_url, server_ip)
send_nat_ip(controller_url, nat_ip)

CLI(net)

net.stop()