# -*- coding: utf-8 -*-
import asyncio
import traceback
from typing import Awaitable, Callable, Dict

from tortoise.exceptions import IntegrityError
from tortoise.timezone import now
from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.common.board import Cell
from hex_forest.models import Player, Game, Move
from hex_forest.models.game import Status


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
        x: int = data["x"]
        y: int = data["y"]

        await player.send(BoardCommunication.get_move_message_dict(player, color, x, y))

    async def _handle_game_put(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black", "moves"
        )
        turn = await game.turn

        if (turn and player == game.white) or (not turn and player == game.black):
            row: int = data["row"]
            column: int = data["column"]

            send_to_game = game.send(
                self.connected_clients_rev,
                BoardCommunication.get_move_message_dict(player, turn, row, column),
            )
            move_count = await game.move_count
            await asyncio.wait(
                [
                    send_to_game,
                    Move.create(game=game, x=row, y=column, index=move_count),
                ]
            )
        else:
            # not your turn
            pass

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

        action = "takeSpot"
        color = data["color"]
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
                    return
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
                    return

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

    async def _handle_start(self, player: Player, data: Dict) -> None:
        """"""

        game = await Game.get(id=data["game_id"]).prefetch_related(
            "owner", "white", "black"
        )

        if game.owner == player and game.white is not None and game.black is not None:
            game.started_at = now()
            game.status = Status.IN_PROGRESS

            message_dict = {"action": "gameStarted"}
            await asyncio.wait(
                [game.save(), game.send(self.connected_clients_rev, message_dict)]
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
