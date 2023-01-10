# -*- coding: utf-8 -*-
import asyncio
from argparse import ArgumentParser
from multiprocessing import Process

from tortoise import Tortoise, run_async
from websockets import serve

from hex_forest.config import config
from hex_forest.http_server import HttpServer
from hex_forest.ws_server import WsServer


async def start_database():
    print("initializing database...")
    await Tortoise.init(db_url=config.db_url, modules={"models": ["hex_forest.models"]})
    try:
        await Tortoise.generate_schemas()
    except:
        pass


def start_websocket():
    import uvloop
    uvloop.install()

    async def serve_websocket():
        print("starting websocket server...")
        async with serve(WsServer().listen, config.ws_host, config.ws_port):
            await asyncio.Future()  # run forever
    asyncio.run(serve_websocket())


parser = ArgumentParser()
parser.add_argument("-t", "--target", choices=["http", "ws", "both"], default="both")

args = parser.parse_args()

run_async(start_database())

if args.target == "ws":
    start_websocket()

elif args.target == "http":
    HttpServer().run("0.0.0.0", config.http_port)

else:
    websocket_server = Process(target=start_websocket)
    websocket_server.start()

    HttpServer().run("0.0.0.0", config.http_port)
