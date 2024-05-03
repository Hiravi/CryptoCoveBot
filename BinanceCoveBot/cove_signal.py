class Signal:
    def __init__(self, order_type=None, between=None, targets=None, stop_loss=None, leverage=None, currency_name=None):
        self.order_type = order_type
        self.between = between
        self.targets = targets
        self.stop_loss = stop_loss
        self.leverage = leverage
        self.currency_name = currency_name

    def __str__(self):
        return (
            f"Order type: {self.order_type}, "
            f"Between: {self.between}, "
            f"Targets: {self.targets}, "
            f"Stop Loss: {self.stop_loss}, "
            f"Leverage: {self.leverage}, "
            f"Currency Name: {self.currency_name}"
        )

    def is_order(self):
        return (
            self.order_type is not None
            and self.between is not None
            and self.targets is not None
            and self.stop_loss is not None
            and self.currency_name is not None
        )
