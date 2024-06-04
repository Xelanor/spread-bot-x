from .utils import request


def get_tickers():
    url = "/api/pro/v1/spot/ticker"
    res = request("GET", url)
    res = res["data"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker["symbol"].split("/")[0]
        _denominator = _ticker["symbol"].split("/")[1]
        if _denominator == denominator:
            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["ask"][0])
            tickers[symbol]["bid"] = float(_ticker["bid"][0])
            tickers[symbol]["volume"] = float(_ticker["volume"]) * float(
                _ticker["ask"][0]
            )
            tickers[symbol]["rate"] = (
                float(_ticker["close"]) / float(_ticker["open"])
            ) - 1

    return tickers
