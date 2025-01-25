from flask.app import Flask
from flask.app import request

from flask_mqtt import Mqtt
from flask_mqtt import MQTT_ERR_SUCCESS

from paho.mqtt.client import MQTTMessage

import typing
import json
import logging
import sys
import os
import traceback
import copy

from subprocess import Popen

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

curr_statuses: typing.Dict[str, str] = {}
sensors_data: typing.Dict[str, typing.List[str]] = {}

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    app.logger.info(f'Connected to Mqtt broker')

@mqtt.on_message()
def handle_publish(client, userdata, message: MQTTMessage):
    global curr_statuses
    payload_msg = message.payload.decode()
    topic = message.topic
    if topic.find('status') != -1:
        #This is a status message
        curr_statuses[message.topic] = payload_msg
        return
    #This is a data message
    if sensors_data.get(message.topic) == None:
        sensors_data[message.topic] = [payload_msg]
    else:
        sensors_data[message.topic].append(payload_msg)
    return

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

########################################################################################
########################################################################################



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
    
    mqtt_data_topic = f'{id}/{instance_id}'
    mqtt_status_topic = f'{id}/{instance_id}_status'

    mqtt.subscribe(mqtt_data_topic)
    mqtt.subscribe(mqtt_status_topic)
    
    app.logger.info(f'Added new sensor of type {py_module} to {id}, with instance id {instance_id}')
    return {'status': 'OK'}, 200

@app.delete("/dev/sensors/delete_all")
def remove_all_sensors():
    for _, host in devices.items():
        sensor_url = f'http://{host}:5000/sensors/delete_all'
        res = requests.delete(sensor_url)
        if res.status_code != 200:
            return res.json(), 400
    mqtt.unsubscribe_all()
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

@app.put("/dev/<string:host_id>/sensor_stop")
def stop_sensor(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid PUT /dev/<id>/sensor_stop content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('sensor_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/sensors/{payload["sensor_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    mqtt_control_topic = f'{host_id}/{payload["sensor_id"]}_control'
    app.logger.info(mqtt_control_topic)
    result, _ = mqtt.publish(mqtt_control_topic, "STOP", qos=1)
    if result != MQTT_ERR_SUCCESS:
        app.logger.error(f'Publish to {mqtt_control_topic} failed')
        return {'status': 'E_FAIL'}, 400
    return {'status': 'E_OK'}, 200

@app.put("/dev/<string:host_id>/sensor_start")
def start_sensor(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid PUT /dev/<id>/sensor_start content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('sensor_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/sensors/{payload["sensor_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    mqtt_control_topic = f'{host_id}/{payload["sensor_id"]}_control'
    app.logger.info(mqtt_control_topic)
    result, _ = mqtt.publish(mqtt_control_topic, "START", qos=1)
    if result != MQTT_ERR_SUCCESS:
        app.logger.error(f'Publish to {mqtt_control_topic} failed')
        return {'status': 'E_FAIL'}, 400
    return {'status': 'E_OK'}, 200



###########################################################################################
###########################################################################################


@app.post("/dev/<string:host_id>/actuators")
def add_actuator(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /dev/<id>/actuators content')
        return {'status': 'E_CONTENT'}, 400
    
    payload: typing.Dict[str, typing.Any] = request.get_json()

    if type(payload) != type({}):
        app.logger.error(f'Invalid POST /dev/<id>/actuators json type: {type(payload).__name__}')
        return {'status': 'E_PARAMS'}, 400
    
    if payload.get('module') == None or payload.get('instance_id') == None:
        app.logger.error(f'Missing POST /dev/<id>/actuators params')
        return {'status': 'E_PARAMS'}, 400
    
    py_module = payload['module']
    instance_id = payload['instance_id']

    if devices.get(host_id) == None:
        app.logger.error(f'POST /dev/<id>/actuators invalid device')
        return {'status': 'E_INV_DEV'}, 400
    
    dev_ip = devices[host_id]
    dev_url = f'http://{dev_ip}:5000/actuators'

    data = json.dumps({'module': py_module, 'instance_id': instance_id})
    res = requests.post(dev_url, headers={'Content-Type': 'application/json'}, data=data)

    if res.status_code != 200:
        return res.json(), 400
    
    mqtt_status_topic = f'{host_id}/{instance_id}_status'
    mqtt.subscribe(mqtt_status_topic)
    
    app.logger.info(f'Added new actuator of type {py_module} to {host_id}, with instance id {instance_id}')
    return {'status': 'OK'}, 200


@app.get("/dev/actuators/get_all")
def get_all_actuators():
    actuator_list: typing.Dict[str, typing.List] = {}
    for host_id, host in devices.items():
        actuator_list[host_id] = []
        sensor_url = f'http://{host}:5000/actuators/get_all'
        res = requests.get(sensor_url)
        if res.status_code != 200:
            return res.json(), 400
        actuator_list[host_id].extend(res.json()['actuators'])
    return {'status': 'E_OK', 'actuators': actuator_list}, 200

@app.delete("/dev/actuators/delete_all")
def remove_all_actuators():
    for _, host in devices.items():
        actuator_url = f'http://{host}:5000/actuators/delete_all'
        res = requests.delete(actuator_url)
        if res.status_code != 200:
            return res.json(), 400
    mqtt.unsubscribe_all()
    return {'status': 'E_OK'}, 200

@app.put("/dev/<string:host_id>/actuator_stop")
def stop_actuator(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid PUT /dev/<id>/actuator_stop content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('actuator_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/actuators/{payload["actuator_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    mqtt_control_topic = f'{host_id}/{payload["actuator_id"]}_control'
    app.logger.info(mqtt_control_topic)
    result, _ = mqtt.publish(mqtt_control_topic, "STOP", qos=1)
    if result != MQTT_ERR_SUCCESS:
        app.logger.error(f'Publish to {mqtt_control_topic} failed')
        return {'status': 'E_FAIL'}, 400
    return {'status': 'E_OK'}, 200

@app.put("/dev/<string:host_id>/actuator_start")
def start_actuator(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid PUT /dev/<id>/actuator_start content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('actuator_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/actuators/{payload["actuator_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    mqtt_control_topic = f'{host_id}/{payload["actuator_id"]}_control'
    app.logger.info(mqtt_control_topic)
    result, _ = mqtt.publish(mqtt_control_topic, "START", qos=1)
    if result != MQTT_ERR_SUCCESS:
        app.logger.error(f'Publish to {mqtt_control_topic} failed')
        return {'status': 'E_FAIL'}, 400
    return {'status': 'E_OK'}, 200

###########################################################################################
###########################################################################################

@app.get("/dev/<string:host_id>/sensor_status")
def get_sensor_status(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid GET /dev/<id>/sensor_status content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('sensor_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/sensors/{payload["sensor_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    topic_name = f'{host_id}/{payload["sensor_id"]}_status'
    if curr_statuses.get(topic_name) == None:
        return {'status': 'E_NOT_AVAIL'}, 400
    
    return {'status': 'E_OK', 'sensor_status': curr_statuses[topic_name]}, 200

@app.get("/dev/<string:host_id>/actuator_status")
def get_actuator_status(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid GET /dev/<id>/actuator_status content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('actuator_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/actuators/{payload["actuator_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    topic_name = f'{host_id}/{payload["actuator_id"]}_status'
    if curr_statuses.get(topic_name) == None:
        return {'status': 'E_NOT_AVAIL'}, 400
    
    return {'status': 'E_OK', 'actuator_status': curr_statuses[topic_name]}, 200

@app.get("/dev/<string:host_id>/sensor_data")
def get_sensor_data(host_id: str):
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid GET /dev/<id>/sensor_data content')
        return {'status': 'E_CONTENT'}, 400
    if devices.get(host_id) == None:
        return {'status': 'E_HOST'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('sensor_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    host_url = f'http://{devices[host_id]}:5000/sensors/{payload["sensor_id"]}/exists'
    res = requests.get(host_url)

    if res.status_code != 200:
        return res.json(), 400
    
    if res.json()["status"] != 'E_FOUND':
        return {'status': 'E_INV_ID'}, 400
    
    topic_name = f'{host_id}/{payload["sensor_id"]}'
    if sensors_data.get(topic_name) == None:
        return {'status': 'E_NOT_AVAIL'}, 400
    data = copy.deepcopy( sensors_data[topic_name] )
    sensors_data[topic_name].clear()
    return {'status': 'E_OK', 'sensor_data': data}, 200

###########################################################################################
###########################################################################################

controllers: typing.Dict[str, Popen] = {}

@app.post("/controllers/add")
def add_controller():
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /controllers/add content')
        return {'status': 'E_CONTENT'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('module') == None:
        return {'status': 'E_MODULE'}, 400
    if payload.get('instance_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    if controllers.get(payload['instance_id']) != None:
        return {'status': 'E_EXISTS'}, 400
    
    py_module = payload['module']
    if not os.path.exists(f'./controllers/{py_module}.py'):
        return {'status': 'E_MODULE'}, 400
    
    new_env = {}
    new_env.update(os.environ)
    new_env['MODULE_NAME'] = payload['instance_id']
    controllers[payload['instance_id']] = Popen(f'python3 ./controllers/{py_module}.py', shell=True, env=new_env)
    return {'status': 'E_OK'}, 200

@app.delete("/controllers/remove")
def remove_controller():
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid DELETE /controllers/remove content')
        return {'status': 'E_CONTENT'}, 400
    
    payload = request.get_json()

    if type(payload) != type({}):
        return {'status': 'E_LIST'}, 400
    if payload.get('instance_id') == None:
        return {'status': 'E_MISSING_ID'}, 400
    
    if controllers.get(payload['instance_id']) == None:
        return {'status': 'E_NOT_EXIST'}, 400
    
    controllers[payload['instance_id']].terminate()
    del controllers[payload['instance_id']]
    return {'status': 'E_OK'}, 200

@app.delete("/controllers/remove_all")
def remove_all_controllers():
    for controller in controllers.values():
        controller.terminate()
    controllers.clear()
    return {'status': 'E_OK'}, 200

@app.get("/controllers/get_all")
def get_all_controllers():
    names = [name for name in controllers.keys()]
    return {'status': 'E_OK', 'controllers': names}, 200


###########################################################################################
###########################################################################################

@app.post("/shutdown")
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return {'status': 'OK'}, 200

@app.errorhandler(Exception)
def handle_exception(exc):
    backtrace = traceback.format_exc()
    app.logger.error(backtrace)
    return {'status': 'E_INTERNAL_ERROR'}, 500