from flask.app import Flask
from flask.app import request

import os
import logging
import typing
from subprocess import Popen

app = Flask(__name__)

sensors: typing.Dict[str, Popen] = {}
actuators: typing.Dict[str, Popen] = {}

app.logger.setLevel(logging.DEBUG)

if os.environ.get('MQTT_ADDRESS') == None or os.environ.get('MQTT_PORT') == None:
    app.logger.fatal(f'Env. variables for MQTT do not exist')
    exit(1)

if os.environ.get('SERVER_ID') == None:
    app.logger.fatal(f'Env. variables SERVER_ID does not exist')
    exit(1)

@app.route("/heartbeat")
def heartbeat():
    return {'status': 'E_OK'}, 200

###################################################################################################

@app.post("/sensors")
def add_sensor():
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /sensors content')
        return {'status': 'E_CONTENT'}, 400
    
    payload: typing.Dict[str, typing.Any] = request.get_json()

    if type(payload) != type({}):
        app.logger.error(f'Invalid POST /sensors type: {type(payload).__name__}')
        return {'status': 'E_PARAMS'}, 400
    
    if payload.get('module') == None or payload.get('instance_id') == None:
        app.logger.error(f'Missing POST /sensors params')
        return {'status': 'E_PARAMS'}, 400
    
    if sensors.get(payload['instance_id']) != None:
        return {'status': 'E_EXISTS'}, 200
    
    instance_id = payload['instance_id']
    py_module = payload['module']

    if not os.path.exists(f'./sensors/{py_module}.py'):
        return {'status': 'E_MODULE'}, 400
    
    new_env = {}
    new_env.update(os.environ)
    new_env['MODULE_NAME'] = instance_id
    proc = Popen(f'python3 ./sensors/{py_module}.py', shell=True, env=new_env)
    sensors[instance_id] = proc
    
    return {'status': 'E_OK'}, 200

@app.delete("/sensors/<string:id>")
def remove_sensor(id):
    if sensors.get(id) == None:
        app.logger.error(f'Sensor {id} does not exist')
        return {'status': 'E_NOT_EXIST'}, 400
    
    proc = sensors[id]
    proc.terminate()
    del sensors[id]
    return {'status': 'E_OK'}, 200

@app.delete("/sensors/delete_all")
def remove_all_sensors():
    for sensor in sensors.values():
        sensor.terminate()
    sensors.clear()
    return {'status': 'E_OK'}, 200

@app.get("/sensors/get_all")
def get_sensors():
    sensor_names = [name for name in sensors.keys()]
    return {'status': 'E_OK', 'sensors': sensor_names}, 200

@app.get("/sensors/<string:sensor_id>/exists")
def find_sensor(sensor_id: str):
    if sensors.get(sensor_id) != None:
        return {'status': 'E_FOUND'}, 200
    return {'status': 'E_NOT_FOUND'}, 200

###################################################################################################

@app.post("/actuators")
def add_actuator():
    if request.headers.get('Content-Type') != 'application/json':
        app.logger.error(f'Invalid POST /actuators content')
        return {'status': 'E_CONTENT'}, 400
    
    payload: typing.Dict[str, typing.Any] = request.get_json()

    if type(payload) != type({}):
        app.logger.error(f'Invalid POST /actuators type: {type(payload).__name__}')
        return {'status': 'E_PARAMS'}, 400
    
    if payload.get('module') == None or payload.get('instance_id') == None:
        app.logger.error(f'Missing POST /actuators params')
        return {'status': 'E_PARAMS'}, 400
    
    if actuators.get(payload['instance_id']) != None:
        return {'status': 'E_EXISTS'}, 200
    
    instance_id = payload['instance_id']
    py_module = payload['module']

    if not os.path.exists(f'./actuators/{py_module}.py'):
        return {'status': 'E_MODULE'}, 400
    
    new_env = {}
    new_env.update(os.environ)
    new_env['MODULE_NAME'] = instance_id
    proc = Popen(f'python3 ./actuators/{py_module}.py', shell=True, env=new_env)
    actuators[instance_id] = proc
    
    return {'status': 'E_OK'}, 200

@app.delete("/actuators/<string:id>")
def remove_actuator(id):
    if actuators.get(id) == None:
        app.logger.error(f'Actuator {id} does not exist')
        return {'status': 'E_NOT_EXIST'}, 400
    
    proc = actuators[id]
    proc.terminate()
    del actuators[id]
    return {'status': 'E_OK'}, 200

@app.delete("/actuators/delete_all")
def remove_all_actuators():
    for actuator in actuators.values():
        actuator.terminate()
    actuators.clear()
    return {'status': 'E_OK'}, 200

@app.get("/actuators/get_all")
def get_actuators():
    actuator_names = [name for name in actuators.keys()]
    return {'status': 'E_OK', 'actuators': actuator_names}, 200

@app.get("/actuators/<string:actuator_id>/exists")
def find_actuator(actuator_id: str):
    if actuators.get(actuator_id) != None:
        return {'status': 'E_FOUND'}, 200
    return {'status': 'E_NOT_FOUND'}, 200