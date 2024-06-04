import requests
import json
import base64
from uuid import uuid1
import time
import hashlib
import hmac

HOST = "https://api.kucoin.com"


def sign_request(public_key, private_key, group, method, url, params=None):
    now = int(time.time() * 1000)

    str_to_sign = str(now) + method + url
    data = None
    if params:
        data = json.dumps(params)
        str_to_sign = str(now) + method + url + data

    signature = base64.b64encode(
        hmac.new(
            private_key.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(
            private_key.encode("utf-8"), group.encode("utf-8"), hashlib.sha256
        ).digest()
    )
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": public_key,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
    }
    if params:
        headers["Content-Type"] = "application/json"

    res = requests.request(method, HOST + url, data=data, headers=headers)
    return parse_response(res)


def request(method, url, params=None):
    url = "{}{}".format(HOST, url)
    res = requests.request(method, url, params=params)
    return parse_response(res)


def parse_response(res, req_type=None):
    if res is None:
        return None
    elif res.status_code == 200:
        obj = json.loads(res.text)
        return obj
    else:
        obj = json.loads(res.text)
        return obj
