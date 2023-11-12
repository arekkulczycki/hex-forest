# -*- coding: utf-8 -*-
from typing import Callable, List, Tuple

from css_html_js_minify import css_minify, html_minify, js_minify
from japronto import Application
from japronto.request.crequest import Request
from japronto.response.py import Response
from jinja2 import Template

from hex_forest.views import AnalysisView, GameView, LobbyView
from hex_forest.views.archive_view import ArchiveView
from hex_forest.views.base_view import BaseView


class HttpServer(LobbyView, GameView, AnalysisView, ArchiveView):
    """
    Japronto web server.
    """

    _routes: List[Tuple[str, Callable]]
    """All handlers decorated with `@route`."""

    _css: str
    _js: str
    _js_npm: str
    _cookieconsent: str
    _wasm_main: str
    _wasm_search: str
    _wasm_distributor: str
    _wasm_eval: str
    _favicon: str
    _wood_grain: str
    _loader: str

    def __init__(self) -> None:
        self._routes = [
            ("/static/favicon.ico", self.favicon),
            ("/static/hex.png", self.favicon),
            ("/static/style.css", self.styles),
            ("/static/js/js.js", self.scripts),
            ("/static/js/bundle.js", self.scripts_npm),
            ("/static/js/cookieconsent.js", self.cookieconsent),
            ("/static/wasm/main.js", self.wasm_main),
            ("/static/wasm/search_worker.js", self.wasm_search),
            ("/static/wasm/distributor_worker.js", self.wasm_distributor),
            ("/static/wasm/eval_worker.js", self.wasm_eval),
            ("/static/wood-grain.png", self.wood_pattern),
            ("/static/loader.gif", self.loader),
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
        with open("static/js/bundle.js") as js_file:
            HttpServer._js_npm = js_file.read()

        with open("static/js/cookieconsent.js") as js_file:
            HttpServer._cookieconsent = js_minify(js_file.read())

        with open("static/wasm/main.js") as js_file:
            HttpServer._wasm_main = js_file.read()
        with open("static/wasm/search_worker.js") as js_file:
            HttpServer._wasm_search = js_file.read()
        with open("static/wasm/distributor_worker.js") as js_file:
            HttpServer._wasm_distributor = js_file.read()
        with open("static/wasm/eval_worker.js") as js_file:
            HttpServer._wasm_eval = js_file.read()

        with open("static/hex.png", "rb") as image:
            HttpServer._favicon = image.read()
        with open("static/wood-grain.png", "rb") as image:
            HttpServer._wood_grain = image.read()
        with open("static/loader.gif", "rb") as image:
            HttpServer._loader = image.read()

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
    async def scripts_npm(request: Request) -> Response:
        return request.Response(text=HttpServer._js_npm, mime_type="text/javascript")

    @staticmethod
    async def cookieconsent(request: Request) -> Response:
        return request.Response(
            text=HttpServer._cookieconsent, mime_type="text/javascript"
        )

    @staticmethod
    async def wasm_main(request: Request) -> Response:
        return request.Response(
            text=HttpServer._wasm_main, mime_type="text/javascript"
        )

    @staticmethod
    async def wasm_search(request: Request) -> Response:
        return request.Response(
            text=HttpServer._wasm_search, mime_type="text/javascript", headers={
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Embedder-Policy": "require-corp",
            }
        )

    @staticmethod
    async def wasm_distributor(request: Request) -> Response:
        return request.Response(
            text=HttpServer._wasm_distributor, mime_type="text/javascript", headers={
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Embedder-Policy": "require-corp",
            }
        )

    @staticmethod
    async def wasm_eval(request: Request) -> Response:
        return request.Response(
            text=HttpServer._wasm_eval, mime_type="text/javascript", headers={
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Embedder-Policy": "require-corp",
            }
        )

    # @route("/favicon.ico")
    @staticmethod
    async def favicon(request: Request) -> Response:
        return request.Response(body=HttpServer._favicon, mime_type="image/png")

    # @route("/wood-pattern.png")
    @staticmethod
    async def wood_pattern(request: Request) -> Response:
        return request.Response(body=HttpServer._favicon, mime_type="image/png")

    @staticmethod
    async def loader(request: Request) -> Response:
        return request.Response(body=HttpServer._loader, mime_type="image/gif")
