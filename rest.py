import asyncio
import aiohttp
import logging
import os

from aiohttp import web


logger = logging.getLogger("rest")
chunk_size = 8192

class RestBridge:
    def __init__(self, bot):
        self.bot = bot

        app = aiohttp.web.Application()

        self.app = app
        self.handler = app.make_handler()

    async def start(self):
        global hostIp
        global hostPort
        loop = asyncio.get_event_loop()
        srv = await loop.create_server(self.handler, os.environ.get('IP'), os.environ.get('PORT', 8080))
        logger.info('REST 執行中: %s', srv.sockets[0].getsockname())
        self.srv = srv

    async def stop(self):
        await self.handler.finish_connections(1.0)
        self.srv.close()
        await self.srv.wait_closed()
        await self.app.finish()
