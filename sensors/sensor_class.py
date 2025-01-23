import paho.mqtt.client as mqtt

import os
import sys

class Sensor:
    def __init__(self):
        if os.environ.get('MQTT_ADDRESS') == None or os.environ.get('MQTT_PORT') == None:
            print('Env. variables for MQTT do not exist', flush=True, file=sys.stdout)
            exit(1)

        if os.environ.get('SERVER_ID') == None:
            print('Env. variables SERVER_ID does not exist', flush=True, file=sys.stdout)
            exit(1)

        if os.environ.get('MODULE_NAME') == None:
            print('Env. variables MODULE_NAME does not exist', flush=True, file=sys.stdout)
            exit(1)

        self.module_name = os.environ['MODULE_NAME']
        self.server_id = os.environ.get('SERVER_ID')
        self.mqtt_client_id = f'{self.server_id}_{self.module_name}'
        self.mqtt_topic = f'{self.server_id}/{self.module_name}'
        self.mqtt_control_topic = f'{self.server_id}/{self.module_name}_control'
        self.log_file = open(f'./logs/{self.server_id}_{self.module_name}_log.txt', 'w')
        self.client = mqtt.Client(self.mqtt_client_id, clean_session=True)
        self.connected = False
        return 
    
    def set_on_message(self, on_message):
        self.client.on_message = on_message
    
    def connect(self):
        def on_connect(client: mqtt.Client, userdata, flags, reason_code):
            print('Connected', flush=True, file=self.log_file)
            client.subscribe(self.mqtt_control_topic)

        self.client.on_connect = on_connect
        self.client.connect(os.environ['MQTT_ADDRESS'], int(os.environ['MQTT_PORT']))
        self.connected = True

    def start(self):
        if not self.connected:
            raise Exception("Not connected to broker")
        self.client.loop_start()

    def stop(self):
        if not self.connected:
            raise Exception("Not connected to broker")
        self.client.loop_stop()

    def disconnect(self):
        if not self.connected:
            raise Exception("Not connected to broker")
        self.client.disconnect()

    def send(self, data):
        if not self.connected:
            raise Exception("Not connected to broker")
        self.client.publish(self.mqtt_topic, data)

    