import asyncio
import os
import threading

import websockets
from japronto import Application

from decorators import ssl_decorator
from views.views import HttpCommunicator
from models import DynamoDB
from websocket.websocket_responses import WebsocketCommunicator


#>TODO: do something with this Japronto async cool stuff
# This is an asynchronous handler, it spends most of the time in the event loop.
# It wakes up every second 1 to print and finally returns after 3 seconds.
# This does let other handlers to be executed in the same processes while
# from the point of view of the client it took 3 seconds to complete.
@ssl_decorator
async def asynchronous(request):
    for i in range(1, 4):
        await asyncio.sleep(1)
        print(i, 'seconds elapsed')

    return request.Response(text='X seconds elapsed')


def run_websocket(db_connection):
    ws_communicator = WebsocketCommunicator(db_connection)
    target = os.environ.get('TARGET')
    if target == 'all':
        port = 8001
    else:
        port = int(os.environ.get('PORT'))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f'starting websocket server on port {port}...')
    loop.run_until_complete(
        websockets.serve(ws_communicator.receive, '0.0.0.0', port))
    asyncio.get_event_loop().run_forever()


def run_default(db_connection):
    run('0.0.0.0', db_connection)


def run(host, db_connection):
    app = Application()
    http_communicator = HttpCommunicator(db_connection)

    r = app.router
    r.add_route('/', http_communicator.show_board)
    r.add_route('/priviledges', http_communicator.show_board_with_priviledges)
    r.add_route('/free', http_communicator.show_free_board)
    r.add_route('/free11', http_communicator.show_board_11)
    r.add_route('/free19', http_communicator.show_board_19)
    r.add_route('/style.css', http_communicator.styles)
    r.add_route('/js.js', http_communicator.scripts)
    r.add_route('/favicon.ico', http_communicator.favicon)
    r.add_route('/wood-pattern.png', http_communicator.wood_pattern)

    r.add_route('/model-predict', http_communicator.get_predicted_action)
    r.add_route('/model-predict-cross', http_communicator.get_predicted_cross)

    # TODO: use that fancy Japronto stuff
    # r.add_route('/async', asynchronous)

    # return app
    port = int(os.environ.get('PORT', 8000))
    app.run(host, port)


if __name__ == "__main__":
    # db = DatabaseConnection()
    db = DynamoDB()
    try:
        target = os.environ.get('TARGET')
        if target == 'websocket':
            run_websocket(db)
        elif target == 'all':
            websocket_server = threading.Thread(target=run_websocket, daemon=True, args=(db,))
            websocket_server.start()
            run('0.0.0.0', db)
        else:
            run('0.0.0.0', db)
    finally:
        pass
        # db.close()
