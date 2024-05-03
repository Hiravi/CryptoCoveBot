class PlacedOrder:
    def __init__(self, order_id, order_type):
        order_id = order_id
        order_type = order_type


class PostOrders:
    def __init__(self):
        self.orders = []

    def add_order(self, order: PlacedOrder):
        self.orders.append(order)



