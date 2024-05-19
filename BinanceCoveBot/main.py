import asyncio
from tenacity import retry, wait_exponential
import config
from binance.um_futures import UMFutures as Client
from telethon import TelegramClient, events
from handler import handle_message, check_for_updates
from logging_config import logging
from requests import get

logger = logging.getLogger(__name__)

tg_client = TelegramClient(
    'covebot', int(config.API_ID), config.API_HASH,
)
client = Client(
    key=config.BINANCE_API_KEY,
    secret=config.BINANCE_API_SECRET,
)


@retry(wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_balance():
    # Check internet connectivity before API call
    if not get("https://google.com").ok:
        raise ConnectionError("No internet connection")
    return client.balance()


@tg_client.on(events.NewMessage(chats=int(config.CHANNEL_USERNAME)))
async def my_event_handler(event):
    print(event.message)
    try:
        await handle_message(client, event)
    except Exception as e:
        print(f"Error in handle_message: {e}")


async def binance_loop():
    while True:
        try:
            balance = await get_balance()
            print(balance)
            orders = client.get_orders()
            check_for_updates(client=client, remote_active_orders=orders)
            print(orders)
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
        await asyncio.sleep(10)


async def main():
    await tg_client.start(config.PHONE_NUMBER)
    # Launch binance_loop as a separate task
    binance_task = asyncio.create_task(binance_loop())
    try:
        # Run Telegram client until disconnected
        await tg_client.run_until_disconnected()
    finally:
        await binance_task


if __name__ == '__main__':
    asyncio.run(main())
