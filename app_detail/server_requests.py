import requests
import typing
import json

def publish_hosts(server_url: str, host_list: typing.Dict[str, str]):
    host_str = json.dumps(host_list)
    res = requests.post(f'{server_url}/devices', headers={'Content-Type': 'application/json'}, data=host_str)
    if res.status_code != 200:
        print(f'Host publish failed: {res.json()}')
        return False
    return True

def remove_hosts(server_url: str, host_list: typing.List[str]):
    host_str = json.dumps(host_list)
    res = requests.delete(f'{server_url}/devices', params={'devs': host_str})
    if res.status_code != 200:
        print(f'Host delete failed: {res.json()}')
        return False 
    return True

def add_sensor(server_url: str, dev_id: str, module: str, name: str):
    data = json.dumps({'module': module, 'instance_id': name})
    res = requests.post(f'{server_url}/dev/{dev_id}/sensors', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Create sensor failed: {res.json()}')
        return False 
    return True

def remove_all_sensors(server_url: str):
    res = requests.delete(f'{server_url}/dev/sensors/delete_all')
    if res.status_code != 200:
        print(f'Remove sensors failed: {res.json()}')
        return False 
    return True

def get_all_sensors(server_url: str):
    res = requests.get(f'{server_url}/dev/sensors/get_all')
    if res.status_code != 200:
        return None 
    return res.json()['sensors']

def stop_sensor(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.put(f'{server_url}/dev/{host_id}/sensor_stop', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Stop sensor failed: {res.json()}')
        return False 
    return True

def start_sensor(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.put(f'{server_url}/dev/{host_id}/sensor_start', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Start sensor failed: {res.json()}')
        return False 
    return True

def add_actuator(server_url: str, dev_id: str, module: str, name: str):
    data = json.dumps({'module': module, 'instance_id': name})
    res = requests.post(f'{server_url}/dev/{dev_id}/actuators', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Create actuator failed: {res.json()}')
        return False 
    return True

def get_all_actuators(server_url: str):
    res = requests.get(f'{server_url}/dev/actuators/get_all')
    if res.status_code != 200:
        print(f'Error getting all actuators: {res.json()}')
        return None 
    return res.json()['actuators']

def remove_all_actuators(server_url: str):
    res = requests.delete(f'{server_url}/dev/actuators/delete_all')
    if res.status_code != 200:
        print(f'Remove actuators failed: {res.json()}')
        return False 
    return True

def stop_actuator(server_url: str, host_id: str, actuator_id: str):
    data = json.dumps({'actuator_id': actuator_id})
    res = requests.put(f'{server_url}/dev/{host_id}/actuator_stop', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Stop actuator failed: {res.json()}')
        return False 
    return True

def start_actuator(server_url: str, host_id: str, actuator_id: str):
    data = json.dumps({'actuator_id': actuator_id})
    res = requests.put(f'{server_url}/dev/{host_id}/actuator_start', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Start actuator failed: {res.json()}')
        return False 
    return True

def get_sensor_status(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.get(f'{server_url}/dev/{host_id}/sensor_status', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Sensor get status failed: {res.json()}')
        return None
    return res.json()['sensor_status']

def get_actuator_status(server_url: str, host_id: str, actuator_id: str):
    data = json.dumps({'actuator_id': actuator_id})
    res = requests.get(f'{server_url}/dev/{host_id}/actuator_status', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Actuator get status failed: {res.json()}')
        return None
    return json.loads(res.json()['actuator_status'])

def get_sensor_data(server_url: str, host_id: str, sensor_id: str):
    data = json.dumps({'sensor_id': sensor_id})
    res = requests.get(f'{server_url}/dev/{host_id}/sensor_data', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Sensor get data failed: {res.json()}')
        return None
    return [json.loads(elem) for elem in res.json()['sensor_data']]

def add_controller(server_url: str, module: str, instance_id: str):
    data = json.dumps({'module': module, 'instance_id': instance_id})
    res = requests.post(f'{server_url}/controllers/add', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Add controller failed: {res.json()}')
        return False
    return True

def remove_controller(server_url: str, instance_id: str):
    data = json.dumps({'instance_id': instance_id})
    res = requests.delete(f'{server_url}/controllers/remove', headers={'Content-Type': 'application/json'}, data=data)
    if res.status_code != 200:
        print(f'Remove controller failed: {res.json()}')
        return False
    return True

def get_all_controllers(server_url: str):
    res = requests.get(f'{server_url}/controllers/get_all')
    if res.status_code != 200:
        print(f'Error getting all controllers: {res.json()}')
        return None 
    return res.json()['controllers']

def remove_all_controllers(server_url: str):
    res = requests.delete(f'{server_url}/controllers/remove_all')
    if res.status_code != 200:
        print(f'Error removing all controllers: {res.json()}')
        return False 
    return True