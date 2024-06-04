from .utils import request


def get_mexc_product_details(ticker):
    url = "/api/v3/exchangeInfo"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    res = res["symbols"][0]
    return res


def get_mexc_tickers():
    url = "/api/v3/ticker/24hr"
    res = request("GET", url)

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        if _ticker["symbol"].endswith(denominator):
            nominator = _ticker["symbol"][: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["askPrice"])
            tickers[symbol]["bid"] = float(_ticker["bidPrice"])
            tickers[symbol]["volume"] = float(_ticker["quoteVolume"])
            tickers[symbol]["rate"] = float(_ticker["priceChangePercent"])

    return tickers


def get_mexc_depth(ticker):
    url = "/api/v3/depth"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    asks = res["asks"]
    bids = res["bids"]

    return asks, bids


def get_allowed_symbols():
    url = "/api/v3/defaultSymbols"

    res = request("GET", url)
    res = res["data"]

    return res
