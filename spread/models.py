from django.db import models
from django.utils.timezone import now


class Exchange(models.Model):
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name


class ExchangeApi(models.Model):
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, db_index=True)
    public_key = models.CharField(max_length=255)
    private_key = models.CharField(max_length=255)
    group = models.CharField(max_length=255, blank=True, null=True)
    kyc = models.CharField(max_length=255, default="", db_index=True)

    def __str__(self):
        return f"{self.exchange.name} - {self.kyc}"


class SpreadBot(models.Model):
    """SpreadTrader bot model class"""

    ticker = models.CharField(max_length=255)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, db_index=True)
    settings = models.JSONField()
    buy_status = models.BooleanField(default=False)
    sell_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        status = "Pasif"
        if self.buy_status == True or self.sell_status == True:
            status = "Aktif"
        return f"{self.exchange} - {self.ticker} - {status}"


class SpreadBotTx(models.Model):
    """SpreadTrader transactions model class"""

    bot = models.ForeignKey(SpreadBot, on_delete=models.CASCADE, db_index=True)
    SIDE_CHOICES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, default="buy")

    buy_price = models.FloatField()
    sell_price = models.FloatField(blank=True, null=True)
    quantity = models.FloatField()
    fee = models.FloatField()
    profit = models.FloatField()
    condition = models.CharField(max_length=255, default="M")
    created_at = models.DateTimeField(default=now, db_index=True)

    def __str__(self):
        return f"{self.bot.ticker} - {self.created_at}"
