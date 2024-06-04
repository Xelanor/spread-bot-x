from .utils import request


def get_tickers():
    url = "/v2/ticker/24hr.do?symbol=all"
    res = request("GET", url)
    res = res["data"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        nominator = _ticker["symbol"].split("_")[0]
        _denominator = _ticker["symbol"].split("_")[1]
        if _denominator.upper() == denominator:
            symbol = f"{nominator.upper()}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["ticker"]["latest"])
            tickers[symbol]["bid"] = float(_ticker["ticker"]["latest"])
            tickers[symbol]["volume"] = float(_ticker["ticker"]["vol"]) * float(
                _ticker["ticker"]["latest"]
            )
            tickers[symbol]["rate"] = float(_ticker["ticker"]["change"]) / 100

    return tickers
