import requests
import hmac
import hashlib
import time
import json
from copy import deepcopy

HOST = "https://sapi.xt.com"
WS_HOST = "wss://stream.xt.com/public"


def create_sign(url, method, headers=None, secret_key=None, **kwargs):
    path_str = url
    query = kwargs.pop("params", None)
    data = kwargs.pop("data", None) or kwargs.pop("json", None)
    query_str = (
        ""
        if query is None
        else "&".join(
            [
                f"{key}={json.dumps(query[key]) if type(query[key]) in [dict, list] else query[key]}"
                for key in sorted(query)
            ]
        )
    )
    body_str = json.dumps(data) if data is not None else ""
    y = "#" + "#".join([i for i in [method, path_str, query_str, body_str] if i])
    x = "&".join([f"{key}={headers[key]}" for key in sorted(headers)])
    sign = f"{x}{y}"
    return (
        hmac.new(secret_key.encode("utf-8"), sign.encode("utf-8"), hashlib.sha256)
        .hexdigest()
        .upper()
    )


def gen_auth_header(public_key, private_key, path, method, **kwargs):
    headers = {}
    headers["xt-validate-timestamp"] = str(int((time.time() - 30) * 1000))
    headers["xt-validate-appkey"] = public_key
    headers["xt-validate-recvwindow"] = "60000"
    headers["xt-validate-algorithms"] = "HmacSHA256"
    headers["xt-validate-signature"] = create_sign(
        path, method, headers, str(private_key), **kwargs
    )
    headers_ = deepcopy(headers)
    headers_.update(headers)
    return headers


def sign_request(public_key, private_key, method, path, **params):
    headers = gen_auth_header(public_key, private_key, path, method, **params)

    kwargs = {"headers": headers, "timeout": 10}
    kwargs.update(params)

    url = "{}{}".format(HOST, path)
    res = requests.request(method, url, **kwargs)
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
