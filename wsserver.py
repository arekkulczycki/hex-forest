import asyncio
import json
import os
import sys
import threading
from json import JSONDecodeError

import websockets
from japronto import Application
from jinja2 import Template

from models import Player, Board, Cell

players = {1: None, 2: None}
clients = {}

lock = threading.Lock()
board = Board()


def styles(request):
    with open('style.css') as html_file:
        return request.Response(text=html_file.read(), mime_type='text/css')


def favicon(request):
    with open('hex.png', 'rb') as favicon:
        return request.Response(body=favicon.read(), mime_type='image/png')


def get_board_status(request):
    with open('index.html') as html_file:
        template = Template(html_file.read())
        fields = []

        # lock.acquire()
        # with open('players.json', 'r') as players_file:
        #     players = json.loads(players_file.read())
        # lock.release()

        template_context = {
            'rows': board.rows,
            'port': 8001
        }
        return request.Response(text=template.render(**template_context), mime_type='text/html')


# This is an asynchronous handler, it spends most of the time in the event loop.
# It wakes up every second 1 to print and finally returns after 3 seconds.
# This does let other handlers to be executed in the same processes while
# from the point of view of the client it took 3 seconds to complete.
async def asynchronous(request):
    for i in range(1, 4):
        await asyncio.sleep(1)
        print(i, 'seconds elapsed')

    return request.Response(text='X seconds elapsed')


def assign_a_player(websocket):
    for i in range(1, 3):
        player = players.get(i)
        if not player:
            player = Player(i, websocket, 'test name')
            players[i] = player
            return player
        elif not player.present:
            player.present = True
            player.websocket = websocket
            players[i] = player
            return player
    return Player(0, websocket, 'test name', 0)


async def send_to_all(message_dict):
    message = json.dumps(message_dict)
    if clients:
        await asyncio.wait([client.send(message) for client in clients])


async def register(websocket):
    print('player connecting...')
    player = assign_a_player(websocket)
    clients[websocket] = player

    if player.id:
        # lock.acquire()
        # with open('players.json', 'w') as players_file:
        #     players_file.write(json.dumps(players, cls=DictEncoder))
        # lock.release()

        host = websocket.request_headers.get('host')
        user_agent = websocket.request_headers.get('User-Agent')
        message_dict = {
            'type': 'info',
            'message': 'Player {} has joined!'.format(player.id),
        }
        await send_to_all(message_dict)


async def unregister(websocket):
    print('player disconnected')
    player_id = clients[websocket].id
    players[player_id].websocket = None
    players[player_id].present = False
    del clients[websocket]

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()

    host = websocket.request_headers.get('host')
    user_agent = websocket.request_headers.get('User-Agent')
    message_dict = {
        'type': 'info',
        'message': 'Player {} has leaved!'.format(player_id),
    }
    await send_to_all(message_dict)


async def delete_player(player_id):  # must be called from websocket thread
    players[player_id] = None

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()


async def handle_board_click(player, r, c):
    message_dict = {
        'type': 'move',
        'move': {'player_id': player.id, 'id': f'{r}-{c}', 'cx': Cell.stone_x(r, c), 'cy': Cell.stone_y(r)},
        'message': f'Player {player.id} has clicked cell {chr(c + 97)}{r + 1}'
    }
    tasks = [
        save_move(player.id, r, c),
        send_to_all(message_dict)
    ]
    await asyncio.wait(tasks)


async def handle_chat_message(player, message):
    message_dict = {
        'type': 'chat',
        'played_id': player.id,
        'message': message
    }
    await send_to_all(message_dict)


async def save_move(player_id, r, c):
    if board.rows[r][c].state == 0:
        board.rows[r][c].state = player_id
    elif board.rows[r][c].state == player_id:
        board.rows[r][c].state = 0

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()


async def receive(websocket, path):
    await register(websocket)
    try:
        async for message in websocket:
            player = clients.get(websocket)
            if player:
                try:
                    data = json.loads(message)
                    action = data.get('action')
                    if action == 'board_click':
                        await handle_board_click(player, data.get('row'), data.get('column'))
                    elif action == 'chat':
                        await handle_chat_message(player, data.get('message'))
                except JSONDecodeError as e:
                    print(e, message)
    except:
        pass
    finally:
        await unregister(websocket)


def run_websocket():
    port = int(os.environ.get('PORT'))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f'starting websocket server on port {port}...')
    loop.run_until_complete(
        websockets.serve(receive, '0.0.0.0', port))
    asyncio.get_event_loop().run_forever()


def run_default():
    run('0.0.0.0')


def run(host):
    app = Application()

    r = app.router
    r.add_route('/', get_board_status)
    r.add_route('/style.css', styles)
    r.add_route('/async', asynchronous)
    r.add_route('/favicon.ico', favicon)

    # return app
    port = int(os.environ.get('PORT'))
    app.run(host, port)


if __name__ == "__main__":
    target = os.environ.get('TARGET')
    if target == 'websocket':
        run_websocket()
    elif target == 'all':
        websocket_server = threading.Thread(target=run_websocket, daemon=True)
        websocket_server.start()
        run('0.0.0.0')
    else:
        run('0.0.0.0')
