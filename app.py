import sys
from topo.topo_read import parse_file
from topo.mininet_topo import Topology

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Host

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

def publish_hosts(server_url: str, host_list: typing.Dict[str, str]):
    host_str = json.dumps(host_list)
    res = requests.post(f'{server_url}/devices', headers={'Content-Type': 'application/json'}, data=host_str)
    if res.status_code != 200:
        print(f'Host publish failed: {res.json()}')
        return False
    return True

def remove_hosts(server_url: str, host_list: typing.List[str]):
    host_str = json.dumps(host_list)
    res = requests.delete(f'{server_url}/devices', params={'devs': host_str})
    if res.status_code != 200:
        print(f'Host delete failed: {res.json()}')
        return False 
    return True

def add_sensor(server_url: str, dev_id: str, module: str, name: str):
    data = json.dumps({'module': module, 'instance_id': name})
    res = requests.post(f'{server_url}/dev/{dev_id}/sensors', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Create sensor failed: {res.json()}')
        return False 
    return True

def remove_all_sensors(server_url: str):
    res = requests.delete(f'{server_url}/dev/sensors/delete_all')
    if res.status_code != 200:
        print(f'Remove sensors failed: {res.json()}')
        return False 
    return True

def get_all_sensors(server_url: str):
    res = requests.get(f'{server_url}/dev/sensors/get_all')
    if res.status_code != 200:
        return None 
    return res.json()['sensors']

def stop_sensor(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.put(f'{server_url}/dev/{host_id}/sensor_stop', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Stop sensor failed: {res.json()}')
        return False 
    return True

def start_sensor(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.put(f'{server_url}/dev/{host_id}/sensor_start', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Start sensor failed: {res.json()}')
        return False 
    return True

def add_actuator(server_url: str, dev_id: str, module: str, name: str):
    data = json.dumps({'module': module, 'instance_id': name})
    res = requests.post(f'{server_url}/dev/{dev_id}/actuators', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Create actuator failed: {res.json()}')
        return False 
    return True

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: app.py <topology file> <broker_addr> <broker_port>")
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
        net = Mininet(mininet_topo)
        mininet_topo.create_ip_map(net)
        net.addNAT().configDefault()
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

        time.sleep(5)
        start_sensor(server_url, 'H1', 'temp_sensor')

        #time.sleep(10)
        #stop_sensor(server_url, 'H1', 'temp_sensor')
        
        CLI(net)

        print("Shutting down servers...")

        print(get_all_sensors(server_url))
        remove_all_sensors(server_url)

        """res = requests.post(f'http://{server_node.IP()}:5000/shutdown')

        if res.status_code != 200:
            print("Server was propably already down")"""
        
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