import requests
import json
import hmac
from hashlib import sha256
import time
import random

from exchanges.utils import proxies

HOST = "https://open-api.bingx.com"
WS_HOST = "wss://open-api-ws.bingx.com/market"


def get_sign(private_key, payload):
    signature = hmac.new(
        private_key.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256
    ).hexdigest()
    return signature


def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "":
        return paramsStr + "&timestamp=" + str(int(time.time() * 1000))
    else:
        return paramsStr + "timestamp=" + str(int(time.time() * 1000))


def sign_request(public_key, private_key, group, method, url, params={}):
    params_str = parseParam(params)
    url = "%s%s?%s&signature=%s" % (
        HOST,
        url,
        params_str,
        get_sign(private_key, params_str),
    )

    headers = {
        "X-BX-APIKEY": public_key,
    }

    res = requests.request(
        method,
        url,
        headers=headers,
        # proxies=random.choice([random.choice(proxies), None]),
    )
    return parse_response(res)


def request(method, url, params=None):
    url = "{}{}".format(HOST, url)
    if not params:
        params = {}

    params["timestamp"] = int(time.time() * 1000)
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
        print(obj)
        return obj
