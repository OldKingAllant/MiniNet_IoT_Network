from controller_class import Controller

from paho.mqtt.client import MQTTMessage

import json
import traceback

controller = Controller()

controller.connect(['H1/temp_sensor'])

def recv_message(controller: Controller, msg: MQTTMessage):
    content = msg.payload.decode()
    print(f'{msg.topic} -> {content}', file=controller.log_file, flush=True)
    if msg.topic == 'H1/temp_sensor':
        data = json.loads(content)
        temp = data['new_temp']
        if temp >= 10.0:
            print('Start heater', file=controller.log_file, flush=True)
            controller.send_control('H3/h3_heater', 'START')
        else:
            print('Stop heater', file=controller.log_file, flush=True)
            controller.send_control('H3/h3_heater', 'STOP')
    return

controller.loop(recv_message)