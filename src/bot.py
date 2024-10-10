import asyncio
import datetime
import json
import logging
import os

import websockets
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(level=logging.INFO)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', '.env'))

# replace !forceOrder@arr to <symbol>@forceOrder for specific crypto liquidation alert
URL = os.getenv("URL", "wss://fstream.binance.com/ws/!forceOrder@arr")
THRESHOLD = int(os.getenv("THRESHOLD", 50000))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL")
bot = Bot(token=BOT_TOKEN)


async def gateData(rawData):  # check the raw data's liquidation value
    if rawData.get('e') == 'forceOrder':
        avgPrice = float(rawData['o']['ap'])
        origQuantity = float(rawData['o']['q'])

        liqValue = avgPrice * origQuantity

        if liqValue >= THRESHOLD:
            await processMessage(rawData, liqValue, avgPrice)


def get_emoji(liqValue):  # add fire emoji to the message
    if liqValue >= 10000000:
        return "🔥🔥🔥"
    elif liqValue >= 1000000:
        return "🔥🔥"
    elif liqValue >= 100000:
        return "🔥"
    return ""


async def processMessage(rawData, liqValue, avgPrice):  # raw data to processed message
    symbol = rawData['o']['s']
    liqPrice = f"{avgPrice:.8g}"
    formatted_liqValue = f"{int(liqValue):,.2f}"
    side = "Long" if rawData['o']['S'] == "SELL" else "Short"
    chart_emoji = "📉" if side == "Long" else "📈"
    fire_emoji = get_emoji(liqValue)

    liqMessage = (
        f"{chart_emoji} #{symbol} Liquidated {side} at\n"
        f"${liqPrice}: ${formatted_liqValue}{fire_emoji}"
    )

    await sendMessage(CHANNEL_ID, liqMessage)


async def sendMessage(channel_id, liqMessage):  # send message to telegram channel
    try:
        await bot.send_message(channel_id, text=liqMessage)
        logging.info(f"sendMessage at {datetime.datetime.now()}: {liqMessage}")
    except Exception as e:
        logging.error(f"Error sendMessage: {e}")


async def connect_websocket():  # websocket connection
    while True:
        try:
            async with websockets.connect(URL) as ws:
                logging.info(
                    f"WebSocket connected at {datetime.datetime.now()}.")
                while True:
                    await gateData(json.loads(await ws.recv()))
        except websockets.exceptions.ConnectionClosedError as e:
            logging.warning(f"WebSocket Connection Closed. Retrying... ({e})")
        except Exception as e:
            logging.error(f"Unknown error occurred... ({e})")
        await asyncio.sleep(5)


async def main():
    await connect_websocket()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt...")
