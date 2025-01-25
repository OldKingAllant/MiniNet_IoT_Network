import paho.mqtt.client as mqtt

import os
import sys

import typing

class Controller:
    def __init__(self):
        if os.environ.get('MQTT_ADDRESS') == None or os.environ.get('MQTT_PORT') == None:
            print('Env. variables for MQTT do not exist', flush=True, file=sys.stdout)
            exit(1)

        if os.environ.get('MODULE_NAME') == None:
            print('Env. variables MODULE_NAME does not exist', flush=True, file=sys.stdout)
            exit(1)

        self.module_name = os.environ['MODULE_NAME']
        self.mqtt_client_id = f'controller_{self.module_name}'
        self.log_file = open(f'./logs/controller_{self.module_name}_log.txt', 'w')
        self.client = mqtt.Client(self.mqtt_client_id, clean_session=True)
        self.connected = False
        self.message_callback = None
        return 
    
    def connect(self, sensor_list: typing.List[str]):
        def on_connect(client: mqtt.Client, userdata, flags, reason_code):
            print('Connected', flush=True, file=self.log_file)
            for sensor in sensor_list:
                client.subscribe(sensor)

        self.client.on_connect = on_connect
        self.client.connect(os.environ['MQTT_ADDRESS'], int(os.environ['MQTT_PORT']))
        self.connected = True

    def send_control(self, sensor: str, message: typing.Any):
        return

    def loop(self, message_callback: typing.Callable[[typing.Any, mqtt.MQTTMessage], typing.Any]):
        self.message_callback = message_callback

        def on_message(client: mqtt.Client, controller: Controller, msg: mqtt.MQTTMessage):
            controller.message_callback(controller, msg)
            return
        
        self.client.user_data_set(self)
        self.client.on_message = on_message
        self.client.loop_forever()
        return