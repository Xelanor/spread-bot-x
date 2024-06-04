import requests
import hmac
import hashlib
import time
import json

HOST = "https://api.bybit.com"
WS_HOST = "wss://stream.bybit.com/v5/public/spot"


proxy = {
    "http": "http://berkeozelsel03UwY:Vp8yt2NIi4@131.196.255.217:50100/",
    "https": "http://berkeozelsel03UwY:Vp8yt2NIi4@131.196.255.217:50100/",
}


def cast_values(parameters):
    string_params = [
        "qty",
        "price",
        "triggerPrice",
        "takeProfit",
        "stopLoss",
    ]
    integer_params = ["positionIdx"]
    for key, value in parameters.items():
        if key in string_params:
            if type(value) != str:
                parameters[key] = str(value)
        elif key in integer_params:
            if type(value) != int:
                parameters[key] = int(value)


def sign_request(public_key, private_key, group, method, url, params={}):
    if params is not None:
        for i in params.keys():
            if isinstance(params[i], float) and params[i] == int(params[i]):
                params[i] = int(params[i])

    timestamp = int(time.time() * 10**3)
    if method == "GET":
        payload = "&".join(
            [str(k) + "=" + str(v) for k, v in sorted(params.items()) if v is not None]
        )
    else:
        cast_values(params)
        payload = json.dumps(params)

    param_str = str(timestamp) + public_key + str(5000) + payload
    signature = hmac.new(
        bytes(private_key, "utf-8"), param_str.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-BAPI-SIGN": signature,
        "X-BAPI-API-KEY": public_key,
        "X-BAPI-TIMESTAMP": str(timestamp),
        "X-BAPI-RECV-WINDOW": str(5000),
    }

    if method == "GET":
        if payload:
            res = requests.request(
                method,
                HOST + url + f"?{payload}",
                headers=headers,
                proxies=proxy,
            )
        else:
            res = requests.request(
                method,
                HOST + url,
                headers=headers,
                proxies=proxy,
            )
    else:
        res = requests.request(
            method,
            HOST + url,
            headers=headers,
            data=payload,
            proxies=proxy,
        )

    return parse_response(res)


def request(method, url, params=None):
    url = "{}{}".format(HOST, url)
    res = requests.request(method, url, params=params, proxies=proxy)
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
