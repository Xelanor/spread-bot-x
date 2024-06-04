from .utils import request


def get_tickers():
    url = "/spot/ticker"
    res = request("GET", url)
    res = res["data"]

    tickers = {}

    denominator = "USDT"
    for _ticker in res:
        if _ticker["market"].endswith(denominator):
            nominator = _ticker["market"][: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["last"])
            tickers[symbol]["bid"] = float(_ticker["last"])
            tickers[symbol]["volume"] = float(_ticker["value"])
            tickers[symbol]["rate"] = (
                float(_ticker["close"]) / float(_ticker["open"])
            ) - 1

    return tickers
