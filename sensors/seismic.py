import paho.mqtt.client as mqtt

import json
import time
import datetime
import numpy as np

from sensor_class import Sensor

sensor = Sensor()

running: bool = True
stop: bool = False

MODE_0 = 0
MODE_1 = 1

current_mode: int = MODE_1

def on_message(client, userdata, msg: mqtt.MQTTMessage):
    global current_mode
    message = str(msg.payload.decode('utf-8')).upper()
    print(f'Received message: {message}')
    if message == 'MODE_0':
        current_mode = MODE_0
    elif message == 'MODE_1': 
        current_mode = MODE_1
    else:
        current_mode = MODE_0

sensor.set_on_message(on_message)
sensor.connect()
sensor.start()

while running:
    time.sleep(5)
    sensor.update_status(json.dumps({'mode': current_mode}))
    if not stop:
        timestamp = datetime.datetime.now().timestamp()
        intensity = np.random.randint(0, 10) 
        acc_x = np.random.randint(0, 5)
        acc_y = np.random.randint(0, 5)
        acc_z = np.random.randint(0, 5)
        
        if current_mode == MODE_0:
            sensor.send_data(json.dumps({'intensity': intensity, 'mode': current_mode, 'timestamp': timestamp}))
        else:
            sensor.send_data(json.dumps({'accelleration': [acc_x, acc_y, acc_z], 'mode': current_mode, 'timestamp': timestamp}))

sensor.stop()
sensor.disconnect()