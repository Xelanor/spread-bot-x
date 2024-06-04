import asyncio
from channels.db import database_sync_to_async

from exchanges.api_classes import api_classes

from exchanges.mexc import mexc_api
from exchanges.bitmart import bitmart_api
from exchanges.bybit import bybit_api
from exchanges.kucoin import kucoin_api
from exchanges.bingx import bingx_api
from exchanges.bitget import bitget_api
from exchanges.ascendex import ascendex_api
from exchanges.coinex import coinex_api
from exchanges.xt import xt_api

from maker.models import ExchangeApi

exchange_functions = {
    "Mexc": {
        "tickers": mexc_api.get_mexc_tickers,
        "depth": mexc_api.get_mexc_depth,
        "allowed": mexc_api.get_allowed_symbols,
    },
    "Bitmart": {
        "tickers": bitmart_api.get_bitmart_tickers,
        "depth": bitmart_api.get_bitmart_depth,
    },
    "Bybit": {
        "tickers": bybit_api.get_tickers,
        "depth": bybit_api.get_depth,
    },
    "Kucoin": {
        "tickers": kucoin_api.get_tickers,
        "depth": kucoin_api.get_depth,
    },
    "BingX": {
        "tickers": bingx_api.get_tickers,
        "depth": bingx_api.get_depth,
        "allowed": bingx_api.get_allowed_symbols,
    },
    "Bitget": {
        "tickers": bitget_api.get_tickers,
    },
    "Ascendex": {
        "tickers": ascendex_api.get_tickers,
    },
    "Coinex": {
        "tickers": coinex_api.get_tickers,
    },
    "XT": {
        "tickers": xt_api.get_tickers,
        "allowed": xt_api.get_allowed_symbols,
    },
}


async def async_exchange_tickers(exchanges):
    tickers = {}
    loop = asyncio.get_event_loop()
    tasks = []
    _exchanges = []
    for exchange in exchanges:
        tasks.append(
            loop.run_in_executor(None, exchange_functions[exchange]["tickers"])
        )
        _exchanges.append(exchange)

    results = await asyncio.gather(*tasks)
    for index, exchange in enumerate(exchanges):
        tickers[exchange] = results[index]

    return tickers


@database_sync_to_async
def get_exchange_api_model(exchange):
    return ExchangeApi.objects.get(exchange__name=exchange)


async def async_exchange_balances(apis):
    balances = {}
    loop = asyncio.get_event_loop()
    tasks = []
    exchange_api_pairs = []
    for exchange in apis:
        for api in apis[exchange]:
            tasks.append(loop.run_in_executor(None, api.get_account_balance))
            exchange_api_pairs.append((exchange, api))

    results = await asyncio.gather(*tasks)

    for (exchange, api), result in zip(exchange_api_pairs, results):
        if exchange not in balances:
            balances[exchange] = {}
        balances[exchange][api.kyc] = result

    return balances


async def async_exchange_allowed_symbols(exchanges):
    tickers = {}
    loop = asyncio.get_event_loop()
    tasks = []
    _exchanges = []
    for exchange in exchanges:
        if "allowed" not in exchange_functions[exchange]:
            continue

        tasks.append(
            loop.run_in_executor(None, exchange_functions[exchange]["allowed"])
        )
        _exchanges.append(exchange)

    results = await asyncio.gather(*tasks)
    for index, exchange in enumerate(_exchanges):
        tickers[exchange] = results[index]

    return tickers


async def async_exchange_asset_details(apis):
    details = {}
    loop = asyncio.get_event_loop()
    tasks = []
    exchange_api_pairs = []
    for exchange in apis:
        for api in apis[exchange]:
            if not (
                hasattr(api, "get_asset_details") and callable(api.get_asset_details)
            ):
                continue

            tasks.append(loop.run_in_executor(None, api.get_asset_details))
            exchange_api_pairs.append((exchange, api))

    results = await asyncio.gather(*tasks)
    for (exchange, api), result in zip(exchange_api_pairs, results):
        if exchange not in details:
            details[exchange] = {}
        details[exchange][api.kyc] = result

    return details


async def async_exchange_withdrawal_details(apis):
    details = {}
    loop = asyncio.get_event_loop()
    tasks = []
    _exchanges = []
    for exchange in apis:
        if not (
            hasattr(apis[exchange], "get_withdrawals")
            and callable(apis[exchange].get_withdrawals)
        ):
            continue

        tasks.append(loop.run_in_executor(None, apis[exchange].get_withdrawals))
        _exchanges.append(exchange)

    results = await asyncio.gather(*tasks)
    for index, exchange in enumerate(_exchanges):
        details[exchange] = results[index]

    return details


async def async_exchange_deposit_details(apis):
    details = {}
    loop = asyncio.get_event_loop()
    tasks = []
    exchange_api_pairs = []
    for exchange in apis:
        for api in apis[exchange]:
            if not (hasattr(api, "get_deposits") and callable(api.get_deposits)):
                continue

            tasks.append(loop.run_in_executor(None, api.get_deposits))
            exchange_api_pairs.append((exchange, api))

    results = await asyncio.gather(*tasks)
    for (exchange, api), result in zip(exchange_api_pairs, results):
        if exchange not in details:
            details[exchange] = {}
        details[exchange][api.kyc] = result

    return details
