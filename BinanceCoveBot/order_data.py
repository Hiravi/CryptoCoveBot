
from cove_signal import Signal


class OrderData:
    def __init__(self, signal: Signal = None, usdt_quantity=None, current_price=None, precision=None):
        self.signal = signal
        self.usdt_quantity = usdt_quantity
        self.current_price = current_price
        self.precision = precision
        self.quantity = self.calculate_market_quantity()

    def __str__(self):
        return f"OrderData(signal={self.signal}, usdt_quantity={self.usdt_quantity}, current_price={self.current_price})"

    def calculate_market_quantity(self):
        if self.usdt_quantity is None or self.current_price is None or self.current_price == 0:
            return None
        else:
            if self.precision == 0:
                quantity = int(round(self.usdt_quantity / self.current_price, 0))
            elif self.precision == 1:
                quantity = int(round(self.usdt_quantity / self.current_price, self.precision))
            else:
                quantity = round(self.usdt_quantity / self.current_price, self.precision)

            return quantity

    def calculate_deferred_quantity(self, price):
        if self.usdt_quantity is None or price is None or price == 0:
            return None
        else:
            if self.precision == 0:
                quantity = int(round(self.usdt_quantity / price, 0))
            elif self.precision == 1:
                quantity = int(round(self.usdt_quantity / price, self.precision))
            else:
                quantity = round(self.usdt_quantity / price, self.precision)

            return quantity
