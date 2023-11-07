# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from japronto.request.crequest import Request
from japronto.response.py import Response
from jinja2 import Template

from hex_forest.config import config
from hex_forest.models import Player

TRANSFER_HIGH_LIMIT: int = 50 * 1024


class BaseView:
    """
    Base view.
    """

    _lobby_template: Template
    _game_template: Template

    @staticmethod
    async def _view_base(
        request: Request,
        template: Template,
        template_context: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> Response:
        if headers is None:
            headers = {
                # the following are set in nginx, but leaving for local, as are important for JS SharedMemory
                # "Cross-Origin-Opener-Policy": "same-origin",
                # "Cross-Origin-Embedder-Policy": "require-corp",
            }

        request.transport.set_write_buffer_limits(high=TRANSFER_HIGH_LIMIT)

        template_context["version"] = config.version
        template_context[
            "websocket_address"
        ] = f"://{config.ws_host}:{config.ws_port}"  # wss/ws determined in javascript

        if "player_name" not in template_context:
            cookie = request.cookies.get("livehex-pin", "")
            player = await Player.get_by_cookie(cookie)
            template_context["player_name"] = player.name if player else "guest"

        warning = request.query.get("warning")
        if warning:
            template_context["warning"] = warning

        return request.Response(
            text=template.render(**template_context),
            mime_type="text/html",
            headers=headers,
        )
