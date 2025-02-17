import paho.mqtt.client as mqtt

import json
import time
import datetime

from sensor_class import Sensor

sensor = Sensor()

running: bool = True
stop: bool = False

def on_message(client, userdata, msg: mqtt.MQTTMessage):
    global running, sensor, stop
    message = str(msg.payload.decode('utf-8')).upper()
    if message == "STOP":
        print("Received stop command", file=sensor.log_file, flush=True)
        stop = True
    if message == "START":
        print("Received start command", file=sensor.log_file, flush=True)
        stop = False
    if message == "DISCONNECT":
        print("Received disconnect command", file=sensor.log_file)
        running = False

sensor.set_on_message(on_message)
sensor.connect()
sensor.start()

step_increment = 1.0
curr_temp = 10.0

while running:
    time.sleep(5)
    sensor.update_status(json.dumps({'is_on': not stop}))
    if not stop:
        sensor.send_data(json.dumps({'new_temp': curr_temp, 'timestamp': datetime.datetime.now().timestamp()}))
        if curr_temp >= 30.0:
            step_increment = -1.0
        elif curr_temp <= 10.0:
            step_increment = 1.0
        curr_temp += step_increment

sensor.stop()
sensor.disconnect()