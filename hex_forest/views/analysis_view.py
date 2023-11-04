# -*- coding: utf-8 -*-
from enum import IntEnum
from typing import List, Optional

from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.common.board import Board, Cell
from hex_forest.constants import MAX_ARCHIVE_RECORD_LENGTH
from hex_forest.models.move import FakeMove, Move
from hex_forest.views.archive_view import ArchiveView
from hex_forest.views.base_view import BaseView


class Action(IntEnum):
    ROTATE: int = 0
    MIRROR: int = 1


class AnalysisView(BaseView):
    """
    Analysis board view (self-play).
    """

    def __init__(self):
        super().__init__()
        self._routes += [
            ("/analysis", self.analysis_board),
            ("/analysis/game/{game_id}", self.analysis_board_from_game),
        ]

    # @route("/game")
    @staticmethod
    async def analysis_board(request: Request) -> Response:
        action: Optional[str] = request.query.get("action")
        moves_str: Optional[str] = request.query.get("moves")

        if action == "rotate":
            return await AnalysisView.analysis_board_action(
                request, moves_str, action=Action.ROTATE
            )
        elif action == "mirror":
            return await AnalysisView.analysis_board_action(
                request, moves_str, action=Action.MIRROR
            )
        else:
            return await AnalysisView.analysis_board_from_moves(request, moves_str)

    @staticmethod
    async def analysis_board_from_moves(
        request: Request, moves_str: Optional[str]
    ) -> Response:
        moves = AnalysisView.get_moves_from_str(moves_str) if moves_str else []

        return await AnalysisView.analysis_board_with_archive(request, moves)

    @staticmethod
    async def analysis_board_action(
        request: Request, moves_str: Optional[str], action: Action
    ) -> Response:
        size = request.headers.get("board-size", 13)

        moves = (
            AnalysisView.get_moves_from_str(moves_str, size=size, action=action)
            if moves_str
            else []
        )

        return await AnalysisView.analysis_board_with_archive(request, moves)

    @staticmethod
    def get_moves_from_str(
        moves_str: str, *, size: int = 13, action: Action = None
    ) -> List[FakeMove]:
        moves = []
        color_mod = None
        for i, move_str in enumerate(moves_str.split(",")):
            cell_id, color_str = move_str.split("-")
            if color_mod is None:
                color_mod = 0 if color_str == "w" else 1

            x, y = Cell.id_to_xy(cell_id)
            # fmt: off
            moves.append(
                FakeMove(
                    index=i + color_mod if action is Action.MIRROR else i,
                    x=size - int(x) - 1 if action is Action.ROTATE else int(y) if action is Action.MIRROR else int(x),
                    y=size - int(y) - 1 if action is Action.ROTATE else int(x) if action is Action.MIRROR else int(y),
                )
            )
            # fmt: on
        return moves

    @staticmethod
    async def analysis_board_from_game(request: Request) -> Response:
        game_id = request.match_dict["game_id"]
        moves = [move.fake() for move in await Move.filter(game_id=game_id)]

        return await AnalysisView.analysis_board_with_archive(request, moves)

    @staticmethod
    async def analysis_board_with_archive(
        request: Request, moves: List[FakeMove]
    ) -> Response:
        size = request.headers.get("board-size", 13)
        board = Board(size=size)

        archive_games = (
            []
            if len(moves) > MAX_ARCHIVE_RECORD_LENGTH
            else await ArchiveView.get_archive_games(tuple(moves), size)
        )

        template_context = {
            "size": size,
            "rows": board.rows,
            "mode": "analysis",
            "archive_games": archive_games,
            "archive_move_limit": MAX_ARCHIVE_RECORD_LENGTH,
            "stones": [
                Cell.render_stone(move.color, move.y, move.x, i)
                for i, move in enumerate(moves)
            ],
        }  # TODO: hovering over archive suggestions highlight cells on board
        return await BaseView._view_base(
            request, BaseView._game_template, template_context
        )
