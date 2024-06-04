import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode, quote
import json

HOST = "https://api.mexc.com"
WS_HOST = "wss://wbs.mexc.com/ws"


def sign(private_key, req_time, sign_params=None):
    if sign_params:
        sign_params = urlencode(sign_params, quote_via=quote)
        to_sign = "{}&timestamp={}".format(sign_params, req_time)
    else:
        to_sign = "timestamp={}".format(req_time)
    sign = hmac.new(
        private_key.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return sign


def sign_request(public_key, private_key, method, url, params=None):
    url = "{}{}".format(HOST, url)
    req_time = str(int(time.time() * 1000))
    if params:
        params["signature"] = sign(private_key, req_time=req_time, sign_params=params)
    else:
        params = {}
        params["signature"] = sign(private_key, req_time=req_time)
    params["timestamp"] = req_time
    headers = {
        "x-mexc-apikey": public_key,
        "Content-Type": "application/json",
    }
    res = requests.request(method, url, params=params, headers=headers)
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
