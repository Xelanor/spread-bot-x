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
