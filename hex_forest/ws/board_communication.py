# -*- coding: utf-8 -*-
import asyncio
import traceback
from typing import Awaitable, Callable, Dict, List

from tortoise.exceptions import IntegrityError
from tortoise.timezone import now
from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.common.board import Cell
from hex_forest.models import Game, Move, Player
from hex_forest.models.game import Status, Variant


class BoardCommunication:
    """
    WebSocket communication related to Board events.
    """

    _actions: Dict[str, Callable[[WebSocketServerProtocol, Dict, str], Awaitable[None]]]

    def __init__(self):
        """"""

        super().__init__()
        self._actions.update(
            **{
                "board_put": self._handle_put,
                "board_remove": self._handle_remove,
                "board_clear": self._handle_clear,
                "board_join": self._handle_join,
                "board_swap": self._handle_swap,
                "board_pass": self._handle_pass,
                "board_start": self._handle_start,
                "board_resign": self._handle_resign,
                "board_undo": self._handle_undo,
            }
        )

    async def _handle_put(self, player: Player, data: Dict) -> None:
        """"""

        mode = data["mode"]
        if mode == "analysis":
            await self._handle_analysis_put(player, data)
        else:
            await self._handle_game_put(player, data)

    async def _handle_analysis_put(self, player: Player, data: Dict) -> None:
        """"""

        color = data["color"]
        cell_id: str = data["cell_id"]
        x, y = Cell.id_to_xy(cell_id)

        await player.send(BoardCommunication.get_move_message_dict(player, color, x, y))

    async def _handle_game_put(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )
        if game.status != Status.IN_PROGRESS:
            message_dict = {
                "action": "alert",
                "message": "move received, but game has not started yet",
            }
            return await player.send(message_dict)

        color = await game.turn

        if game.variant is Variant.AI or ((color and player == game.white) or (not color and player == game.black)):
            cell_id: str = data["cell_id"]
            x, y = Cell.id_to_xy(cell_id)

            message_dict = BoardCommunication.get_move_message_dict(player, color, x, y)
            if game.variant is Variant.AI and (player == game.white) == color:
                message_dict["action"] = "moveAi"
                message_dict["notation"] = await game.notation

            send_to_game = (
                (player.send(message_dict),)
                if game.variant is Variant.AI
                else (game.send(
                    self.connected_clients_rev,
                    message_dict,
                ),)
                if game.variant is not Variant.BLIND
                else (player.send(message_dict), game.send(
                    self.connected_clients_rev,
                    BoardCommunication.get_pass_message_dict(player, color, []),
                ))
            )

            await asyncio.wait([*send_to_game, self.create_move(game, x, y)])
        else:
            # not your turn
            pass

    @staticmethod
    async def create_move(game: Game, x: int, y: int) -> None:
        """"""

        await Move.create(game=game, x=x, y=y, index=await game.move_count)

    @staticmethod
    def get_move_message_dict(player: Player, color: bool, x: int, y: int) -> Dict:
        """"""

        return {
            "action": "move",
            "move": {
                "color": color,
                "id": Cell.stone_id(x, y, color),
                "cx": Cell.stone_x(y, x),
                "cy": Cell.stone_y(y),
            },
            "message": f"Player {player.name} has clicked cell {chr(x + 97)}{y + 1}",
        }

    @staticmethod
    def get_pass_message_dict(player: Player, color: bool, moves: List[Move]) -> Dict:
        """"""

        return {
            "action": "passed",
            "color": color,
            "moves": [
                {
                    "color": not color,
                    "id": Cell.stone_id(move.x, move.y, color),
                    "cx": Cell.stone_x(move.y, move.x),
                    "cy": Cell.stone_y(move.y),
                } for move in moves if move.color is not color and move.x != -1 and move.y != -1
            ],
            "message": f"Player {player.name} has passed turn",
        }

    async def _handle_remove(self, player: Player, data: Dict) -> None:
        """"""

        mode = data["mode"]
        if mode != "analysis":
            # cannot remove stones during a game
            return

        stone_id = data["id"]
        message_dict = {
            "action": "remove",
            "id": stone_id,
            "message": f"Player {player.name} has removed stone {stone_id}",
        }

        await player.send(message_dict)

    async def _handle_clear(self, player: Player, data: Dict) -> None:
        """"""

        mode = data["mode"]
        if mode != "analysis":
            # cannot remove stones during a game
            return

        message_dict = {
            "action": "clear",
            "message": f"Player {player.name} has cleared the board",
        }

        await player.send(message_dict)

    async def _handle_join(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black"
        )
        if player.is_guest:
            await player.send(
                {"action": "alert", "message": "Cannot take side as guest."}
            )
            return
        if game.status != Status.PENDING:
            await player.send(
                {"action": "alert", "message": "Cannot change side, game in progress."}
            )
            return

        color = data["color"]
        if game.variant is Variant.AI:
            await self._take_ai_spot(game, player, color)
        else:
            await self._take_spot(game, player, color)

    async def _take_spot(self, game: Game, player: Player, color) -> None:
        """"""

        action = "takeSpot"
        if color:
            if not game.white:
                game.white = player
                if game.black and game.black == player:
                    game.black = None
            else:
                if game.white == player or game.owner == player:
                    game.white = None
                    action = "leaveSpot"
                else:
                    await player.send(
                        {"action": "alert", "message": "Side already taken."}
                    )
                    action = None
        else:
            if not game.black:
                game.black = player
                if game.white and game.white == player:
                    game.white = None
            else:
                if game.black == player or game.owner == player:
                    game.black = None
                    action = "leaveSpot"
                else:
                    await player.send(
                        {"action": "alert", "message": "Side already taken."}
                    )
                    action = None

        if action:
            message_dict = {
                "action": action,
                "color": color,
                "player_name": player.name,
            }

            tasks = [game.send(self.connected_clients_rev, message_dict), game.save()]

            try:
                await asyncio.wait(tasks)
            except IntegrityError:
                traceback.print_exc()

    async def _take_ai_spot(self, game, player, color):
        """"""

        if color:
            game.white = player
            game.black = None
        else:
            game.white = None
            game.black = player

        await asyncio.wait([player.send(
            {"action": "takeSpotAi", "color": color, "player_name": player.name}
        ), game.save()])

    async def _handle_swap(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )

        if game.white == player:
            white = game.white
            game.white = game.black
            game.black = white

            game.swapped = True

            message_dict = {"action": "swapped"}
            await asyncio.wait(
                [game.save(), game.send(self.connected_clients_rev, message_dict)]
            )
        else:
            # cannot swap as black
            pass

    async def _handle_pass(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )
        color = await game.turn

        if (color and player == game.white) or (not color and player == game.black):
            x: int = -1
            y: int = -1

            message_dict = BoardCommunication.get_pass_message_dict(player, color, game.moves)
            send_to_game = (
                (game.send(
                    self.connected_clients_rev,
                    BoardCommunication.get_pass_message_dict(player, color, game.moves),
                ),)
                if game.variant is not Variant.BLIND
                else (player.send(message_dict), game.send(
                    self.connected_clients_rev,
                    BoardCommunication.get_pass_message_dict(player, color, []),
                ))
            )

            await asyncio.wait([*send_to_game, self.create_move(game, x, y)])
        else:
            # not your turn
            pass

    async def _handle_start(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black"
        )

        if game.owner == player and game.white is not None and game.black is not None:
            game.started_at = now()
            game.status = Status.IN_PROGRESS

            await asyncio.wait(
                [game.save(), game.send(self.connected_clients_rev, {"action": "gameStarted"})]
            )
        elif game.owner == player and (game.white or game.black) and game.variant is Variant.AI:
            game.started_at = now()
            game.status = Status.IN_PROGRESS

            await asyncio.wait(
                [game.save(), player.send({"action": "gameStarted"})]
            )
        else:
            # only owner can start
            message_dict = {
                "action": "alert",
                "message": "cannot start yet",
            }
            await player.send(message_dict)

    async def _handle_resign(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )

        result = (
            Status.WHITE_WON
            if player == game.black
            else Status.BLACK_WON
            if player == game.white
            else None
        )
        if result:
            game.status = result
            game.finished_at = now()

            message_dict = {
                "action": "resigned",
                "color": True if result == Status.BLACK_WON else False,
            }
            await asyncio.wait(
                [
                    game.send(self.connected_clients_rev, message_dict),
                    game.save(),
                    game.invalidate_archive_record_cache(),
                ]
            )

    async def _handle_undo(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )
        turn = await game.turn

        if (turn and player == game.black) or (not turn and player == game.white):
            move = await Move.filter(game=game).order_by("-index").first()
            id_ = f"{move.x}-{move.y}-{move.color}"

            message_dict = {
                "action": "remove",
                "id": id_,
            }
            send_to_game = game.send(self.connected_clients_rev, message_dict)
            await asyncio.wait([send_to_game, move.delete()])
        else:
            # not your turn
            message_dict = {
                "action": "alert",
                "message": "can only undo your last move while your opponent turn",
            }
            await player.send(message_dict)
