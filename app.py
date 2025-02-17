import sys
from topo.topo_read import parse_file
from topo.mininet_topo import Topology
from app_detail.server_requests import *
from app_detail.ryu_requests import *

from gui.gui_main import MainWindow

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Host, RemoteController, Node

from PyQt5.QtWidgets import QApplication

import traceback
import time
import os

import requests

CONTROLLER_IP = '127.0.0.1'
CONTROLLER_HTTP_PORT = 8080

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

    if len(sys.argv) != 2:
        if len(sys.argv) == 3 and sys.argv[2] == 'remote':
            use_remote_controller = True
            print('Using remote controller')
        else:
            print("usage: app.py <topology file> [remote]")
            exit(1)
    topo = parse_file(sys.argv[1])

    BROKER_PORT = 1883

    if topo.server == None:
        print("Missing server in topology!")
        exit(1)

    mininet_topo = Topology(topo)
    net = None

    if not os.path.isdir('./logs'):
        os.makedirs('./logs')

    try:
        if not use_remote_controller:
            net = Mininet(mininet_topo)
        else:
            net = Mininet(mininet_topo, controller=lambda name: RemoteController(name, ip=CONTROLLER_IP, port=6633))
        
        mininet_topo.create_ip_map(net)

        net.addNAT(name='nat0').configDefault()
        net.start()
        net.waitConnected()

        nat_node: Node = net.getNodeByName('nat0')
        server_node: Host = net.getNodeByName(topo.server.name)

        BROKER_ADDRESS = nat_node.IP()

        controller_url = f'http://{CONTROLLER_IP}:{CONTROLLER_HTTP_PORT}'

        if use_remote_controller:
            send_server_ip(controller_url, server_node.IP())
            send_nat_ip(controller_url, BROKER_ADDRESS)

        print("Testing whether server can reach all hosts")
    
        for host in topo.hosts:
            print(f'Testing host {host.name}')
            host_node: Host = net.getNodeByName(host.name)
            if net.ping([server_node, host_node]) > 0:
                print("Ping failed")
                exit(1)

        broker_exports = f'export MQTT_ADDRESS={BROKER_ADDRESS} && export MQTT_PORT={BROKER_PORT}'
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

        add_sensor(server_url, 'H1', 'temp', 'first_room_temp')
        add_sensor(server_url, 'H2', 'temp', 'second_room_temp')
        add_sensor(server_url, 'H3', 'temp', 'third_room_temp')
        add_actuator(server_url, 'H2', 'heater', 'second_room_heater')
        add_controller(server_url, 'test_controller', 'test')

        add_sensor(server_url, 'H3', 'seismic', 'seismic_sensor')
        
        app = QApplication(sys.argv)
        sensors = [('H1', 'first_room_temp'), ('H2', 'second_room_temp'), ('H3', 'third_room_temp')]
        heaters = [('H2', 'second_room_heater')]
        connection_list = [(0, 0)]
        window = MainWindow(sensor_list=sensors, 
                            open_sensors=[0, 2], 
                            heaters=heaters, 
                            connection_list=connection_list,
                            server_url=server_url)
        window.show()
        app.exec_()

        print("Shutting down servers...")

        print(get_actuator_status(server_url, 'H2', 'second_room_heater'))
        print(get_sensor_data(server_url, 'H3', 'seismic_sensor'))

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