from controller_class import Controller

from paho.mqtt.client import MQTTMessage

controller = Controller()

controller.connect(['H1/temp_sensor'])

def recv_message(controller: Controller, msg: MQTTMessage):
    content = msg.payload.decode()
    print(f'{msg.topic} -> {content}', file=controller.log_file, flush=True)
    return

controller.loop(recv_message)