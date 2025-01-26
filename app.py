import sys
from topo.topo_read import parse_file
from topo.mininet_topo import Topology
from app_detail.server_requests import *

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Host, RemoteController

import traceback
import json
import typing
import time
import socket
import os

import requests

def waitfor_beat(server_url: str, max_attempts: int):
    while max_attempts > 0:
        time.sleep(1)
        try:
            requests.get(f'{server_url}/heartbeat')
            return True
        except:
            max_attempts -= 1
    return False

if __name__ == '__main__':
    use_remote_controller = False

    if len(sys.argv) != 4:
        if len(sys.argv) == 5 and sys.argv[4] == 'remote':
            use_remote_controller = True
            print('Using remote controller')
        else:
            print("usage: app.py <topology file> <broker_addr> <broker_port> [remote]")
            exit(1)
    topo = parse_file(sys.argv[1])

    try:
        socket.inet_aton(sys.argv[2])
    except:
        print("Invalid broker address, expected valid IPv4")
        exit(1)

    broker_port = 0
    try:
        broker_port = int(sys.argv[3])
        if broker_port < 0 or broker_port >= 2**16:
            raise Exception()
    except:
        print("Invalid broker port")
        exit(1)

    if topo.server == None:
        print("Missing server!")
        exit(1)

    mininet_topo = Topology(topo)
    net = None

    if not os.path.isdir('./logs'):
        os.makedirs('./logs')

    try:
        if not use_remote_controller:
            net = Mininet(mininet_topo)
        else:
            net = Mininet(mininet_topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633))
        mininet_topo.create_ip_map(net)
        net.addNAT().configDefault()

        #if use_remote_controller:
        #    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

        net.start()
        net.waitConnected()

        server_node: Host = net.getNodeByName(topo.server.name)

        print("Testing whether server can reach all hosts")
    
        for host in topo.hosts:
            print(f'Testing host {host.name}')
            host_node: Host = net.getNodeByName(host.name)
            if net.ping([server_node, host_node]) > 0:
                print("Ping failed")
                exit(1)

        broker_exports = f'export MQTT_ADDRESS={sys.argv[2]} && export MQTT_PORT={broker_port}'
        main_server_cmd = f'{broker_exports} && export FLASK_APP=./server/main_server.py && flask run --host=0.0.0.0 &> ./logs/iot_server.txt'

        server_url = f'http://{server_node.IP()}:5000'
        conn = server_node.popen(main_server_cmd, shell=True)

        print("Starting host servers")

        server_conns = []

        for host in topo.hosts:
            host_node: Host = net.getNodeByName(host.name)
            server_id = f'export SERVER_ID={host.name}'
            cmd = f'{server_id} && {broker_exports} && export FLASK_APP=./server/host_server.py && flask run --host=0.0.0.0 &> ./logs/{host.name}.txt'
            server_conns.append(host_node.popen(cmd, shell=True))

        if not waitfor_beat(server_url, 10):
            print("Cannot connect to server")
            net.stop()
            exit(1)

        publish_hosts(server_url, mininet_topo.ip_map)
        remove_hosts(server_url, [topo.server.name])

        add_sensor(server_url, 'H1', 'temp', 'temp_sensor')
        add_sensor(server_url, 'H2', 'temp', 'temp_sensor')
        add_actuator(server_url, 'H3', 'heater', 'h3_heater')
        add_controller(server_url, 'test_controller', 'test')
        
        CLI(net)

        print("Shutting down servers...")

        print(get_actuator_status(server_url, 'H3', 'h3_heater'))

        remove_all_sensors(server_url)
        remove_all_actuators(server_url)
        remove_all_controllers(server_url)
        
        conn.terminate()

        for curr_con in server_conns:
            curr_con.terminate()

        net.stop()
    except:
        print(traceback.format_exc())
        print("Exception occurred")
        if net != None:
            net.stop()
        exit(1)