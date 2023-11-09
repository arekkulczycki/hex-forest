# -*- coding: utf-8 -*-
import asyncio
import ssl
from argparse import ArgumentParser
from multiprocessing import Process

from tortoise import Tortoise, run_async
from websockets import serve, unix_serve

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


def start_websocket(unix: bool = True):
    import uvloop
    uvloop.install()

    ssl_context = None
    if config.crt_path and config.key_path:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(config.crt_path, config.key_path)

    async def serve_websocket():
        print("starting websocket server...")
        async with serve(WsServer().listen, host="localhost", port=config.ws_port, ssl=ssl_context):
            await asyncio.Future()  # run forever

    async def unix_serve_websocket():
        print("starting websocket server...")
        async with unix_serve(WsServer().listen, path=config.ws_unix_path, ssl=ssl_context):
            await asyncio.Future()  # run forever

    if unix:
        asyncio.run(unix_serve_websocket())
    else:
        asyncio.run(serve_websocket())


def start_http():
    HttpServer().run("0.0.0.0", config.http_port)


parser = ArgumentParser()
parser.add_argument("-t", "--target", choices=["http", "ws", "wsunix", "both", "local"], default="both")

args = parser.parse_args()

run_async(start_database())

if args.target == "ws":
    start_websocket(False)

elif args.target == "wsunix":
    start_websocket()

elif args.target == "http":
    start_http()

elif args.target == "local":
    websocket_server = Process(target=start_websocket, args=(False,))
    websocket_server.start()

    start_http()

else:
    websocket_server = Process(target=start_websocket)
    websocket_server.start()

    start_http()
