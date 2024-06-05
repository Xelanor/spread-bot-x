from django.contrib import admin

from spread import models


@admin.register(models.Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(models.ExchangeApi)
class ExchangeApiAdmin(admin.ModelAdmin):
    list_display = ("exchange", "public_key")
    search_fields = ("exchange__name", "public_key")


@admin.register(models.SpreadBot)
class SpreadBotAdmin(admin.ModelAdmin):
    list_display = ("ticker", "buy_status", "sell_status", "created_at")
    search_fields = ("ticker",)


@admin.register(models.SpreadBotTx)
class SpreadBotTxAdmin(admin.ModelAdmin):
    list_display = (
        "bot",
        "buy_price",
        "sell_price",
        "profit",
        "created_at",
    )
    search_fields = ("bot__ticker",)
