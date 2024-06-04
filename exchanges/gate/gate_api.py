from .utils import request


def get_gate_tickers():
    url = "/spot/tickers"
    params = {"category": "spot"}
    res = request("GET", url, params=params)

    tickers = {}

    denominator = "USDT"
    for _ticker in res["result"]["list"]:
        if _ticker["symbol"].endswith(denominator):
            nominator = _ticker["symbol"][: -len(denominator)]

            symbol = f"{nominator}/{denominator}"
            tickers[symbol] = {}

            tickers[symbol]["ask"] = float(_ticker["ask1Price"])
            tickers[symbol]["bid"] = float(_ticker["bid1Price"])
            tickers[symbol]["volume"] = float(_ticker["volume24h"]) * float(
                _ticker["bid1Price"]
            )
            tickers[symbol]["rate"] = float(_ticker["price24hPcnt"])

    return tickers
