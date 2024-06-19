from .utils import request


def get_tickers():
    url = "/market/tickers"
    res = request("GET", url)

    tickers = {}

    denominator = "USDT"
    for _ticker in res["data"]:
        if _ticker["symbol"].upper().endswith(denominator):
            nominator = _ticker["symbol"].upper()[: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            try:
                tickers[symbol] = {}

                tickers[symbol]["ask"] = float(_ticker["ask"])
                tickers[symbol]["bid"] = float(_ticker["bid"])
                tickers[symbol]["volume"] = float(_ticker["vol"])
                tickers[symbol]["rate"] = (
                    float(_ticker["close"]) / float(_ticker["open"]) - 1
                )
            except:
                del tickers[symbol]
                continue

    return tickers


def get_depth(ticker):
    url = "/market/depth"

    params = {"symbol": ticker, "depth": 5, "type": "step0"}
    res = request("GET", url, params=params)
    res = res["tick"]
    asks = res["asks"]
    bids = res["bids"]

    return asks, bids


def get_product_details(ticker):
    url = "/v2/settings/common/symbols"

    res = request("GET", url)
    res = [coin for coin in res["data"] if coin["sc"] == ticker][0]
    return res
