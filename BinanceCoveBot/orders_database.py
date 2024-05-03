from datetime import datetime
from tinydb import TinyDB, Query


class OrderDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrderDB, cls).__new__(cls)
            # Define Order Schema (for data type consistency)
            cls._instance.order_schema = {
                "symbol": str,
                "open_position_order": {
                    "order_id": int,
                    "status": str,
                    "side": str,
                    "open_price": float
                },
                "targets": [
                    {
                        "order_id": int,
                        "status": str,
                        "target_price": float,
                    }
                ],
                "stop_loss": {
                    "order_id": int,
                    "value": float,
                    "status": str
                },
                "timestamp": str,
                "precision": int,
                "quantity": float,
            }
            # Initialize TinyDB database
            cls._instance.db = TinyDB('active_orders.json')
        return cls._instance

    def store_active_order(self, symbol, open_position_order_status, open_position_order_id, open_position_side,
                           targets, stop_loss_value, precision, quantity, stop_loss_status="pending", stop_loss_id=None,
                           open_price=0.0):

        # Data validation (add validation for symbol and side)
        if not isinstance(symbol, str):
            raise ValueError("symbol must be a string")
        if not isinstance(open_position_order_status, str):
            raise ValueError("open_position_order_status must be a string")
        if not isinstance(open_position_order_id, int):
            raise ValueError("open_position_order_id must be a int")
        if not isinstance(open_position_side, str):
            raise ValueError("open_position_side must be a string")
        if not isinstance(targets, list):
            raise ValueError("targets must be a list")
        if not isinstance(stop_loss_status, str):
            raise ValueError("stop_loss_status must be a string")
        if not isinstance(stop_loss_value, float):
            raise ValueError("stop_loss_id must be a int")
        if not isinstance(precision, int):
            raise ValueError("precision must be an integer")
        if not isinstance(quantity, float):
            raise ValueError("quantity must be a float")
        if not isinstance(open_price, float):
            raise ValueError("open_price must be a float")

        # Error handling for database insert
        try:
            # Create a new dictionary for the order
            new_order = {
                "symbol": symbol,
                "open_position_order": {
                    "order_id": open_position_order_id,
                    "status": open_position_order_status,
                    "side": open_position_side,
                    "open_price": open_price  # Added new field here
                },
                "targets": targets,
                "stop_loss": {
                    "order_id": stop_loss_id,
                    "value": stop_loss_value,
                    "status": stop_loss_status
                },
                "timestamp": datetime.now().isoformat(),
                "precision": precision,
                "quantity": quantity,
            }

            # Insert the new order into the database
            self.db.insert(new_order)
        except Exception as e:
            # Handle database insertion error (log it, notify admin, etc.)
            print(f"Error storing order: {e}")

    def remove_completed_order(self, position_id):
        query = Query().open_position_order.order_id == position_id
        self.db.remove(query)

    def get_active_orders(self):
        return self.db.all()

    def clear_active_orders(self):
        self.db.truncate()

    def modify_order_status(self, symbol, order_type, order_id, new_status):
        """
        Modify the status of a specific order or target.

        Args:
        symbol (str): The symbol of the order.
        order_type (str): The type of order or target to modify ('open_position_order', 'target', or 'stop_loss').
        order_id (int): The ID of the order or target to modify.
        new_status (str): The new status to set for the order or target.

        Raises:
        ValueError: If invalid order_type is provided.
        """
        # Validate order_type
        if order_type not in ['open_position_order', 'target', 'stop_loss']:
            raise ValueError("Invalid order_type. Must be 'open_position_order', 'target', or 'stop_loss'.")

        # Find the order in the database
        query = Query()
        order = self.db.get((query.symbol == symbol) & (query[order_type].order_id == order_id))
        if order:
            try:
                # Update the status
                order[order_type]['status'] = new_status
                # Update the order in the database
                self.db.update(order, (query.symbol == symbol) & (query[order_type].order_id == order_id))
            except Exception as e:
                # Handle database update error (log it, notify admin, etc.)
                print(f"Error modifying order status: {e}")
        else:
            print(f"Order with symbol '{symbol}' and ID '{order_id}' not found.")

    def get_order_by_id(self, order_id):
        """
        Get an order by its order ID.

        :param order_id: The ID of the order to retrieve.
        :return: A dictionary representing the order data if found, None otherwise.
        """
        if not isinstance(order_id, int):
            raise ValueError("order_id must be an integer")

        return self.db.get(lambda doc: doc["open_position_order"]["order_id"] == order_id)

    def modify_stop_loss(self, order_id, new_status, new_value=None):
        """
        Modify the stop loss value and status of a specific order.

        Args:
        order_id (int): The ID of the order whose stop loss to modify.
        new_status (str): The new status to set for the stop loss.
        new_value (float, optional): The new value to set for the stop loss. Defaults to None.

        Raises:
        ValueError: If order_id is not an integer.
        """
        # Validate order_id
        if not isinstance(order_id, int):
            raise ValueError("order_id must be an integer")

        # Find the order in the database
        query = Query()
        order = self.db.get((query.stop_loss.order_id == order_id))
        if order:
            try:
                # Update the stop loss status
                order['stop_loss']['status'] = new_status
                # If new_value is provided, update the stop loss value
                if new_value is not None:
                    order['stop_loss']['value'] = new_value
                # Update the order in the database
                self.db.update(order, (query.stop_loss.order_id == order_id))
            except Exception as e:
                # Handle database update error (log it, notify admin, etc.)
                print(f"Error modifying stop loss: {e}")
        else:
            print(f"Stop loss with order ID '{order_id}' not found.")
