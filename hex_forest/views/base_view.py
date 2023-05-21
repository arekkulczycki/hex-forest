# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from css_html_js_minify import html_minify
from japronto.request.crequest import Request
from japronto.response.py import Response
from jinja2 import Template

from hex_forest.config import config
from hex_forest.models import Player

TRANSFER_HIGH_LIMIT: int = 50 * 1025


class BaseView:
    """
    Base view.
    """

    @staticmethod
    async def _view_base(
        request: Request,
        html_file_name: str,
        template_context: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> Response:
        if headers is None:
            headers = {}

        request.transport.set_write_buffer_limits(high=TRANSFER_HIGH_LIMIT)

        template_context["version"] = config.version
        template_context["websocket_address"] = f"ws://{config.ws_host}:{config.ws_port}"
        if "player_name" not in template_context:
            cookie = request.cookies.get("livehex-pin", "")
            player = await Player.filter(cookie=cookie).first()
            template_context["player_name"] = player.name if player else "guest"

        warning = request.query.get("warning")
        if warning:
            template_context["warning"] = warning

        with open(f"static/{html_file_name}") as html_file:
            template = Template(html_minify(html_file.read()))
            return request.Response(
                text=template.render(**template_context),
                mime_type="text/html",
                headers=headers,
            )
