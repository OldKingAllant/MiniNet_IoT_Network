from controller_class import Controller

from paho.mqtt.client import MQTTMessage

import json
import traceback

controller = Controller()

controller.connect(['H1/first_room_temp'])

def recv_message(controller: Controller, msg: MQTTMessage):
    content = msg.payload.decode()
    print(f'{msg.topic} -> {content}', file=controller.log_file, flush=True)
    if msg.topic == 'H1/first_room_temp':
        data = json.loads(content)
        temp = data['new_temp']
        if temp >= 10.0:
            print('Start heater', file=controller.log_file, flush=True)
            controller.send_control('H2/second_room_heater', 'START')
        else:
            print('Stop heater', file=controller.log_file, flush=True)
            controller.send_control('H2/second_room_heater', 'STOP')
    return

controller.loop(recv_message)