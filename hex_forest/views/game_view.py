# -*- coding: utf-8 -*-
import traceback

from japronto.request.crequest import Request
from japronto.response.py import Response
from tortoise.exceptions import IntegrityError, DoesNotExist

from hex_forest.common.board import Board, Cell
from hex_forest.models import Player
from hex_forest.models.game import Game, Status
from hex_forest.views.base_view import BaseView


class GameView(BaseView):
    """
    Active game view.
    """

    def __init__(self):
        super().__init__()
        self._routes += [
            ("/game/{game_id}", self.show_board),
            ("/new-game", self.new_game),
        ]

    # @route("/game")
    @staticmethod
    async def show_board(request: Request) -> Response:
        cookie = request.cookies.get("livehex-pin")
        player = cookie and await Player.filter(cookie=cookie).first()

        game_id = request.match_dict["game_id"]
        try:
            game = await Game.get(id=game_id).prefetch_related(
                "owner", "white", "black", "moves"
            )
        except DoesNotExist:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Location": f"/?warning=Game with id {game_id} does not exist.",
                },
            )

        size = 13
        board = Board(size)

        moves = await game.moves.all().order_by("index")
        last_move = moves[-1] if moves else None

        template_context = {
            "size": size,
            "rows": board.rows,
            "white_player": game.white.name if game.white else "join",
            "black_player": game.black.name if game.black else "join",
            "show_swap": len(moves) == 1,
            "show_start": game.owner == player and game.status is Status.PENDING,
            "game_status": game.status,
            "game_status_text": f"status: {Status(game.status).name.lower().replace('_', ' ')}",
            "stones": [Cell.render_stone(move.color, move.x, move.y) for move in moves],
            "marker": Cell.render_marker(last_move.color, last_move.x, last_move.y)
            if last_move
            else None,
        }
        return await BaseView._view_base(request, "game.html", template_context)

    @staticmethod
    async def new_game(request: Request) -> Response:
        cookie = request.cookies.get("livehex-pin")
        player = cookie and await Player.filter(cookie=cookie).first()
        if not player:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Cache-Control": "no-store",
                    "Location": "/?warning=Sorry, can't start a new game as guest.",
                },
            )

        active_games_count = await Game.filter(owner=player).count()
        if active_games_count >= 3:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Cache-Control": "no-store",
                    "Location": "/?warning=Can't have more than 3 active games.",
                },
            )

        try:
            game = await Game.create(owner=player)
        except IntegrityError:
            traceback.print_exc()
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Cache-Control": "no-store",
                    "Location": "/?warning=Sorry, can't start a new game as this time.",
                },
            )

        return request.Response(
            code=301,
            mime_type="text/html",
            headers={"Cache-Control": "no-store", "Location": f"/game/{game.id}"},
        )
