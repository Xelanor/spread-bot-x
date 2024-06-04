from .utils import request


def get_bitmart_product_details(ticker):
    url = "/spot/v1/symbols/details"

    res = request("GET", url)
    res = [coin for coin in res["data"]["symbols"] if coin["symbol"] == ticker][0]
    return res


def get_bitmart_tickers():
    url = "/spot/quotation/v3/tickers"
    res = request("GET", url)
    res = res["data"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker[0].split("_")[0]
        _denominator = _ticker[0].split("_")[1]
        if _denominator == denominator:
            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker[10])
            tickers[symbol]["bid"] = float(_ticker[8])
            tickers[symbol]["volume"] = float(_ticker[3])
            tickers[symbol]["rate"] = float(_ticker[7])

    return tickers


def get_bitmart_depth(ticker):
    url = "/spot/quotation/v3/books"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    asks = res["data"]["asks"]
    bids = res["data"]["bids"]

    return asks, bids
