import asyncio
import json
import os
import random
import string
import threading
from json import JSONDecodeError

import websockets
from japronto import Application
from jinja2 import Template

from models import Player, Board, Cell, DynamoDB, DecimalEncoder

players = {1: None, 2: None}
free_clients = {}
clients = {}
position = []
turn = 1
free_mode = False

lock = threading.Lock()
board = Board()
db = None


def styles(request):
    with open('style.css') as html_file:
        return request.Response(text=html_file.read(), mime_type='text/css')


def favicon(request):
    with open('hex.png', 'rb') as favicon:
        return request.Response(body=favicon.read(), mime_type='image/png')


def show_board(request, mode=''):
    with open('index.html') as html_file:
        template = Template(html_file.read())
        fields = []

        # lock.acquire()
        # with open('players.json', 'r') as players_file:
        #     players = json.loads(players_file.read())
        # lock.release()
        websocket_route = mode

        target = os.environ.get('TARGET')
        if target == 'all':
            websocket_address = f'ws://localhost:8001/{websocket_route}'
        else:
            websocket_address = f'wss://hex-forest-ws.herokuapp.com/{websocket_route}'

        template_context = {
            'rows': board.rows,
            'websocket_address': websocket_address,
            'mode': mode
        }
        return request.Response(text=template.render(**template_context), mime_type='text/html')


def show_free_board(request):
    return show_board(request, 'free')


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
            player = Player(i, websocket, f'player name {i}')
            players[i] = player
            return player
        elif not player.present:
            player.present = True
            player.websocket = websocket
            players[i] = player
            return player
    return Player(0, websocket, 'spectator', 0)


async def send_to_all(message_dict, websocket):
    message = json.dumps(message_dict)
    if not clients.get(websocket):
        await websocket.send(message)
    elif clients:
        await asyncio.wait([client.send(message) for client in clients])


async def register(websocket, free):
    print('player connecting...')
    if free:
        free_clients[websocket] = Player(3, websocket, 'free')
        return
    player = assign_a_player(websocket)
    clients[websocket] = player

    tasks = [send_assigned_players(websocket)]
    if player.id:
        # lock.acquire()
        # with open('players.json', 'w') as players_file:
        #     players_file.write(json.dumps(players, cls=DictEncoder))
        # lock.release()

        host = websocket.request_headers.get('host')
        user_agent = websocket.request_headers.get('User-Agent')
        message_dict = {
            'type': 'playerIn',
            'player_id': player.id,
            'player_name': player.name,
            'message': 'Player {} has joined!'.format(player.id),
        }
        tasks.append(send_to_all(message_dict, websocket))

    await asyncio.wait(tasks)


async def send_assigned_players(player):
    message_dict = {
        'type': 'players',
        'players': [{'id': player_id, 'name': player.name} for player_id, player in players.items() if player is not None]
    }
    await send_to_all(message_dict, player)


async def unregister(websocket, free):
    if free:
        player = free_clients[websocket]
        del player
        del free_clients[websocket]
        return
    print('player disconnected')
    player_id = clients[websocket].id
    players[player_id].websocket = None
    players[player_id].present = False

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()

    host = websocket.request_headers.get('host')
    user_agent = websocket.request_headers.get('User-Agent')
    message_dict = {
        'type': 'playerOut',
        'player_id': player_id,
        'message': 'Player {} has leaved!'.format(player_id),
    }
    await send_to_all(message_dict, websocket)
    del clients[websocket]


async def delete_player(player_id):  # must be called from websocket thread
    players[player_id] = None

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()


async def handle_board_click(player, r, c, alternate, free=False):
    if alternate:
        moving_player = player.turn
    else:
        moving_player = player.id

    message_dict = {
        'type': 'move',
        'move': {'player_id': moving_player, 'id': f'{r}-{c}', 'cx': Cell.stone_x(r, c), 'cy': Cell.stone_y(r)},
        'message': f'Player {player.id} has clicked cell {chr(c + 97)}{r + 1}'
    }
    tasks = [
        make_move(player, moving_player, r, c, free),
        send_to_all(message_dict, player.websocket)
    ]
    await asyncio.wait(tasks)


async def make_move(player, moving_player_id, r, c, free=False):
    if board.rows[r][c].state == 0:
        board.rows[r][c].state = moving_player_id
    elif board.rows[r][c].state == moving_player_id:
        board.rows[r][c].state = 0

    if free:
        player.turn = 1 if player.turn == 2 else 2
    else:
        global turn
        global position
        position.append(f'{r}-{c}')
        turn = 2 if len(position) % 2 == 1 else 1

    # positions = db.get_positions_for('a1,b2')
    # print(positions)
    #
    # client = clients[players[player_id].websocket]
    # message_dict = {
    #     'type': 'info',
    #     'message': positions
    # }
    # await asyncio.wait([client.send(DecimalEncoder().encode(message_dict))])

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()


async def handle_chat_message(player, message):
    message_dict = {
        'type': 'chat',
        'player_id': player.id,
        'message': message
    }
    await send_to_all(message_dict, player.websocket)


async def handle_remove(player, id):
    message_dict = {
        'type': 'remove',
        'id': id,
        'message': f'Player {player.id} has removed stone {id}'
    }
    await send_to_all(message_dict, player.websocket)


async def handle_undo(player):
    id = position.pop()
    message_dict = {
        'type': 'remove',
        'id': id,
        'message': f'Player {player.id} has clicked undo'
    }
    await send_to_all(message_dict, player.websocket)


async def handle_clear(player):
    global position
    position = []

    message_dict = {
        'type': 'clear',
        'message': f'Player {player.id} has cleared the board'
    }
    await send_to_all(message_dict, player.websocket)


async def handle_swap(player, free=False):
    if free:
        player.turn = 1 if player.turn == 2 else 2
        return
    player_1 = players.get(1)
    player_2 = players.get(2)
    player_1.id = 2
    player_2.id = 1
    players[1] = player_2
    players[2] = player_1
    await send_assigned_players(player)


async def handle_save_game(player, game_id):
    global position
    if not game_id:
        game_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

    message_dict = {
        'type': 'saved',
        'game_id': game_id,
        'message': f'Player {player.id} has saved the game'
    }
    tasks = [
        send_to_all(message_dict, player.websocket),
        db.save_game_async(game_id, position)
    ]
    await asyncio.wait(tasks)


async def handle_load_game(player, game_id):
    if not game_id:
        print('game id not provided')
        return
    game = db.load_game(game_id)

    if not game:
        print('game doesn\'t exist in database')
        return

    global position
    position = game.get('position')

    global turn
    tasks = []
    for move in position:
        split = move.split('-')
        try:
            r = int(split[0])
            c = int(split[1])
            message_dict = {
                'type': 'move',
                'move': {'player_id': turn, 'id': move, 'cx': Cell.stone_x(r, c), 'cy': Cell.stone_y(r)},
            }
            tasks.append(send_to_all(message_dict, player.websocket))
        except IndexError as e:
            print(f'Something wrong with game {game_id} position. Move: {move}')
            print(e)
            break
        except Exception as e:
            print(e)
        turn = 2 if turn == 1 else 1
        player.turn = turn
    await asyncio.wait(tasks)


async def receive(websocket, path):
    free = path == '/free'
    await register(websocket, free)
    try:
        async for message in websocket:
            if free:
                player = free_clients.get(websocket)
            else:
                player = clients.get(websocket)
            if player and player.id != 0:
                try:
                    data = json.loads(message)
                    action = data.get('action')
                    if action == 'board_click':
                        await handle_board_click(player, data.get('row'), data.get('column'), data.get('alternate'), free)
                    elif action == 'chat':
                        if not free:
                            await handle_chat_message(player, data.get('message'))
                    elif action == 'remove':
                        if free:
                            await handle_remove(player, data.get('id'))
                    elif action == 'undo':
                        await handle_undo(player)
                    elif action == 'swap':
                        await handle_swap(player, free)
                    elif action == 'clear':
                        await handle_clear(player)
                    elif action == 'save':
                        if not free:
                            await handle_save_game(player, data.get('game_id'))
                    elif action == 'load':
                        await handle_load_game(player, data.get('game_id'))
                except JSONDecodeError as e:
                    print(e, message)
    except:
        pass
    finally:
        await unregister(websocket, free)


def run_websocket():
    target = os.environ.get('TARGET')
    if target == 'all':
        port = 8001
    else:
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
    r.add_route('/', show_board)
    r.add_route('/free', show_free_board)
    r.add_route('/style.css', styles)
    r.add_route('/async', asynchronous)
    r.add_route('/favicon.ico', favicon)

    # return app
    port = int(os.environ.get('PORT'))
    app.run(host, port)


if __name__ == "__main__":
    # db = DatabaseConnection()
    db = DynamoDB()
    try:
        target = os.environ.get('TARGET')
        if target == 'websocket':
            run_websocket()
        elif target == 'all':
            websocket_server = threading.Thread(target=run_websocket, daemon=True)
            websocket_server.start()
            run('0.0.0.0')
        else:
            run('0.0.0.0')
    finally:
        pass
        # db.close()
