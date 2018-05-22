import logging
import asyncio
import os

from bot import bot
from rest import RestBridge

rest = RestBridge(bot)

async def start():
    await rest.start()
    await bot.loop()


async def stop():
    await rest.stop()


if __name__ == '__main__':
    loglevel = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
    logging.basicConfig(level=loglevel)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(stop())
