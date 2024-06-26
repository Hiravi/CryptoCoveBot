from order_data import OrderData
from binance.um_futures import UMFutures as Client
from binance.error import ClientError
from orders_database import OrderDB
from logging_config import logging

logger = logging.getLogger(__name__)


def get_usdt_balance(client, asset='USDT'):
    balance = client.balance()
    asset_balance = None
    for asset_info in balance:
        if asset_info['asset'] == asset:
            asset_balance = float(asset_info['balance'])
            break  # Exit the loop after finding the balance
    if asset_balance is None:
        logging.warning(f"Couldn't find balance for asset {asset}")
    return asset_balance


def get_coin_price(client, symbol):
    try:
        data = client.ticker_price(symbol + 'USDT')
        price = float(data['price'])
        return price
    except Exception as e:
        logging.error(f"Error getting price for symbol {symbol}: {e}")
        return None


def place_target_orders(client: Client, symbol, side, targets, quantity, precision):
    placed_orders = []
    targeted_asset = 0
    for index, target_price in enumerate(targets):
        if precision == 0:
            target_quantity = int(round(quantity / len(targets), precision))
        else:
            target_quantity = round(quantity / len(targets), precision)
        try:
            order = client.new_order(
                symbol=symbol + 'USDT',
                side='SELL' if side == 'BUY' else 'BUY',
                type='LIMIT',
                timeInForce='GTC',
                price=target_price,
                quantity=target_quantity if index < len(targets) - 1 else round(quantity - targeted_asset, 3),
            )

            placed_orders.append(order)
            targeted_asset += target_quantity
            logging.info(f"TP order placed for symbol {symbol}: {order}")
        except Exception as e:
            logging.error(f"Error placing target order {index + 1} for {symbol}: {e}")
        except ClientError as e:
            # Check for specific error code
            if e.error_code == -2021 and "Order would immediately trigger." in str(e):
                try:
                    order = client.new_order(
                        symbol=symbol + 'USDT',
                        side='SELL' if side == 'BUY' else 'BUY',
                        type='MARKET',
                        quantity=target_quantity if index < len(targets) - 1 else round(quantity - targeted_asset, 3),
                    )

                    logging.warning(
                        f"Target price {target_price} for {symbol} might be too close to current market price. Place.")
                except Exception as e:
                    # Handle other ClientErrors
                    logging.error(f"Error placing target order {index + 1} for {symbol}: {e}")
            else:
                # Handle other ClientErrors
                logging.error(f"Error placing target order {index + 1} for {symbol}: {e}")
    return placed_orders


def new_market_targeted_position(client, order_data: OrderData):
    client.change_leverage(symbol=order_data.signal.currency_name + 'USDT', leverage=order_data.signal.leverage)
    logging.info(f"Setting leverage to {order_data.signal.leverage} for {order_data.signal.currency_name}")

    try:
        client.change_margin_type(symbol=order_data.signal.currency_name + 'USDT', marginType='ISOLATED')
    except Exception as e:
        if 'No need to change margin type.' in str(e):
            logging.info("Margin type already set to ISOLATED.")
        else:
            logging.error(f"Error changing margin type for {order_data.signal.currency_name}: {e}")
            raise e  # Re-raise other exceptions

    order = client.new_order(
        symbol=order_data.signal.currency_name + 'USDT',
        side=order_data.signal.order_type,
        type='MARKET',
        quantity=order_data.quantity
    )
    stop_loss_order = place_stop_loss_order(
        client=client,
        symbol=order_data.signal.currency_name,
        side=order_data.signal.order_type,
        quantity=order_data.quantity,
        stop_price=order_data.signal.stop_loss,
    )
    target_orders = place_target_orders(client, order_data.signal.currency_name, order_data.signal.order_type,
                                        order_data.signal.targets, order_data.quantity, order_data.precision)

    order_db = OrderDB()
    targets = []
    for index, target_price in enumerate(order_data.signal.targets):
        target = {
            "order_id": target_orders[index]['orderId'],
            "status": "placed",
            "target_price": target_price
        }
        targets.append(target)

    order_db.store_active_order(
        symbol=order_data.signal.currency_name,
        open_position_order_id=order['orderId'],
        open_position_order_status='filled',
        open_position_side=order_data.signal.order_type,
        targets=targets,
        stop_loss_id=stop_loss_order['orderId'],
        stop_loss_status='placed',
        stop_loss_value=order_data.signal.stop_loss,
        precision=order_data.precision,
        quantity=float(order_data.quantity),
        open_price=order_data.current_price,
    )

    logging.info(f"Order {order['orderId']} placed as market order")


def new_deferred_targeted_position(client, order_data: OrderData):
    try:
        client.change_leverage(symbol=order_data.signal.currency_name + 'USDT', leverage=order_data.signal.leverage)
    except Exception as e:  # Catch any error during leverage change
        logging.error(f"Error changing leverage: {e}")

    try:
        client.change_margin_type(symbol=order_data.signal.currency_name + 'USDT', marginType='ISOLATED')
    except Exception as e:  # Catch any error during margin type change
        if 'No need to change margin type.' in str(e):
            logging.info("Margin type is already set to ISOLATED. No need to change.")
        else:
            logging.error(f"Error changing margin type: {e}")

    lower_bound = min(order_data.signal.between)
    higher_bound = max(order_data.signal.between)
    entry_price = lower_bound if order_data.current_price < lower_bound else higher_bound

    order_data.quantity = order_data.calculate_deferred_quantity(entry_price)

    order = client.new_order(
        symbol=order_data.signal.currency_name + 'USDT',
        side=order_data.signal.order_type,
        type='LIMIT',  # Change from 'MARKET' to 'LIMIT'
        timeInForce='GTC',  # Good 'Til Canceled, or you can use 'IOC' (Immediate or Cancel) or 'FOK' (Fill or Kill)
        quantity=order_data.quantity,
        price=entry_price,
    )

    print("Order placed successfully:", order)

    order_db = OrderDB()

    targets = []
    for target_price in order_data.signal.targets:
        target = {
            "order_id": None,
            "status": "pending",
            "target_price": target_price
        }
        targets.append(target)

    order_db.store_active_order(
        symbol=order_data.signal.currency_name,
        open_position_order_id=order['orderId'],
        open_position_side=order_data.signal.order_type,
        open_position_order_status='placed',
        targets=targets,
        stop_loss_value=order_data.signal.stop_loss,
        precision=order_data.precision,
        quantity=float(order_data.quantity),
        open_price=entry_price,
    )

    logging.info(f"Order {order['orderId']} placed as deferred order")


def get_precision(info, symbol):
    try:
        # Iterate over symbols in the exchange information
        for x in info['symbols']:
            # Check if the symbol matches the one we are interested in
            if x['symbol'] == symbol:
                # Return the precision of the quantity for this symbol
                return int(x['quantityPrecision'])

        # If the symbol is not found
        raise ValueError(f"Symbol '{symbol}' not found in exchange information.")
    except Exception as e:
        logging.error(f"Error getting precision for {symbol}: {e}")
        raise  # Re-raise the exception for critical functions


def get_min_notional(info, symbol):
    try:
        for x in info['symbols']:
            if x['symbol'] == symbol:
                for notional_filter in x['filters']:
                    if notional_filter['filterType'] == "MIN_NOTIONAL":
                        return int(notional_filter['notional'])
                # Minimum notional not found in filters, return None
                return None
        raise ValueError(f"Symbol '{symbol}' not found in exchange information.")
    except Exception as e:
        logging.error("An error occurred:", e)
        return None


def place_stop_loss_order(client, symbol, side, quantity, stop_price):
    try:
        order = client.new_order(
            symbol=symbol + 'USDT',
            side='SELL' if side == 'BUY' else 'BUY',
            type='STOP_MARKET',
            quantity=quantity,
            stopPrice=stop_price
        )

        return order
    except ClientError as e:
        if e.error_code == -2021:  # Handle specific error code for immediate trigger
            logging.error(
                f"Stop-loss order not placed because price already reached stop price ({stop_price}) for {symbol}.")
        else:
            logging.error(f"Failed to place stop-loss order: {e}", e)


def cancel_target_orders(client, remote_order_ids, symbol, targets):
    for target in targets:
        if target['order_id'] in remote_order_ids:
            if target['status'] == 'placed':
                try:
                    client.cancel_order(symbol=symbol + 'USDT', orderId=target['order_id'])
                    logging.info(f"Target order (ID: {target['order_id']}) cancelled successfully.")
                except Exception as e:
                    logging.error(f"Failed to cancel target order (ID: {target['order_id']}):", e)


def cancel_expired_order(client, order):
    symbol = order['symbol']

    try:
        client.cancel_order(symbol=symbol + 'USDT', orderId=order['open_position_order']['order_id'])

    except Exception as e:
        logging.error(f"Failed to cancel expired order (ID: {order['open_position_order']['order_id']}. Cause: {e}")


def modify_stop_loss_order(client, symbol, side, order, new_stop_price, quantity):
    try:
        order_id = order['stop_loss']['order_id']
        # Fetch the existing order details to ensure accuracy
        original_order = client.get_open_orders(symbol=symbol + 'USDT', orderId=order_id)

        # Validate that the order is indeed a stop-loss order
        if original_order['type'] != 'STOP_MARKET':
            raise ValueError("Order is not a stop-loss order.")

        client.cancel_order(symbol=symbol + 'USDT', orderId=order_id)

        modified_order = place_stop_loss_order(
            client=client,
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=new_stop_price,
        )

        OrderDB().modify_stop_loss(order['open_position_order']['order_id'], 'placed', new_id=modified_order['orderId'], new_value=new_stop_price)

        logging.info(f"Stop-loss order (ID: {order_id}) modified successfully.")
        return modified_order

    except Exception as e:
        logging.error(f"Failed to modify stop-loss order: {e}", e)
        return None
