# -*- coding: utf-8 -*-
import asyncio
import traceback
from typing import Tuple

from asyncpg import TooManyConnectionsError
from japronto.request.crequest import Request
from japronto.response.py import Response
from tortoise.exceptions import IntegrityError, DoesNotExist

from hex_forest.common.board import Board, Cell
from hex_forest.models import Player
from hex_forest.models.game import Game, Status, Variant
from hex_forest.views.base_view import BaseView
from hex_forest.views.variants.ai_view import AiView
from hex_forest.views.variants.blind_hex_view import BlindHexView


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

    @staticmethod
    async def get_game_data(request: Request) -> Tuple[Player, Game]:
        cookie = request.cookies.get("livehex-pin")
        game_id = request.match_dict["game_id"]

        player = None
        try:
            if cookie:
                player, game = await asyncio.gather(Player.get_by_cookie(cookie), Game.get_by_id(game_id))
            else:
                game = await Game.get_by_id(game_id)
        except TooManyConnectionsError:
            await asyncio.sleep(1)
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Location": f"/?warning=Sorry, we couldn't handle your request due to high traffic on the site.",
                },
            )
        except DoesNotExist:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Location": f"/?warning=Game with id {game_id} does not exist.",
                },
            )

        return player, game

    # @route("/game")
    @staticmethod
    async def show_board(request: Request) -> Response:
        player, game = await GameView.get_game_data(request)
        if game.variant is Variant.BLIND:
            return await BlindHexView.show_board(request, player, game)
        elif game.variant is Variant.AI:
            return await AiView.show_board(request, player, game)

        # the NORMAL variant
        size = 13
        board = Board(size=size)

        moves = await game.moves.all().order_by("index")
        last_move = moves[-1] if moves else None
        moves_n = len(moves)
        turn_int = 0 if game.status is not Status.IN_PROGRESS else 1 if moves_n % 2 == 1 else 2

        template_context = {
            "size": size,
            "rows": board.rows,
            "mode": "game",
            "owner": game.owner.name,
            "white_player": game.white.name if game.white else "join",
            "black_player": game.black.name if game.black else "join",
            "turn": turn_int,
            "show_swap": moves_n == 1,
            "show_start": game.owner == player and game.status is Status.PENDING,
            "game_status": game.status,
            "game_status_text": f"status: {Status(game.status).name.lower().replace('_', ' ')}",
            "stones": [Cell.render_stone(move.color, move.y, move.x) for move in moves],
            "marker": Cell.render_marker(last_move.color, last_move.y, last_move.x)
            if last_move
            else None,
        }
        return await BaseView._view_base(request, BaseView._game_template, template_context)

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

        variant_str: str = request.query["variant"]
        variant = Variant[variant_str.upper()]
        try:
            game = await Game.create(owner=player, variant=variant)
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
