from .utils import request


def get_tickers():
    url = "/v5/market/tickers"
    params = {"category": "spot"}
    res = request("GET", url, params=params)

    tickers = {}

    denominator = "USDT"
    for _ticker in res["result"]["list"]:
        if _ticker["symbol"].endswith(denominator):
            nominator = _ticker["symbol"][: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            try:
                tickers[symbol] = {}

                tickers[symbol]["ask"] = float(_ticker["ask1Price"])
                tickers[symbol]["bid"] = float(_ticker["bid1Price"])
                tickers[symbol]["volume"] = float(_ticker["volume24h"]) * float(
                    _ticker["bid1Price"]
                )
                tickers[symbol]["rate"] = float(_ticker["price24hPcnt"])
            except:
                del tickers[symbol]
                continue

    return tickers


def get_depth(ticker):
    url = "/v5/market/orderbook"

    params = {"symbol": ticker, "category": "spot", "limit": 20}
    res = request("GET", url, params=params)
    res = res["result"]
    asks = res["a"]
    bids = res["b"]

    return asks, bids


def get_product_details(ticker):
    url = "/v5/market/instruments-info"

    params = {"symbol": ticker, "category": "spot"}
    res = request("GET", url, params=params)
    res = res["result"]["list"][0]
    return res
