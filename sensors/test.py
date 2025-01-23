import paho.mqtt.client as mqtt

import os
import sys
import json
import time

import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

module_name = 'test'
server_id = 'test_server'
mqtt_client_id = f'{server_id}_{module_name}'
mqtt_topic = f'{server_id}/{module_name}'
mqtt_control_topic = f'{server_id}/{module_name}_stop'

running = True

def on_connect(client: mqtt.Client, userdata, flags, reason_code):
    print('Connected', flush=True, file=sys.stdout)
    client.subscribe(mqtt_control_topic)

def on_message(client, userdata, msg: mqtt.MQTTMessage):
    if msg.topic == mqtt_control_topic and str(msg.payload).upper() == "STOP":
        running = False

client = mqtt.Client(mqtt_client_id, clean_session=True)

client.on_connect = on_connect
client.on_message = on_message
client.connect('127.0.0.1', 1883)

client.loop_start()

while running:
    time.sleep(5)
    logger.debug('PUBLISH')
    print('PUBLISH')
    client.publish(mqtt_topic, json.dumps({'new_temp': 10.0}))

client.loop_stop()
client.disconnect()