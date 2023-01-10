# -*- coding: utf-8 -*-
from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.common.board import Board
from hex_forest.config import config
from hex_forest.views.base_view import BaseView


class AnalysisView(BaseView):
    """
    Analysis board view (self-play).
    """

    def __init__(self):
        super().__init__()
        self._routes += [("/analysis", self.show_analysis_board)]

    # @route("/game")
    @staticmethod
    async def show_analysis_board(request: Request) -> Response:
        size = request.headers.get("board-size", 13)
        board = Board(size)

        # TODO: wtf is mode?
        websocket_address = f"ws://{config.ws_host}:{config.ws_port}"

        template_context = {
            "size": size,
            "rows": board.rows,
            "websocket_address": websocket_address,
            "mode": "analysis",
        }
        return await BaseView._view_base(request, "game.html", template_context)
