import requests

def call_url(url, headers={}, payload = {}, method= 'GET'):
    if method == 'GET':
        return requests.get(url, headers=headers, data=payload)
    elif method == 'POST':
        return requests.post(url, headers=headers, data=payload)