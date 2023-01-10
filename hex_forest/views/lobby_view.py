# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from random import randint

from japronto.request.crequest import Request
from japronto.response.py import Response
from tortoise.exceptions import IntegrityError
from tortoise.timezone import now

from hex_forest.config import config
from hex_forest.models import Player
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
        players = await Player.all()

        player = None
        players_online = []
        players_offline = []
        now_ = now()
        for p in players:
            if p.cookie == cookie:
                player = p
                players_online.append(p)

            elif p.is_online(now_):
                players_online.append(p)
            else:
                players_offline.append(p)

        template_context = {
            "websocket_address": websocket_address,
            "is_logged": player is not None,
            "player_name": player.name if player else "guest",
            "players_online": players_online,
            "players_offline": players_offline,
        }

        if player:
            asyncio.create_task(LobbyView._update_player_heartbeat(player, now_))

        return await BaseView._view_base(request, "lobby.html", template_context)

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
            await Player.create(name=name, cookie=cookie)
        except IntegrityError:
            return request.Response(
                code=301,
                mime_type="text/html",
                headers={"Location": "/?warning=Name was already taken."},
            )

        headers = {
            "Access-Control-Expose-Headers": "Set-Cookie",
            "Set-Cookie": f"livehex-pin={cookie}; max-age=2592000; path=/; samesite=strict",
            "Location": "/",
        }

        return request.Response(
            code=301,
            mime_type="text/html",
            headers=headers,
        )
