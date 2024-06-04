from exchanges.bingx.utils import request


def get_product_details(ticker):
    url = "/openApi/spot/v1/common/symbols"

    res = request("GET", url)
    res = [coin for coin in res["data"]["symbols"] if coin["symbol"] == ticker][0]
    return res


def get_tickers():
    url = "/openApi/spot/v1/ticker/24hr"
    res = request("GET", url)
    res = res["data"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker["symbol"].split("-")[0]
        _denominator = _ticker["symbol"].split("-")[1]
        if _denominator == denominator:
            symbol = f"{nominator}/{denominator}"
            try:
                tickers[symbol] = {}

                tickers[symbol]["ask"] = float(_ticker["askPrice"])
                tickers[symbol]["bid"] = float(_ticker["bidPrice"])
                tickers[symbol]["volume"] = float(_ticker["quoteVolume"])
                tickers[symbol]["rate"] = float(_ticker["priceChange"]) / float(
                    _ticker["openPrice"]
                )
            except:
                del tickers[symbol]
                continue

    return tickers


def get_depth(ticker):
    url = "/openApi/spot/v1/market/depth"

    params = {"symbol": ticker}
    res = request("GET", url, params=params)
    asks = res["data"]["asks"][::-1]
    bids = res["data"]["bids"]

    return asks, bids


def get_allowed_symbols():
    url = "/openApi/spot/v1/common/symbols"

    res = request("GET", url)
    res = [
        coin["symbol"]
        for coin in res["data"]["symbols"]
        if coin["apiStateBuy"] and coin["apiStateSell"]
    ]

    return res
