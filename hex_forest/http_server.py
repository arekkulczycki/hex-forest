# -*- coding: utf-8 -*-
from typing import Callable, List, Tuple

from css_html_js_minify import css_minify, html_minify, js_minify
from japronto import Application
from japronto.request.crequest import Request
from japronto.response.py import Response
from jinja2 import Template

from hex_forest.views import AnalysisView, GameView, LobbyView
from hex_forest.views.ai_view import AiView
from hex_forest.views.archive_view import ArchiveView
from hex_forest.views.base_view import BaseView


class HttpServer(LobbyView, GameView, AnalysisView, ArchiveView, AiView):
    """
    Japronto web server.
    """

    _routes: List[Tuple[str, Callable]]
    """All handlers decorated with `@route`."""

    _css: str
    _js: str
    _cookieconsent: str
    _favicon: str
    _wood_grain: str

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

        self.prepare_templates()
        self.prepare_files()
        self.collect_routes()

    def run(self, host: str, port: int) -> None:
        self.app.run(host, port)

    @staticmethod
    def prepare_templates() -> None:
        with open(f"static/lobby.html") as html_file:
            BaseView._lobby_template = Template(html_minify(html_file.read()))

        with open(f"static/game.html") as html_file:
            BaseView._game_template = Template(html_minify(html_file.read()))

    @staticmethod
    def prepare_files() -> None:
        with open("static/style.css") as html_file:
            HttpServer._css = css_minify(html_file.read())

        with open("static/js/js.js") as js_file:
            HttpServer._js = js_minify(js_file.read())

        with open("static/js/cookieconsent.js") as js_file:
            HttpServer._cookieconsent = js_minify(js_file.read())

        with open("static/hex.png", "rb") as image:
            HttpServer._favicon = image.read()

        with open("static/wood-grain.png", "rb") as image:
            HttpServer._wood_grain = image.read()

    def collect_routes(self) -> None:
        for url, handler in self._routes:
            self.app.router.add_route(url, handler)

    # @route("/style.css")
    @staticmethod
    async def styles(request: Request) -> Response:
        return request.Response(text=HttpServer._css, mime_type="text/css")

    # @route("/js.js")
    @staticmethod
    async def scripts(request: Request) -> Response:
        return request.Response(text=HttpServer._js, mime_type="text/javascript")

    @staticmethod
    async def cookieconsent(request: Request) -> Response:
        return request.Response(
            text=HttpServer._cookieconsent, mime_type="text/javascript"
        )

    # @route("/favicon.ico")
    @staticmethod
    async def favicon(request: Request) -> Response:
        return request.Response(body=HttpServer._favicon, mime_type="image/png")

    # @route("/wood-pattern.png")
    @staticmethod
    async def wood_pattern(request: Request) -> Response:
        return request.Response(body=HttpServer._favicon, mime_type="image/png")
