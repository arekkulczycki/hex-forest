# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta
from random import randint
from typing import List, Optional, Tuple

from japronto.request.crequest import Request
from japronto.response.py import Response
from tortoise.exceptions import IntegrityError
from tortoise.timezone import now

from hex_forest.config import config
from hex_forest.constants import LG_IMPORT_OWNER_NAME, ADMIN_NAME
from hex_forest.models import Player, Game
from hex_forest.views.base_view import BaseView


class LobbyView(BaseView):
    """
    Class_docstring
    """

    def __init__(self):
        # self.event_loop = asyncio.get_event_loop()
        super().__init__()
        self._routes += [("/", self.lobby), ("/login/{player_name}", self.login)]

    # @route("/")
    @staticmethod
    async def lobby(request: Request) -> Response:
        websocket_address = f"ws://{config.ws_host}:{config.ws_port}/"
        cookie = request.cookies.get("livehex-pin")
        now_ = now()

        # datetime to get cached players list for that moment in time
        tm = now_ - timedelta(seconds=now_.second, microseconds=now_.microsecond)

        players, active_games, finished_games = await asyncio.gather(
            Player.get_all(tm),
            Game.get_open(),
            Game.get_finished(),
        )

        player, players_online, players_offline = LobbyView._collect_players(
            players, cookie, now_
        )

        your_games, other_games = LobbyView._collect_games(active_games, player)

        template_context = {
            "websocket_address": websocket_address,
            "is_logged": player is not None,
            "player_name": player.name if player else "guest",
            "players_online": players_online,
            "players_offline": players_offline,
            "your_games": your_games,
            "other_games": other_games,
            "finished_games": finished_games,
            "is_admin": player and player.name == ADMIN_NAME,
        }

        if player:
            asyncio.create_task(LobbyView._update_player_heartbeat(player, now_))

        return await BaseView._view_base(request, BaseView._lobby_template, template_context)

    @staticmethod
    def _collect_players(
        players: List[Player], cookie: str, now_: datetime
    ) -> Tuple[Optional[Player], List, List]:
        """"""

        player = None
        players_online = []
        players_offline = []
        for p in players:
            if p.cookie == cookie:
                player = p
                players_online.append(p)

            elif p.is_online(now_):
                players_online.append(p)
            else:
                players_offline.append(p)

        return player, players_online, players_offline

    @staticmethod
    def _collect_games(
        games: List[Game], player: Optional[Player]
    ) -> Tuple[List, List]:
        """"""

        your_games = []
        other_games = []

        for game in games:
            if player and player == game.white or player == game.black:
                your_games.append(game)
            else:
                other_games.append(game)

        return your_games, other_games

    @staticmethod
    async def _update_player_heartbeat(player: Player, now_: datetime) -> None:
        player.last_heartbeat = now_
        try:
            await player.save()
        except IntegrityError:
            import traceback

            traceback.print_exc()

    @staticmethod
    async def login(request: Request) -> Response:
        name: str = request.match_dict["player_name"]
        cookie: str = str(randint(100000, 999999))

        try:
            if name.startswith(LG_IMPORT_OWNER_NAME):
                raise IntegrityError

            await Player.create(name=name, cookie=cookie)
        except IntegrityError:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={
                    "Cache-Control": "no-store",
                    "Location": "/?warning=Name was already taken.",
                },
            )

        headers = {
            "Access-Control-Expose-Headers": "Set-Cookie",
            "Set-Cookie": f"livehex-pin={cookie}; max-age=2592000; path=/; samesite=strict",
            "Cache-Control": "no-store",
            "Location": "/",
            "SameSite": "Strict",
        }

        return request.Response(
            code=301,
            mime_type="text/html",
            headers=headers,
        )
