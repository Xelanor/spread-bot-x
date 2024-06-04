import requests
import json
import hmac
import datetime

HOST = "https://api-cloud.bitmart.com"
WS_HOST = "wss://ws-manager-compress.bitmart.com/api?protocol=1.1"
WS_LOGIN_HOST = "wss://ws-manager-compress.bitmart.com/user?protocol=1.1"


def utc_timestamp():
    return str(datetime.datetime.now().timestamp() * 1000).split(".")[0]


def sign(secret, message):
    mac = hmac.new(
        bytes(secret, encoding="utf8"),
        bytes(message, encoding="utf-8"),
        digestmod="sha256",
    )
    return mac.hexdigest()


def pre_substring(timestamp, memo, body):
    return f"{str(timestamp)}#{memo}#{body}"


def sign_request(public_key, private_key, group, method, url, params=None):
    url = "{}{}".format(HOST, url)
    ts = utc_timestamp()
    headers = {
        "X-BM-KEY": public_key,
        "X-BM-SIGN": sign(
            private_key, pre_substring(ts, group, str(json.dumps(params)))
        ),
        "X-BM-TIMESTAMP": ts,
    }

    res = requests.request(method, url, json=params, headers=headers)
    return parse_response(res, url)


def request(method, url, params=None):
    url = "{}{}".format(HOST, url)
    res = requests.request(method, url, params=params)
    return parse_response(res, url)


def parse_response(res, url=None):
    if res is None:
        return None
    elif res.status_code == 200:
        obj = json.loads(res.text)
        return obj
    else:
        obj = json.loads(res.text)
        print(obj, url)
        return obj
