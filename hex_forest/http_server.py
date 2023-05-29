# -*- coding: utf-8 -*-
from typing import Callable, List, Tuple

from css_html_js_minify import js_minify, css_minify
from japronto import Application
from japronto.request.crequest import Request
from japronto.response.py import Response

from hex_forest.views import LobbyView, GameView, AnalysisView
from hex_forest.views.archive_view import ArchiveView


class HttpServer(LobbyView, GameView, AnalysisView, ArchiveView):
    """
    Japronto web server.
    """

    _routes: List[Tuple[str, Callable]]
    """All handlers decorated with `@route`."""

    def __init__(self) -> None:
        self._routes = [
            ("/static/favicon.ico", self.favicon),
            ("/static/hex.png", self.favicon),
            ("/static/style.css", self.styles),
            ("/static/js/js.js", self.scripts),
            ("/static/js/cookieconsent.js", self.cookieconsent),
            ("/static/wood-grain.png", self.wood_pattern),
        ]
        super().__init__()

        self.app = Application()

        self.collect_routes()

    def run(self, host: str, port: int) -> None:
        self.app.run(host, port)

    def collect_routes(self) -> None:
        for url, handler in self._routes:
            self.app.router.add_route(url, handler)

    # @route("/style.css")
    @staticmethod
    async def styles(request: Request) -> Response:
        with open("static/style.css") as html_file:
            return request.Response(
                text=css_minify(html_file.read()), mime_type="text/css"
            )

    # @route("/js.js")
    @staticmethod
    async def scripts(request: Request) -> Response:
        with open("static/js/js.js") as js_file:
            return request.Response(
                text=js_minify(js_file.read()), mime_type="text/javascript"
            )

    @staticmethod
    async def cookieconsent(request: Request) -> Response:
        with open("static/js/cookieconsent.js") as js_file:
            return request.Response(
                text=js_minify(js_file.read()), mime_type="text/javascript"
            )

    # @route("/favicon.ico")
    @staticmethod
    async def favicon(request: Request) -> Response:
        with open("static/hex.png", "rb") as image:
            return request.Response(body=image.read(), mime_type="image/png")

    # @route("/wood-pattern.png")
    @staticmethod
    async def wood_pattern(request: Request) -> Response:
        with open("static/wood-grain.png", "rb") as image:
            return request.Response(body=image.read(), mime_type="image/png")
