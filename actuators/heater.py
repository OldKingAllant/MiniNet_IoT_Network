from actuator_class import Actuator

import paho.mqtt.client as mqtt

import time
import json

actuator = Actuator()

running: bool = True
stop: bool = True

def handle_control(client, userdata, msg: mqtt.MQTTMessage):
    global running, actuator, stop
    message = str(msg.payload.decode('utf-8')).upper()
    if message == "STOP":
        print("Received stop command", file=actuator.log_file, flush=True)
        stop = True
    if message == "START":
        print("Received start command", file=actuator.log_file, flush=True)
        stop = False
    if message == "DISCONNECT":
        print("Received disconnect command", file=actuator.log_file)
        running = False


actuator.set_control(handle_control)
actuator.connect()
actuator.start()

while running:
    time.sleep(5)
    actuator.update_status(json.dumps({'is_on': not stop}))

actuator.stop()
actuator.disconnect()