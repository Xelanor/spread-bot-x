from .utils import request


def get_tickers():
    url = "/api/v2/spot/market/tickers"
    res = request("GET", url)

    tickers = {}

    denominator = "USDT"
    for _ticker in res["data"]:
        if _ticker["symbol"].endswith(denominator):
            nominator = _ticker["symbol"][: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["askPr"])
            tickers[symbol]["bid"] = float(_ticker["bidPr"])
            tickers[symbol]["volume"] = float(_ticker["quoteVolume"])
            tickers[symbol]["rate"] = float(_ticker["change24h"])

    return tickers


def get_depth(ticker):
    url = "/api/v2/spot/market/orderbook"

    params = {"symbol": ticker, "limit": 20}
    res = request("GET", url, params=params)
    res = res["data"]
    asks = res["asks"]
    bids = res["bids"]

    return asks, bids


def get_product_details(ticker):
    url = "/api/v2/spot/public/symbols"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    res = res["data"][0]
    return res
