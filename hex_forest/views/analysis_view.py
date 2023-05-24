# -*- coding: utf-8 -*-
from typing import List

from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.common.board import Board, Cell
from hex_forest.models import Game
from hex_forest.models.move import FakeMove, Move
from hex_forest.views.archive_view import ArchiveView
from hex_forest.views.base_view import BaseView


class AnalysisView(BaseView):
    """
    Analysis board view (self-play).
    """

    def __init__(self):
        super().__init__()
        self._routes += [
            ("/analysis", self.analysis_board),
            ("/analysis/game/{game_id}", self.analysis_board_from_game),
            ("/analysis/{moves}", self.analysis_board_from_moves),
        ]

    # @route("/game")
    @staticmethod
    async def analysis_board(request: Request) -> Response:
        size = request.headers.get("board-size", 13)
        board = Board(size)

        template_context = {
            "size": size,
            "rows": board.rows,
            "mode": "analysis",
            "archive_games": [],
        }
        return await BaseView._view_base(request, "game.html", template_context)

    @staticmethod
    async def analysis_board_from_game(request: Request) -> Response:
        game_id = request.match_dict["game_id"]
        moves = [move.fake() for move in await Move.filter(game_id=game_id)]

        return await AnalysisView.analysis_board_with_archive(request, moves)

    @staticmethod
    async def analysis_board_from_moves(request: Request) -> Response:
        moves_str = request.match_dict["moves"]
        moves = []
        for move_str in moves_str.split(","):
            x, y, color = move_str.split("-")
            moves.append(
                FakeMove(index=0 if color == "False" else 1, x=int(x), y=int(y))
            )

        return await AnalysisView.analysis_board_with_archive(request, moves)

    @staticmethod
    async def analysis_board_with_archive(
        request: Request, moves: List[FakeMove]
    ) -> Response:
        size = request.headers.get("board-size", 13)
        board = Board(size)

        template_context = {
            "size": size,
            "rows": board.rows,
            "mode": "analysis",
            "archive_games": await ArchiveView.get_archive_games(moves),
            "stones": [Cell.render_stone(move.color, move.y, move.x) for move in moves],
        }  # TODO: hovering over archive suggestions highlight cells on board
        return await BaseView._view_base(request, "game.html", template_context)
