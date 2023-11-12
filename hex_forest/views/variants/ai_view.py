# -*- coding: utf-8 -*-
from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.common.board import Board, Cell
from hex_forest.models import Game, Player
from hex_forest.models.game import Status
from hex_forest.views.base_view import BaseView


class AiView(BaseView):
    """
    A board view for a game against an AI opponent.
    """

    @staticmethod
    async def show_board(request: Request, player: Player, game: Game) -> Response:
        size = 13
        board = Board(size=size)

        moves = await game.moves.all().order_by("index")
        last_move = moves[-1] if moves else None
        moves_n = len(moves)
        turn_int = (
            0 if game.status is not Status.IN_PROGRESS else 1 if moves_n % 2 == 1 else 2
        )

        print("showing game with AI: ", game.status)

        template_context = {
            "size": size,
            "rows": board.rows,
            "mode": "ai",
            "owner": game.owner.name,
            "white_player": game.white.name if game.white else "join",
            "black_player": game.black.name if game.black else "join",
            "turn": turn_int,
            "show_swap": moves_n == 1,
            "show_start": game.owner == player and game.status is Status.PENDING,
            "game_status": game.status,
            "game_status_text": f"status: {Status(game.status).name.lower().replace('_', ' ')}",
            "stones": [Cell.render_stone(move.color, move.y, move.x) for move in moves],
            "notation": "".join([move.get_coord() for move in moves]),
            "marker": Cell.render_marker(last_move.color, last_move.y, last_move.x)
            if last_move
            else None,
        }
        return await BaseView._view_base(
            request, BaseView._game_template, template_context
        )
