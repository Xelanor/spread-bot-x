import json

from tenacity import retry, stop, wait
from django.core.management.base import BaseCommand, CommandError
from spread.models import SpreadBot
from spread.tasks import run_spread_task, run_spread_depth_cacher_bot


@retry(stop=stop.stop_after_attempt(100), wait=wait.wait_fixed(5))
def open_bots():
    with open("json/spread_bots.json", "r") as outfile:
        bots = json.load(outfile)

    for bot in bots:
        bot_id = bot["bot_id"]
        buy_status = bot["buy"]
        sell_status = bot["sell"]

        if buy_status or sell_status:
            run_spread_depth_cacher_bot.delay(bot_id)

        if buy_status:
            bot = SpreadBot.objects.get(id=bot_id)
            bot.buy_status = True
            bot.save()
            run_spread_task.delay(bot_id, "buy")
            print(f"Bot: {bot.id} buy started ({bot.ticker})")

        if sell_status:
            bot = SpreadBot.objects.get(id=bot_id)
            bot.sell_status = True
            bot.save()
            run_spread_task.delay(bot_id, "sell")
            print(f"Bot: {bot.id} sell started ({bot.ticker})")


class Command(BaseCommand):
    def handle(self, *args, **options):
        open_bots()
