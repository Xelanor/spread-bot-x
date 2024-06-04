from .utils import request


def get_tickers():
    url = "/v4/public/ticker"
    res = request("GET", url)
    res = res["result"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker["s"].split("_")[0]
        _denominator = _ticker["s"].split("_")[1]
        if _denominator.upper() == denominator:
            symbol = f"{nominator.upper()}/{denominator}"
            tickers[symbol] = {}

            try:
                tickers[symbol]["ask"] = float(_ticker["ap"])
                tickers[symbol]["bid"] = float(_ticker["bp"])
                tickers[symbol]["volume"] = float(_ticker["v"])
                tickers[symbol]["rate"] = float(_ticker["cr"])
            except:
                continue

    return tickers


def get_depth(ticker):
    url = "/v4/public/depth"

    params = {"symbol": ticker, "limit": 10}
    res = request("GET", url, params=params)
    res = res["result"]
    asks = res["asks"]
    bids = res["bids"]

    return asks, bids


def get_product_details(ticker):
    url = "/v4/public/symbol"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    res = res["result"]["symbols"][0]
    return res


def get_allowed_symbols():
    url = "/v4/public/symbol"

    res = request("GET", url)
    res = res["result"]["symbols"]
    res = [coin["displayName"] for coin in res if coin["openapiEnabled"]]

    return res
