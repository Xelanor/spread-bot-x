import requests
import json
import base64
from uuid import uuid1
import time
import hashlib
import hmac
import urllib.parse

HOST = "https://api.huobi.pro"
WS_HOST = "wss://api.huobi.pro/ws"


def sign_request(public_key, private_key, method, path, params={}, data={}):
    params.update(
        {
            "AccessKeyId": public_key,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": "2",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        }
    )

    sorted_params = sorted(params.items())
    encoded_params = urllib.parse.urlencode(sorted_params)

    pre_signed_text = f"{method.upper()}\napi.huobi.pro\n{path}\n{encoded_params}"
    digest = hmac.new(
        private_key.encode("utf-8"), pre_signed_text.encode("utf-8"), hashlib.sha256
    ).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    signature = urllib.parse.quote(signature, safe="")
    signed_params = f"{encoded_params}&Signature={signature}"
    url = f"{HOST}{path}?{signed_params}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if method == "GET":
        res = requests.request(method, url, headers=headers)
    else:
        res = requests.request(method, url, headers=headers, json=data)
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
