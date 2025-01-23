from flask.app import Flask
from flask.app import request

from flask_mqtt import Mqtt
from flask_mqtt import MQTT_ERR_SUCCESS

import typing
import json
import logging
import sys
import os

import requests

app = Flask(__name__)

sys.stderr = sys.stdout

app.logger.setLevel(logging.DEBUG)

"""try:
    app.logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
except:
    print("Error occurred while creating console logger", flush=True, file=sys.stdout)"""

if os.environ.get('MQTT_ADDRESS') == None or os.environ.get('MQTT_PORT') == None:
    app.logger.fatal(f'Env. variables for MQTT do not exist')
    exit(1)

app.config['MQTT_CLIENT_ID'] = 'MAIN_SERVER'
app.config['MQTT_BROKER_URL'] = os.environ['MQTT_ADDRESS']
app.config['MQTT_BROKER_PORT'] = int(os.environ['MQTT_PORT'])

mqtt = Mqtt(app)

devices: typing.Dict[str, str] = {}

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    app.logger.info(f'Connected to Mqtt broker')

@app.route("/heartbeat")
def heartbeat():
    return {'status': 'E_OK'}, 200

@app.post("/devices")
def add_devices():
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /devices content')
        return {'status': 'E_CONTENT'}, 400
    parsed = request.get_json()

    if type(parsed) != type({}):
        app.logger.error(f'Invalid POST /devices json type: {type(parsed).__name__}')
        return {'status': 'E_LIST'}, 400

    for host in parsed.keys():
        if devices.get(host) == None:
            devices[host] = parsed.get(host)

    app.logger.info('Updated devices')
    return {'status': 'E_OK'}, 200

@app.get("/devices")
def get_devices():
    return {'status': 'E_OK', 'devs': json.dumps(devices)}, 200

@app.delete("/devices")
def del_devices():
    if request.args.get('devs') == None:
        app.logger.error(f'Invalid DELETE /devices param')
        return {'status': 'E_CONTENT'}, 400

    try:
        dev_str = request.args.get('devs', type=str)
        devs = json.loads(dev_str)
        if type(devs) != type([]):
            return {'status': 'E_PARAM'}
        for dev in devs:
            devices.pop(dev, None)
    except:
        return {'status': 'E_PARAM'}
    return {'status': 'E_OK'}

@app.post("/dev/<string:id>/sensors")
def add_sensor(id):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /dev/<id>/sensors content')
        return {'status': 'E_CONTENT'}, 400
    
    payload: typing.Dict[str, typing.Any] = request.get_json()

    if type(payload) != type({}):
        app.logger.error(f'Invalid POST /dev/<id>/sensors json type: {type(payload).__name__}')
        return {'status': 'E_PARAMS'}, 400
    
    if payload.get('module') == None or payload.get('instance_id') == None:
        app.logger.error(f'Missing POST /dev/<id>/sensors params')
        return {'status': 'E_PARAMS'}, 400
    
    py_module = payload['module']
    instance_id = payload['instance_id']

    if devices.get(id) == None:
        app.logger.error(f'POST /dev/<id>/sensors invalid device')
        return {'status': 'E_INV_DEV'}, 400
    
    dev_ip = devices[id]
    dev_url = f'http://{dev_ip}:5000/sensors'

    data = json.dumps({'module': py_module, 'instance_id': instance_id})
    res = requests.post(dev_url, headers={'Content-Type': 'application/json'}, data=data)

    if res.status_code != 200:
        return res.json(), 400
    
    app.logger.info(f'Added new sensor of type {py_module} to {id}, with instance id {instance_id}')
    return {'status': 'OK'}, 200

@app.delete("/dev/sensors/delete_all")
def remove_all_sensors():
    for host_id, host in devices.items():
        sensor_url = f'http://{host}:5000/sensors/get_all'
        res = requests.get(sensor_url)
        if res.status_code != 200:
            return res.json(), 400
        sensor_list = res.json()['sensors']
        
        for sensor in sensor_list:
            mqtt_control_topic = f'{host_id}/{sensor}_stop'
            app.logger.info(mqtt_control_topic)
            result, _ = mqtt.publish(mqtt_control_topic, "STOP", qos=1)
            if result != MQTT_ERR_SUCCESS:
                app.logger.error(f'Publish to {mqtt_control_topic} failed')

        sensor_url = f'http://{host}:5000/sensors/delete_all'
        res = requests.delete(sensor_url)
        if res.status_code != 200:
            return res.json(), 400
    return {'status': 'E_OK'}, 200

@app.get("/dev/sensors/get_all")
def get_all_sensors():
    sensor_list: typing.Dict[str, typing.List] = {}
    for host_id, host in devices.items():
        sensor_list[host_id] = []
        sensor_url = f'http://{host}:5000/sensors/get_all'
        res = requests.get(sensor_url)
        if res.status_code != 200:
            return res.json(), 400
        sensor_list[host_id].extend(res.json()['sensors'])
    return {'status': 'E_OK', 'sensors': sensor_list}, 200
        

@app.post("/shutdown")
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return {'status': 'OK'}, 200
