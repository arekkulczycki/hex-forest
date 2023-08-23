import asyncio
import json
import random
import string
import threading
import traceback
from decimal import Decimal
from json import JSONDecodeError
from typing import Optional, Dict

import requests
from websockets.server import WebSocketServerProtocol

from hex_forest.common.board import Cell
from hex_forest.constants import STORE_MINIMUM, WHITE_COLOR, BLACK_COLOR
from hex_forest.models.player import OnlinePlayer as Player

players = {1: None, 2: None}
free_clients = {}
clients = {}
position = []

free_mode = False

lock = threading.Lock()

turn = BLACK_COLOR


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        if isinstance(o, set):
            return list(o)
        return super().default(o)


class WebsocketCommunicator:
    def __init__(self):
        self.db = None

    async def legacy_receive(self, websocket: WebSocketServerProtocol, data: Dict, path: str):
        is_analysis = "/analysis" in path
        if is_analysis:
            player = free_clients.get(websocket)
        else:
            player = clients.get(websocket)
        if player and player.name != 0:
            action = data.get("action")
            if action == "board_click":
                if player.id in [1, 2] or is_analysis:
                    await self.handle_board_click(
                        player,
                        data.get("row"),
                        data.get("column"),
                        data.get("color"),
                        data.get("hints"),
                        is_analysis,
                    )
            elif action == "chat":
                if player.id in [1, 2] and not is_analysis:
                    await self.handle_chat_message(
                        player, data.get("message")
                    )
            elif action == "remove":
                if is_analysis:
                    await self.handle_remove(player, data.get("id"))
            elif action == "undo":
                if is_analysis or player.id in [1, 2]:
                    await self.handle_undo(player, is_analysis)
            elif action == "swap":
                if player.id in [1, 2]:
                    await self.handle_swap(player, is_analysis)
            elif action == "clear":
                if is_analysis or player.id in [1, 2]:
                    await self.handle_clear(player, is_analysis)
            elif action == "save":
                if is_analysis or player.id in [1, 2]:
                    await self.handle_save_game(
                        player, data.get("game_id"), is_analysis
                    )
            elif action == "load":
                if is_analysis or player.id in [1, 2]:
                    await self.handle_load_game(
                        player, data.get("game_id"), is_analysis
                    )
                else:
                    print("Player disallowed to load the game!")
            elif action == "import":
                if is_analysis or player.id in [1, 2]:
                    await self.handle_import_game(
                        player, data.get("game_id"), is_analysis
                    )
            elif action == "store":
                if player.id in [1, 2]:
                    await self.handle_store_position(
                        player,
                        data.get("opening"),
                        data.get("position"),
                        data.get("result"),
                    )
            # elif action == 'hints':
            #     await self.handle_hints(player, data.get('opening'), data.get('position'))
            elif action == "name":
                await self.handle_set_name(player, data.get("name"))
            elif action == "kick":
                await self.handle_kick_player(player, data.get("player_id"))
            elif action == "join_board":
                if not is_analysis:
                    await self.handle_join_board(player, data.get("spot"))

    def legacy_assign_player(self, websocket: WebSocketServerProtocol):

        name = f"spectator"
        player = Player(websocket, name)

        clients[websocket] = player

        return player

    async def send_to_board(self, message_dict, websocket=None):
        message = DecimalEncoder().encode(message_dict)
        if websocket and websocket not in clients:
            await websocket.send(message)
        elif clients:
            await asyncio.wait([client.send(message) for client in clients])

    async def send_to_one(self, message_dict, websocket):
        if websocket:
            message = DecimalEncoder().encode(message_dict)
            await websocket.send(message)

    async def register(self, websocket: WebSocketServerProtocol):
        print("player connecting...")
        player = self.legacy_assign_player(websocket)

        tasks = [
            self.send_assigned_players(player),
        ]

        host = websocket.request_headers.get("host")
        user_agent = websocket.request_headers.get("User-Agent")
        message_dict = {
            "type": "playerIn",
            "player_name": player.name,
            "message": "Player {} has joined!".format(player.name),
        }
        tasks.append(self.send_to_board(message_dict, websocket))

        for move in position:
            split = move.split("-")
            r = int(split[0])
            c = int(split[1])
            color = int(split[2])

            message_dict = {
                "type": "move",
                "move": {
                    "player_id": color,
                    "id": move,
                    "cx": Cell.stone_x(r, c),
                    "cy": Cell.stone_y(r),
                },
            }
            tasks.append(self.send_to_one(message_dict, player.websocket))

        await asyncio.wait(tasks[:-1])
        await tasks[-1]

    async def handle_set_name(self, player, name):
        player.name = name if name else "player"

        message_dict = {"type": "playerName", "player_name": player.name}
        await self.send_to_board(message_dict, player.websocket)

    async def handle_kick_player(self, _player, kicked_player_id):
        players[kicked_player_id] = None
        kicked_player = None

        for websocket, player in clients.items():
            if player.id == kicked_player_id:
                _id = random.randint(3, 1000000)
                player.id = _id
                kicked_player = player

        if kicked_player:
            tasks = []

            message_dict = {"type": "leaveSpot", "spot": kicked_player_id}
            tasks.append(self.send_to_board(message_dict, _player.websocket))

            message_dict = {
                "type": "kicked",
                "message": "Site administrator has dropped you from the board.",
            }
            tasks.append(self.send_to_one(message_dict, kicked_player.websocket))

            await asyncio.wait(tasks)

    async def handle_join_board(self, player, spot):
        try:
            spot = int(spot)
        except ValueError:
            await self.send_alert("Sorry, something went wrong...", player.websocket)

        if players.get(spot) is None:
            players[spot] = player

            old_id = player.id
            player.id = spot
            if old_id in [1, 2]:
                players[old_id] = None
                message_dict = {
                    "type": "leaveSpot",
                    "player_old_id": old_id,
                    "player_id": spot,
                    "player_name": player.name,
                }
                await self.send_to_board(message_dict, player.websocket)
            message_dict = {
                "type": "takeSpot",
                "player_old_id": old_id,
                "player_id": spot,
                "player_name": player.name,
            }
            await self.send_to_board(message_dict, player.websocket)
        else:
            await self.send_alert("Sorry, spot is taken!", player)

    async def send_assigned_players(self, _player):
        message_dict = {
            "type": "players",
            "players": [
                {"name": "__name__" if player == _player else player.name}
                for websocket, player in clients.items()
                if player is not None
            ],
        }
        await self.send_to_one(message_dict, _player.websocket)

    async def unregister(self, websocket: WebSocketServerProtocol):
        print("player disconnected")

        player_name = clients[websocket].name
        player = clients[websocket]
        del player
        del clients[websocket]

        if player_name in [1, 2]:
            players[player_name] = None

        # lock.acquire()
        # with open('players.json', 'w') as players_file:
        #     players_file.write(json.dumps(players, cls=DictEncoder))
        # lock.release()

        host = websocket.request_headers.get("host")
        user_agent = websocket.request_headers.get("User-Agent")
        message_dict = {
            "type": "playerOut",
            "player_name": player_name,
            "message": "Player {} has leaved!".format(player_name),
        }
        await self.send_to_board(message_dict)

    async def delete_player(self, player_id):  # must be called from websocket thread
        players[player_id] = None

        # lock.acquire()
        # with open('players.json', 'w') as players_file:
        #     players_file.write(json.dumps(players, cls=DictEncoder))
        # lock.release()

    async def handle_board_click(self, player, r, c, color, hints, is_analysis=False):
        try:
            if is_analysis:
                if color == "natural":
                    moving_player = (
                        BLACK_COLOR
                        if (len(player.position) % 2 == 0 and not player.swap)
                        or (len(player.position) % 2 == 1 and player.swap)
                        else WHITE_COLOR
                    )
                elif color == "black":
                    moving_player = BLACK_COLOR
                elif color == "white":
                    moving_player = WHITE_COLOR
            else:
                if player.id != turn:
                    return
                moving_player = player.id

            message_dict = {
                "type": "move",
                "move": {
                    "player_id": moving_player,
                    "id": f"{r}-{c}-{moving_player}",
                    "cx": Cell.stone_x(r, c),
                    "cy": Cell.stone_y(r),
                },
                "message": f"Player {player.id} has clicked cell {chr(c + 97)}{r + 1}",
            }
            tasks = [
                self.make_move(player, moving_player, r, c, is_analysis),
                self.send_to_board(message_dict, player.websocket),
            ]
        except Exception as e:
            traceback.print_exc()

        await asyncio.wait(tasks)

        # global position
        # if not is_analysis and hints and len(position) >= 2:
        #     first_coords = position[0].split('-')
        #     opening = f'{chr(int(first_coords[1]) + 97)}{int(first_coords[0]) + 1}'
        #     await self.handle_hints(player, opening, position)

    async def make_move(self, player, moving_player_id, r, c, is_analysis=False):
        # if board.rows[r][c].state == 0:
        #     board.rows[r][c].state = moving_player_id
        # elif board.rows[r][c].state == moving_player_id:
        #     board.rows[r][c].state = 0

        if is_analysis:
            player.turn = WHITE_COLOR if player.turn == BLACK_COLOR else BLACK_COLOR
            player.position.append(f"{r}-{c}-{moving_player_id}")
        else:
            global position
            position.append(f"{r}-{c}-{moving_player_id}")

        global turn
        turn = WHITE_COLOR if moving_player_id == BLACK_COLOR else BLACK_COLOR

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

    async def handle_chat_message(self, player, message):
        message_dict = {"type": "chat", "player_id": player.id, "message": message}
        await self.send_to_board(message_dict, player.websocket)

    async def handle_remove(self, player, id):
        player.position.remove(id)

        message_dict = {
            "type": "remove",
            "id": id,
            "message": f"Player {player.id} has removed stone {id}",
        }
        await self.send_to_board(message_dict, player.websocket)

    async def handle_undo(self, player, is_analysis):
        # TODO: get rid of stupid turn
        global turn
        turn = BLACK_COLOR if turn == WHITE_COLOR else WHITE_COLOR

        if is_analysis:
            board_position = player.position
        else:
            global position
            board_position = position

        if board_position:
            id = board_position.pop()
            remove_message_dict = {
                "type": "remove",
                "id": id,
                "message": f"Player {player.id} has clicked undo",
            }
            tasks = [self.send_to_board(remove_message_dict, player.websocket)]

            if board_position:
                move = board_position[-1]
                split = move.split("-")
                r = int(split[0])
                c = int(split[1])
                marker_message_dict = {
                    "type": "mark",
                    "move": {
                        "id": move,
                        "cx": Cell.stone_x(r, c),
                        "cy": Cell.stone_y(r),
                    },
                }
                tasks.append(self.send_to_board(marker_message_dict, player.websocket))

            await asyncio.wait(tasks)

    async def handle_clear(self, player, is_analysis=False):
        global turn
        turn = BLACK_COLOR

        global position
        position = []

        message_dict = {
            "type": "clear",
            "message": f"Player {player.id} has cleared the board",
        }
        if is_analysis:
            await self.send_to_one(message_dict, player.websocket)
        else:
            await self.send_to_board(message_dict, player.websocket)

    async def handle_swap(self, player, is_analysis=False):
        if is_analysis:
            player.turn = BLACK_COLOR if player.turn == WHITE_COLOR else WHITE_COLOR
            return
        elif len(position) != 1:
            return
        black = players.get(1)
        white = players.get(2)
        if not black or not white:
            return

        black.id = 2
        white.id = 1
        players[1] = white
        players[2] = black

        message_dict = {
            "type": "players",
            "players": [
                {"id": player_id, "name": player.name}
                for player_id, player in players.items()
                if player is not None
            ],
        }
        await self.send_to_board(message_dict, player.websocket)

    async def handle_save_game(self, player, game_id, is_analysis=False):
        global position
        if not game_id:
            game_id = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=16)
            )

        message_dict = {
            "type": "saved",
            "game_id": game_id,
            "message": f"Player {player.id} has saved the game",
        }

        position_to_save = player.position if is_analysis else position
        tasks = [
            self.send_to_board(message_dict, player.websocket),
            self.db.save_game_async(game_id, position_to_save, players),
        ]
        await asyncio.wait(tasks)

    async def send_alert(self, message, player):
        message_dict = {
            "type": "alert",
            "message": message,
        }
        await self.send_to_one(message_dict, player.websocket)

    async def handle_load_game(self, player, game_id, is_analysis):
        print("signal reached target")
        if not game_id:
            print("game id not provided")
            return
        game = self.db.load_game(game_id)

        if not game:
            message = f"Game with ID: {game_id} doesn't exist in database!"
            print(message)
            await self.send_alert(message, player)
            return
        else:
            await self.handle_clear(player)

        game_position = game.get("position")
        if is_analysis:
            player.position = game_position
        else:
            global position
            position = game_position

        global turn
        tasks = []

        for move in game_position:
            split = move.split("-")
            try:
                r = int(split[0])
                c = int(split[1])
                message_dict = {
                    "type": "move",
                    "move": {
                        "player_id": turn,
                        "id": move,
                        "cx": Cell.stone_x(r, c),
                        "cy": Cell.stone_y(r),
                    },
                }
                tasks.append(self.send_to_board(message_dict, player.websocket))
            except IndexError as e:
                print(f"Something wrong with game {game_id} position. Move: {move}")
                print(e)
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
            turn = WHITE_COLOR if turn == BLACK_COLOR else BLACK_COLOR
            player.turn = turn

        if tasks:
            await asyncio.wait(tasks)

    async def handle_store_position(self, player, opening, position, result):
        if len(position) < STORE_MINIMUM:
            print("position not long enough!")
            return
        await self.db.store_position_async(opening, position, result)

    # async def handle_hints(self, player, opening, position):
    #     shown_percent = 0.1
    #
    #     if len(position) < 2:
    #         return
    #     print('handling hints...')
    #
    #     tasks = [
    #         self.db.get_position_result_async(opening, position),
    #         self.db.get_positions_for_async(opening, position)
    #     ]
    #     finished_tasks = (await asyncio.wait(tasks))[0]
    #
    #     # all_positions = await db.get_positions_for(opening, position)
    #
    #     for task in finished_tasks:
    #         result = task.result()
    #         if isinstance(result, list):
    #             all_positions = result
    #         else:
    #             winner = result
    #
    #     message_dict = {
    #         'type': 'result',
    #         'winner': winner  # TODO: change to relative to the player who's asking???
    #     }
    #     await self.send_to_one(message_dict, player.websocket)
    #
    #     options = {}
    #     positions_n = 0
    #
    #     position = sorted(position, key=self.db.position_sorting_key)
    #     moves_n = len(position)
    #     turn = WHITE_COLOR if moves_n % 2 == 1 else BLACK_COLOR
    #
    #     t_1 = time()
    #     for pos in all_positions:
    #         all_moves = pos.get('all_moves')
    #         print(all_moves, position)
    #         # is_subset, diff_moves = rest_if_is_subset(position, moves_n, all_moves)
    #         is_subset, diff_moves = utils.rest_if_is_subset_faster(position, all_moves)
    #         if is_subset:
    #             positions_n += 1
    #             winner = pos.get('winner')
    #             for diff_move in diff_moves:
    #                 move_split = diff_move.split('-')
    #                 cell_id = f'{move_split[0]}-{move_split[1]}'
    #                 color = int(move_split[2])
    #                 if color == turn:
    #                     options[cell_id] = utils.position_outcome(options.get(cell_id), int(winner))
    #     t_2 = time()
    #     print(f'search took {t_2 - t_1}')
    #     print(options)
    #
    #     tasks = []
    #     for move, outcomes in options.items():
    #         results = outcomes.get('results')
    #         winner = outcomes.get('winner')
    #         if len(results) / positions_n < shown_percent:
    #             continue
    #         message_dict = {
    #             'type': 'hint',
    #             'move': move,
    #             'winner': winner
    #         }
    #         tasks.append(self.send_to_board(message_dict, player.websocket))
    #
    #     if tasks:
    #         await asyncio.wait(tasks)

    async def handle_import_game(self, player, game_number, is_analysis):
        global position
        position = []

        message_dict = {"type": "clear", "message": f""}
        if is_analysis:
            await self.send_to_one(message_dict, player.websocket)
        else:
            await self.send_to_board(message_dict, player.websocket)
        await self.import_lg_game(player, game_number, is_analysis)

    async def import_lg_game(self, player, game_number, is_analysis):
        response = requests.get(
            f"https://littlegolem.net/servlet/sgf/{game_number}/game{game_number}.hsgf"
        )
        moves = response.text.split(";")[2:]

        is_over = moves[-1][2:8] == "resign"
        if is_over:
            moves.pop(-1)

        has_swap = moves[1][2:6] == "swap"
        if has_swap:
            moves.pop(1)

        k = 0
        for move in moves:
            k += 1
            moving_player = WHITE_COLOR if move[0] == "B" else BLACK_COLOR
            if k == 1 and has_swap:
                moving_player = (
                    WHITE_COLOR if moving_player == BLACK_COLOR else BLACK_COLOR
                )
                r = ord(move[2]) - 97
                c = ord(move[3]) - 97
            else:
                c = ord(move[2]) - 97
                r = ord(move[3]) - 97
            message_dict = {
                "type": "move",
                "move": {
                    "player_id": moving_player,
                    "id": f"{r}-{c}-{moving_player}",
                    "cx": Cell.stone_x(r, c),
                    "cy": Cell.stone_y(r),
                },
                "message": f"",
            }
            tasks = [self.make_move(player, moving_player, r, c, is_analysis)]
            if is_analysis:
                tasks.append(self.send_to_one(message_dict, player.websocket))
            else:
                tasks.append(self.send_to_board(message_dict, player.websocket))
            await asyncio.wait(tasks)
