from ..base import order as od
from .api import BitmexApi
from ..etc.util import unix_time_from_ISO8601Z


class BitmexOrderManager(od.OrderManagerBase):
    def _after_auth(self):
        self.ws.subscribe('execution', self.__on_events)

    def _generate_order_object(self, e):
        info = e.info
        api = BitmexApi.ccxt_instance()
        symbol = api.markets_by_id[info['symbol']]['symbol']
        return od.Order(
            symbol, info['ordType'].lower(), info['side'].lower(),
            info['orderQty'], info['price'])

    def __on_events(self, msg):
        if msg['action'] != 'insert':
            return

        for e in msg['data']:
            oe = od.OrderEvent()
            oe.info = e
            oe.id = e['orderID']
            oe.ts = unix_time_from_ISO8601Z(e['timestamp'])

            t = e['ordStatus']
            size = e['lastQty']
            if size:
                oe.type = od.EVENT_EXECUTION
                oe.price = e['lastPx']
                oe.size = size if e['side'] == 'Buy' else -size
            elif t == 'New':
                oe.type = od.EVENT_OPEN
            elif t == 'Filled':
                oe.type = od.EVENT_CLOSE
            elif t == 'Canceled':
                oe.type = od.EVENT_CANCEL

            self._handle_order_event(oe)


class BitmexPositionGroup(od.PositionGroupBase):
    SIZE_IN_FIAT = True

    def __init__(self):
        super().__init__()
        self.commission = 0  # total commissions in USD

    def update(self, price, size, info):
        super().update(price, size)
        commission = info['commission'] * size
        self.commission += commission
        self.pnl -= commission


class BitmexOrderGroup(od.OrderGroupBase):
    PositionGroup = BitmexPositionGroup


class BitmexOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitmexOrderGroup
