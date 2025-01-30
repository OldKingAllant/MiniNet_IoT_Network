import json 
import requests

def send_server_ip(controller_url: str, ip):
    body = json.dumps( {'ip_address': ip} )
    res = requests.post(f'{controller_url}/set_server_address', headers={'ContentType': 'application/json'}, data=body)
    if res.status_code != 200:
        print(f'Set server ip failed: {res.json()}')
    return

def send_nat_ip(controller_url: str, ip):
    body = json.dumps( {'ip_address': ip} )
    res = requests.post(f'{controller_url}/set_nat_address', headers={'ContentType': 'application/json'}, data=body)
    if res.status_code != 200:
        print(f'Set server ip failed: {res.json()}')
    return