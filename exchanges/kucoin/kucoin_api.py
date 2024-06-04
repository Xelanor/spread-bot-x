from .utils import request


def get_product_details(ticker):
    url = "/api/v2/symbols"

    res = request("GET", url)
    res = [coin for coin in res["data"] if coin["symbol"] == ticker][0]
    return res


def get_tickers():
    url = "/api/v1/market/allTickers"
    res = request("GET", url)
    res = res["data"]["ticker"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker["symbol"].split("-")[0]
        _denominator = _ticker["symbol"].split("-")[1]
        if _denominator == denominator:
            symbol = f"{nominator}/{denominator}"
            try:
                tickers[symbol] = {}

                tickers[symbol]["ask"] = float(_ticker["sell"])
                tickers[symbol]["bid"] = float(_ticker["buy"])
                tickers[symbol]["volume"] = float(_ticker["volValue"])
                tickers[symbol]["rate"] = float(_ticker["changeRate"])
            except:
                del tickers[symbol]
                continue

    return tickers


def get_depth(ticker):
    url = "/api/v1/market/orderbook/level2_20"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    asks = res["data"]["asks"]
    bids = res["data"]["bids"]

    return asks, bids
