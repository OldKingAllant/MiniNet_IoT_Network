import paho.mqtt.client as mqtt

import os
import sys
import json
import time

import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if os.environ.get('MQTT_ADDRESS') == None or os.environ.get('MQTT_PORT') == None:
    print('Env. variables for MQTT do not exist', flush=True, file=sys.stdout)
    exit(1)

if os.environ.get('SERVER_ID') == None:
    print('Env. variables SERVER_ID does not exist', flush=True, file=sys.stdout)
    exit(1)

if os.environ.get('MODULE_NAME') == None:
    print('Env. variables MODULE_NAME does not exist', flush=True, file=sys.stdout)
    exit(1)

module_name = os.environ['MODULE_NAME']
server_id = os.environ.get('SERVER_ID')
mqtt_client_id = f'{server_id}_{module_name}'
mqtt_topic = f'{server_id}/{module_name}'
mqtt_control_topic = f'{server_id}/{module_name}_stop'

log_file = open(f'./logs/{server_id}_{module_name}_log.txt', 'w')

print(mqtt_control_topic, file=log_file)

running: bool = True

def on_connect(client: mqtt.Client, userdata, flags, reason_code):
    print('Connected', flush=True, file=log_file)
    client.subscribe(mqtt_control_topic)

def on_message(client, userdata, msg: mqtt.MQTTMessage):
    global running, log_file
    if msg.topic == mqtt_control_topic and str(msg.payload.decode('utf-8')).upper() == "STOP":
        print("Received disconnect command", file=log_file)
        running = False

client = mqtt.Client(mqtt_client_id, clean_session=True)

client.on_connect = on_connect
client.on_message = on_message
client.connect(os.environ['MQTT_ADDRESS'], int(os.environ['MQTT_PORT']))

client.loop_start()

while running:
    time.sleep(5)
    client.publish(mqtt_topic, json.dumps({'new_temp': 10.0}))

client.loop_stop()
client.disconnect()

print("DISCONNECTED", file=log_file)