import json
from django.core.management.base import BaseCommand, CommandError
from spread.models import SpreadBot
import os


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not os.path.exists("json"):
            os.makedirs("json")

        bots = SpreadBot.objects.all()
        bots_dict = []
        for bot in bots:
            print(
                f"{bot.id} - {bot.ticker} - buy:{bot.buy_status} - sell:{bot.sell_status}"
            )
            buy_status = bot.buy_status
            sell_status = bot.sell_status
            bots_dict.append(
                {
                    "bot_id": bot.id,
                    "buy": buy_status,
                    "sell": sell_status,
                }
            )
            bot.buy_status = False
            bot.sell_status = False
            bot.save()

        with open("json/spread_bots.json", "w") as outfile:
            json.dump(bots_dict, outfile)
