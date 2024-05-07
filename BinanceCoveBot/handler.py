from connector import get_usdt_balance, get_coin_price, new_market_targeted_position, new_deferred_targeted_position, \
    get_precision, place_target_orders, modify_stop_loss_order, cancel_target_orders, get_min_notional, \
    place_stop_loss_order
from parser import parse_message
from order_data import OrderData
from orders_database import OrderDB
from logging_config import logging
import config

logger = logging.getLogger(__name__)


async def handle_message(client, event):
    # Parse the message and extract useful data
    signal = parse_message(event.message.text)
    if signal.is_order():
        active_orders = OrderDB().get_active_orders()

        order_handled = None
        for order in active_orders:
            if signal.compare(
                    symbol=order['symbol'],
                    side=order['open_position_order']['side'],
                    open_price=order['open_position_order']['open_price'],
                    stop_loss=order['stop_loss']['value'],
            ):
                logger.info(f"Such signal already handled!")
                order_handled = True
                break

        if order_handled is not True:
            usdt_balance = get_usdt_balance(client=client)
            usdt_for_order = usdt_balance / 100 * config.PERCENT_FOR_ORDER
            current_price = get_coin_price(client=client, symbol=signal.currency_name)

            try:
                info = client.exchange_info()
                if info is not None:
                    min_notional = get_min_notional(info=info, symbol=signal.currency_name + 'USDT')
                    if min_notional is not None and min_notional <= config.MAX_NOTIONAL:
                        current_order_data = OrderData(
                            signal=signal,
                            usdt_quantity=usdt_for_order,
                            current_price=current_price,
                            precision=get_precision(info=info, symbol=signal.currency_name + 'USDT'),
                        )
                        if min(signal.between) <= current_price <= max(signal.between):
                            new_market_targeted_position(client=client, order_data=current_order_data)
                        else:
                            new_deferred_targeted_position(client=client, order_data=current_order_data)
            except Exception as e:
                logger.error(f"Error in handle_message: {e}")


def check_for_updates(client, remote_active_order):
    orders_db = OrderDB()
    local_active_orders = orders_db.get_active_orders()

    # Get and compare local and remote position orders
    open_position_orders = []
    for order in local_active_orders:
        open_position_orders.append(order)
    remote_order_ids = [order['orderId'] for order in remote_active_order]

    if local_active_orders and open_position_orders:
        try:
            handle_filled_stop(client, local_active_orders, remote_order_ids)
            handle_entered_positions(client, open_position_orders, remote_order_ids)
            handle_filled_targets(client, local_active_orders, remote_order_ids)
        except Exception as e:
            logger.error(f"Error in check_for_updates: {e}")


# Functions for handling filled stops, entered positions, and filled targets


def handle_filled_stop(client, local_active_orders, remote_order_ids):
    for order in local_active_orders:
        if order['stop_loss']['order_id'] is not None and order['stop_loss']['order_id'] not in remote_order_ids:
            try:
                cancel_target_orders(client, remote_order_ids, order['symbol'], order['targets'])
                OrderDB().remove_completed_order(order['open_position_order']['order_id'])
            except Exception as e:
                logger.error(f"Error in handle_filled_stop for order {order['symbol']}: {e}")


def handle_filled_targets(client, local_active_orders, remote_order_ids):
    for order in local_active_orders:
        if all(target == 'filled' for target in order['targets']):
            OrderDB().remove_completed_order(order)
        else:
            for index, target in enumerate(order['targets']):
                if target['order_id'] not in remote_order_ids and target['status'] == 'placed':
                    try:
                        new_stop_price = order['open_position_order']['open_price'] if index == 0 else \
                            order['targets'][index - 1]['target_price']
                        modify_stop_loss_order(
                            client=client,
                            symbol=order['symbol'],
                            side=order['open_position_order']['side'],
                            order_id=order['stop_loss']['order_id'],
                            new_stop_price=new_stop_price,
                            quantity=order['quantity'],
                        )
                    except Exception as e:
                        logger.error(f"Error in handle_filled_targets for order {order['symbol']}: {e}")


def handle_entered_positions(client, open_position_orders, remote_order_ids):
    orders_db = OrderDB()
    missing_orders = []
    for order in open_position_orders:
        if order['open_position_order']['order_id'] not in remote_order_ids:
            missing_orders.append(order)

    for order_data in missing_orders:
        if order_data['open_position_order']['status'] != 'filled':
            try:
                stop_loss_order = place_stop_loss_order(
                    client=client,
                    symbol=order_data['symbol'],
                    side=order_data['open_position_order']['side'],
                    quantity=order_data['quantity'],
                    stop_price=order_data['stop_loss']['value']
                )

                orders_db.modify_stop_loss(order_id=stop_loss_order['orderId'], new_status="placed")
                order_id = order_data['open_position_order']['order_id']
                orders_db.modify_order_status(symbol=order_data['symbol'], order_id=int(order_id),
                                              order_type='open_position_order', new_status='filled')

                # Place target orders
                current_order = orders_db.get_order_by_id(order_id=order_id)
                position = None
                try:
                    position = client.get_position_risk(symbol=current_order['symbol'] + 'USDT')
                except Exception as e:
                    print(f"An error occurred while getting position risk: {e}")

                if position is not None:
                    amt = float(position[0]['positionAmt'])
                else:
                    amt = 0.0

                if amt != 0.0:
                    target_orders = place_target_orders(
                        client=client,
                        symbol=current_order['symbol'],
                        side=current_order['open_position_order']['side'],
                        targets=[target['target_price'] for target in current_order['targets']],
                        quantity=current_order['quantity'],
                        precision=current_order['precision'],
                    )

                    orders_db.update_targets(
                        order_id=order_data['open_position_order']['order_id'],
                        new_status='placed',
                        new_target_ids=[order['orderId'] for order in target_orders]
                    )

            except Exception as e:
                logger.error(f"Error in handle_entered_positions for order {order_data['symbol']}: {e}")
