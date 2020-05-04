import asyncio
import json
import os
import random
import string
import threading
import traceback
from json import JSONDecodeError
from time import time

import websockets
from japronto import Application
from jinja2 import Template

from models import Player, Board, Cell, DynamoDB, DecimalEncoder

players = {1: None, 2: None}
free_clients = {}
clients = {}
position = []
free_mode = False

lock = threading.Lock()
board = Board()
db = None
STORE_MINIMUM = 10
BLACK_COLOR = 1
WHITE_COLOR = 2

turn = BLACK_COLOR


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
            'mode': mode,
            'store_minimum': STORE_MINIMUM,
            'black_color': BLACK_COLOR,
            'white_color': WHITE_COLOR
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


async def send_to_board(message_dict, websocket=None):
    message = DecimalEncoder().encode(message_dict)
    if websocket and websocket not in clients:
        await websocket.send(message)
    elif clients:
        await asyncio.wait([client.send(message) for client in clients])


async def send_to_self(message_dict, websocket):
    message = DecimalEncoder().encode(message_dict)
    await websocket.send(message)


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
        tasks.append(send_to_board(message_dict, websocket))

    turn = 1
    for move in position:
        split = move.split('-')
        r = int(split[0])
        c = int(split[1])

        message_dict = {
            'type': 'move',
            'move': {'player_id': turn, 'id': move, 'cx': Cell.stone_x(r, c), 'cy': Cell.stone_y(r)},
        }
        tasks.append(send_to_self(message_dict, player.websocket))

        turn = WHITE_COLOR if turn == BLACK_COLOR else BLACK_COLOR

    await asyncio.wait(tasks)


async def send_assigned_players(player):
    message_dict = {
        'type': 'players',
        'players': [{'id': player_id, 'name': player.name} for player_id, player in players.items() if player is not None]
    }
    await send_to_board(message_dict, player)


async def unregister(websocket, free):
    if free:
        player = free_clients[websocket]
        del player
        del free_clients[websocket]
        return
    print('player disconnected')

    player_id = clients[websocket].id
    del clients[websocket]

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
    await send_to_board(message_dict)


async def delete_player(player_id):  # must be called from websocket thread
    players[player_id] = None

    # lock.acquire()
    # with open('players.json', 'w') as players_file:
    #     players_file.write(json.dumps(players, cls=DictEncoder))
    # lock.release()


async def handle_board_click(player, r, c, alternate, hints, free=False):
    try:
        if alternate:
            moving_player = player.turn
        else:
            if player.id != turn:
                return
            moving_player = player.id

        message_dict = {
            'type': 'move',
            'move': {'player_id': moving_player, 'id': f'{r}-{c}', 'cx': Cell.stone_x(r, c), 'cy': Cell.stone_y(r)},
            'message': f'Player {player.id} has clicked cell {chr(c + 97)}{r + 1}'
        }
        tasks = [
            make_move(player, moving_player, r, c, free),
            send_to_board(message_dict, player.websocket)
        ]
    except Exception as e:
        traceback.print_exc()

    await asyncio.wait(tasks)

    global position
    if not free and hints and len(position) >= 2:
        first_coords = position[0].split('-')
        first = f'{chr(int(first_coords[0]) + 97)}{int(first_coords[1]) + 1}'
        second_coords = position[1].split('-')
        second = f'{chr(int(second_coords[0]) + 97)}{int(second_coords[1]) + 1}'
        await handle_hints(player, f'{first},{second}', position)


async def make_move(player, moving_player_id, r, c, free=False):
    if board.rows[r][c].state == 0:
        board.rows[r][c].state = moving_player_id
    elif board.rows[r][c].state == moving_player_id:
        board.rows[r][c].state = 0

    if free:
        player.turn = WHITE_COLOR if player.turn == BLACK_COLOR else BLACK_COLOR
    else:
        global turn
        global position
        position.append(f'{r}-{c}')
        turn = WHITE_COLOR if len(position) % 2 == 1 else BLACK_COLOR

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
    await send_to_board(message_dict, player.websocket)


async def handle_remove(player, id):
    message_dict = {
        'type': 'remove',
        'id': id,
        'message': f'Player {player.id} has removed stone {id}'
    }
    await send_to_board(message_dict, player.websocket)


async def handle_undo(player):
    global turn
    turn = BLACK_COLOR if turn == WHITE_COLOR else WHITE_COLOR

    id = position.pop()
    message_dict = {
        'type': 'remove',
        'id': id,
        'message': f'Player {player.id} has clicked undo'
    }
    await send_to_board(message_dict, player.websocket)


async def handle_clear(player):
    global turn
    turn = BLACK_COLOR

    global position
    position = []

    message_dict = {
        'type': 'clear',
        'message': f'Player {player.id} has cleared the board'
    }
    await send_to_board(message_dict, player.websocket)


async def handle_swap(player, free=False):
    if free:
        player.turn = BLACK_COLOR if player.turn == WHITE_COLOR else WHITE_COLOR
        return
    elif len(position) != 1:
        return
    player_1 = players.get(1)
    player_2 = players.get(2)
    if not player_1 or not player_2:
        return
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
        send_to_board(message_dict, player.websocket),
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
            tasks.append(send_to_board(message_dict, player.websocket))
        except IndexError as e:
            print(f'Something wrong with game {game_id} position. Move: {move}')
            print(e)
            break
        except Exception as e:
            traceback.print_exc()
        turn = WHITE_COLOR if turn == BLACK_COLOR else BLACK_COLOR
        player.turn = turn
    await asyncio.wait(tasks)


async def handle_store_position(player, opening, position, result):
    if len(position) < STORE_MINIMUM:
        print('position not long enough!')
        return
    await db.store_position_async(opening, position, result)


async def handle_hints(player, opening, position):
    shown_percent = 0.1

    if len(position) < 2:
        return
    print('handling hints...')

    tasks = [
        db.get_position_result_async(opening, position),
        db.get_positions_for_async(opening)  # not passing any position on purpose
    ]
    finished_tasks = (await asyncio.wait(tasks))[0]

    # all_positions = await db.get_positions_for(opening, position)

    for task in finished_tasks:
        result = task.result()
        if isinstance(result, list):
            all_positions = result
        else:
            winner = result

    message_dict = {
        'type': 'result',
        'winner': winner  # TODO: change to relative to the player who's asking???
    }
    await send_to_self(message_dict, player.websocket)

    options = {}
    positions_n = 0
    moves_n = len(position)
    turn = WHITE_COLOR if moves_n % 2 == 1 else BLACK_COLOR

    t_1 = time()
    for pos in all_positions:
        all_moves = pos.get('all_moves').split(',')
        is_subset, diff_moves = rest_if_is_subset(position, moves_n, all_moves)
        # is_subset, diff_moves = rest_if_is_subset_fast(position, all_moves)
        if is_subset:
            positions_n += 1
            winner = pos.get('winner')
            for diff_move in diff_moves:
                move_split = diff_move.split('-')
                cell_id = f'{move_split[0]}-{move_split[1]}'
                color = int(move_split[2])
                if color == turn:
                    options[cell_id] = position_outcome(options.get(cell_id), int(winner))
    t_2 = time()
    print(f'search took {t_2 - t_1}')

    tasks = []
    for move, outcomes in options.items():
        results = outcomes.get('results')
        winner = outcomes.get('winner')
        if len(results) / positions_n < shown_percent:
            continue
        message_dict = {
            'type': 'hint',
            'move': move,
            'winner': winner
        }
        tasks.append(send_to_board(message_dict, player.websocket))

    if tasks:
        await asyncio.wait(tasks)


# def rest_if_is_subset_fast(moves, all_moves):
#     pass


# slow implementation (not using position order)
# TODO: # fast implementation (using position order)
def rest_if_is_subset(moves, moves_n, all_moves):
    rest = []
    rest_n = 0
    for move in all_moves:
        if move not in moves:
            rest.append(move)
            rest_n += 1
    is_subset = moves_n + rest_n == len(all_moves)
    return is_subset, rest


def position_outcome(outcomes, new_outcome):
    if outcomes is None:
        return {'results': [new_outcome], 'winner': new_outcome}
    outcomes['results'].append(new_outcome)
    results = outcomes['results']
    if len(results) >= 5:
        if len(set(results)) == 1:
            outcomes['winner'] = new_outcome
        else:
            outcomes['winner'] = 0
    else:
        outcomes['winner'] = None

    return outcomes


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
                        await handle_board_click(player, data.get('row'), data.get('column'), data.get('alternate'),
                                                 data.get('hints'), free)
                    elif action == 'chat':
                        if not free:
                            await handle_chat_message(player, data.get('message'))
                    elif action == 'remove':
                        if free:
                            await handle_remove(player, data.get('id'))
                    elif action == 'undo':
                        if not free:
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
                    elif action == 'store':
                        await handle_store_position(player, data.get('opening'), data.get('position'), data.get('result'))
                    elif action == 'hints':
                        await handle_hints(player, data.get('opening'), data.get('position'))
                except JSONDecodeError as e:
                    print(e, message)
    except Exception as e:
        traceback.print_exc()
    finally:
        try:
            await unregister(websocket, free)
        except Exception as e:
            traceback.print_exc()


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
