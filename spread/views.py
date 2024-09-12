from datetime import datetime, timedelta
import asyncio
import json

from django.db.models import Sum, FloatField
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from django.db.models import Q
from django.core.cache import cache

from spread.models import SpreadBot, SpreadBotTx


def get_profits(bot):
    profit_today = SpreadBotTx.objects.filter(
        bot=bot,
        created_at__gte=now().replace(hour=0, minute=0, second=0),
        side="sell",
    ).aggregate(profit_today=Coalesce(Sum("profit"), 0, output_field=FloatField()))[
        "profit_today"
    ]
    profit_24hours = SpreadBotTx.objects.filter(
        bot=bot,
        created_at__gte=now() - timedelta(hours=24),
        side="sell",
    ).aggregate(profit_24hours=Coalesce(Sum("profit"), 0, output_field=FloatField()))[
        "profit_24hours"
    ]
    profit_7days = SpreadBotTx.objects.filter(
        bot=bot,
        created_at__gte=now() - timedelta(days=7),
        side="sell",
    ).aggregate(profit_7days=Coalesce(Sum("profit"), 0, output_field=FloatField()))[
        "profit_7days"
    ]
    profit_30days = SpreadBotTx.objects.filter(
        bot=bot,
        created_at__gte=now() - timedelta(days=30),
        side="sell",
    ).aggregate(profit_30days=Coalesce(Sum("profit"), 0, output_field=FloatField()))[
        "profit_30days"
    ]
    profit_total = SpreadBotTx.objects.filter(bot=bot, side="sell").aggregate(
        profit_total=Coalesce(Sum("profit"), 0, output_field=FloatField())
    )["profit_total"]

    profits = {
        "profit_today": profit_today,
        "profit_24hours": profit_24hours,
        "profit_7days": profit_7days,
        "profit_30days": profit_30days,
        "profit_total": profit_total,
    }
    return profits


@api_view(["GET"])
def spread_bots_data(request):
    data = {"bots": []}

    query = SpreadBot.objects.all()

    for bot in query:
        bot_dict = {}
        settings = {
            "id": bot.id,
            "ticker": bot.ticker,
            "exchange": bot.exchange.name,
            "point": bot.point,
            "budget": bot.budget,
            "spread_rate": bot.spread_rate,
            "average_price": bot.average_price,
            "sellable_quantity": bot.sellable_quantity,
            "max_size": bot.max_size,
            "profit_rate": bot.profit_rate,
            "take_profit_rate": bot.take_profit_rate,
            "average_correction_minutes": bot.average_correction_minutes,
            "average_correction_rate": bot.average_correction_rate,
            "buy_status": bot.buy_status,
            "sell_status": bot.sell_status,
            "last_buy_order_date": bot.last_buy_order_date,
            "last_sell_order_date": bot.last_sell_order_date,
            "last_sell_order_date_raw": bot.last_sell_order_date_raw,
            "created_at": bot.created_at,
        }
        bot_dict["settings"] = settings
        bot_dict["profits"] = get_profits(bot)

        data["bots"].append(bot_dict)

    return Response(data)


@api_view(["POST"])
def get_spread_transactions(request):
    if request.method == "POST":
        body = request.data
        bot_id = body["bot_id"]
        full = body.get("full", None)

        if bot_id == "all-transactions":
            last_24_hours = now() - timedelta(hours=6)
            query = transactions = SpreadBotTx.objects.filter(
                created_at__gte=last_24_hours
            )
        else:
            if full:
                query = transactions = SpreadBotTx.objects.filter(bot_id=bot_id)
            else:
                last_3_days = now() - timedelta(days=2)
                query = transactions = SpreadBotTx.objects.filter(
                    bot_id=bot_id, created_at__gte=last_3_days
                )

        transactions = query.order_by("-created_at").values(
            "bot__ticker",
            "bot__exchange__name",
            "buy_price",
            "sell_price",
            "quantity",
            "fee",
            "profit",
            "side",
            "condition",
            "created_at",
        )

        total_profit = 0
        total_volume = 0
        for transaction in transactions:
            total_profit += transaction["profit"]
            if transaction["side"] == "buy":
                total_volume += transaction["quantity"] * transaction["buy_price"]
            else:
                total_volume += transaction["quantity"] * transaction["sell_price"]

        ticker = transactions[0]["bot__ticker"] if transactions else None
        ticker = "All Transactions" if bot_id == "all-transactions" else ticker

        return Response(
            {
                "ticker": ticker,
                "transactions": transactions,
                "total_profit": total_profit,
                "total_volume": total_volume,
            }
        )


@api_view(["POST"])
def average_correction(request):
    if request.method == "POST":
        body = request.data
        bot_id = body["bot_id"]
        new_average = body["new_average"]

        bot = SpreadBot.objects.get(id=bot_id)

        transaction = {
            "bot_id": bot_id,
            "side": "sell",
            "buy_price": bot.average_price,
            "sell_price": new_average,
            "quantity": bot.sellable_quantity,
            "fee": 0,
            "condition": "OD",
        }

        profit = (transaction["sell_price"] - transaction["buy_price"]) * transaction[
            "quantity"
        ]

        if profit < 0:
            transaction["profit"] = profit
            tx = SpreadBotTx.objects.create(**transaction)

            bot.average_price = new_average

        bot.last_sell_order_date = now()
        bot.save()

        return Response({"result": "ok"})


@api_view(["POST"])
def budget_update(request):
    if request.method == "POST":
        body = request.data
        bot_id = body["bot_id"]
        new_budget = body["new_budget"]

        bot = SpreadBot.objects.get(id=bot_id)
        bot.budget = new_budget

        bot.save()
        return Response({"result": "ok"})


def get_bot_total_profit(bot_id):
    profit = SpreadBotTx.objects.filter(bot_id=bot_id).aggregate(
        total=Coalesce(Sum("profit"), 0.0),
    )
    return profit


@api_view(["GET"])
def spread_historical_data(request):
    bots = []

    _bots = (
        SpreadBot.objects.filter()
        .order_by("-created_at")
        .values("id", "ticker", "exchange__name", "created_at")
    )

    for bot in _bots:
        bot_id = bot["id"]
        profit = get_bot_total_profit(bot_id)
        bot["profit"] = profit["total"]
        try:
            get_bot_latest_tx = (
                SpreadBotTx.objects.filter(bot_id=bot_id)
                .order_by("-created_at")
                .values("created_at")
                .first()
            )
            bot["latest_tx"] = get_bot_latest_tx["created_at"]
        except:
            bot["latest_tx"] = None
        bots.append(bot)

    return Response(bots)
