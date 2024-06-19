from exchanges.mexc.mexc_api_class import MexcAPI
from exchanges.mexc.mexc_ws_class import MexcWS

from exchanges.bitmart.bitmart_api_class import BitmartAPI
from exchanges.bitmart.bitmart_ws_class import BitmartWS

from exchanges.kucoin.kucoin_api_class import KucoinAPI
from exchanges.kucoin.kucoin_ws_class import KucoinWS

from exchanges.bingx.bingx_api_class import BingXAPI
from exchanges.bingx.bingx_ws_class import BingXWS

from exchanges.bybit.bybit_api_class import BybitAPI
from exchanges.bybit.bybit_ws_class import BybitWS

from exchanges.bitget.bitget_api_class import BitgetAPI
from exchanges.bitget.bitget_ws_class import BitgetWS

from exchanges.xt.xt_api_class import XtAPI
from exchanges.xt.xt_ws_class import XtWS

from exchanges.htx.htx_api_class import HtxAPI
from exchanges.htx.htx_ws_class import HtxWS

api_classes = {
    "Mexc": MexcAPI,
    "Bitmart": BitmartAPI,
    "Kucoin": KucoinAPI,
    "BingX": BingXAPI,
    "Bybit": BybitAPI,
    "Bitget": BitgetAPI,
    "XT": XtAPI,
    "Htx": HtxAPI,
}

ws_classes = {
    "Mexc": MexcWS,
    "Bitmart": BitmartWS,
    "Kucoin": KucoinWS,
    "BingX": BingXWS,
    "Bybit": BybitWS,
    "Bitget": BitgetWS,
    "XT": XtWS,
    "Htx": HtxWS,
}
