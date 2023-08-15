# -*- coding: utf-8 -*-
from typing import List

from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.common.board import Board, Cell
from hex_forest.models import Move, Player
from hex_forest.models.game import Game, Status
from hex_forest.views.base_view import BaseView


class BlindHexView:
    """
    A variant where only own moves are visible by default.

    To see the opponent moves a player has to pass a turn. Uncovered moves stay visible for the rest of the game.
    """

    @staticmethod
    async def show_board(request: Request, player: Player, game: Game) -> Response:
        size = 13
        board = Board(size)

        moves = await game.moves.all().order_by("index")

        visible_moves: List[Move] = []

        last_pass_index = -1
        for move in moves:
            if (
                (
                    (game.white.name == player.name and move.color)
                    or (game.black.name == player.name and not move.color)
                )
                and move.x == -1
                and move.y == -1
            ):
                last_pass_index = move.index

        for move in moves:
            if ((
                (game.white.name == player.name and move.color)
                or (game.black.name == player.name and not move.color)
            ) or move.index < last_pass_index) and move.x != -1 and move.y != -1:
                visible_moves.append(move)

        last_move = visible_moves[-1] if visible_moves else None

        template_context = {
            "size": size,
            "rows": board.rows,
            "owner": game.owner.name,
            "white_player": game.white.name if game.white else "join",
            "black_player": game.black.name if game.black else "join",
            "show_swap": len(moves) == 1,
            "show_start": game.owner == player and game.status is Status.PENDING,
            "game_status": game.status,
            "game_status_text": f"status: {Status(game.status).name.lower().replace('_', ' ')}",
            "stones": [
                Cell.render_stone(move.color, move.y, move.x) for move in visible_moves
            ],
            "marker": Cell.render_marker(last_move.color, last_move.y, last_move.x)
            if last_move
            else None,
            "allow_pass": True,
        }
        return await BaseView._view_base(
            request, BaseView._game_template, template_context
        )
