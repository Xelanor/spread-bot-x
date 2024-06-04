import requests
import hmac
import base64
import time
import json

HOST = "https://api.bitget.com"
WS_HOST = "wss://ws.bitget.com/v2/ws/public"


def get_timestamp():
    return int(time.time() * 1000)


def sign(message, secret_key):
    mac = hmac.new(
        bytes(secret_key, encoding="utf8"),
        bytes(message, encoding="utf-8"),
        digestmod="sha256",
    )
    d = mac.digest()
    return base64.b64encode(d)


def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body


def parse_params_to_str(params):
    params = [(key, val) for key, val in params.items()]
    params.sort(key=lambda x: x[0])
    url = "?" + toQueryWithNoEncode(params)
    if url == "?":
        return ""
    return url


def toQueryWithNoEncode(params):
    url = ""
    for key, value in params:
        url = url + str(key) + "=" + str(value) + "&"
    return url[0:-1]


def sign_request(public_key, private_key, group, method, path, params={}):
    url = "{}{}".format(HOST, path)
    timestamp = get_timestamp()

    if method == "GET":
        body = ""
        request_path = path + parse_params_to_str(params)
        signature = sign(
            pre_hash(timestamp, "GET", request_path, str(body)), private_key
        )

    elif method == "POST":
        body = json.dumps(params)
        signature = sign(pre_hash(timestamp, "POST", path, str(body)), private_key)

    headers = {
        "ACCESS-KEY": public_key,
        "ACCESS-SIGN": signature,
        "ACCESS-PASSPHRASE": group,
        "ACCESS-TIMESTAMP": str(timestamp),
        "locale": "en-US",
        "Content-Type": "application/json",
    }

    if method == "GET":
        res = requests.request(method, HOST + request_path, headers=headers)
    elif method == "POST":
        res = requests.request(method, url, data=body, headers=headers)

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
