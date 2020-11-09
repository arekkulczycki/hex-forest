import json
import os

import numpy as np
from css_html_js_minify import html_minify, js_minify, css_minify
from jinja2 import Template
from stable_baselines import PPO2

from constants import STORE_MINIMUM, WHITE_COLOR, BLACK_COLOR
from decorators import ssl_decorator
from models import Board

VERSION_MAJOR = 0
VERSION_MINOR = 2
VERSION_PATCH = 4


class HttpCommunicator:

    def __init__(self, db):
        self.db = db

    @ssl_decorator
    def styles(self, request):
        with open('static/style.css') as html_file:
            return request.Response(text=css_minify(html_file.read()), mime_type='text/css')

    @ssl_decorator
    def scripts(self, request):
        with open('static/js.js') as js_file:
            return request.Response(text=js_minify(js_file.read()), mime_type='text/javascript')

    @ssl_decorator
    def favicon(self, request):
        with open('static/hex.png', 'rb') as favicon:
            return request.Response(body=favicon.read(), mime_type='image/png')

    @ssl_decorator
    def wood_pattern(self, request):
        with open('static/wood-grain.png', 'rb') as favicon:
            return request.Response(body=favicon.read(), mime_type='image/png')

    @ssl_decorator
    def show_board(self, request, mode='', size=13):
        board = Board(size)
        with open('static/index.html') as html_file:
            template = Template(html_minify(html_file.read()))
            fields = []

            # lock.acquire()
            # with open('players.json', 'r') as players_file:
            #     players = json.loads(players_file.read())
            # lock.release()
            websocket_route = mode

            target = os.environ.get('TARGET')
            if target == 'all':
                websocket_address = f'ws://localhost:8001/{websocket_route}'
            else:
                websocket_address = f'wss://hex-forest-ws.herokuapp.com/{websocket_route}'

            games = self.db.load_all_games()
            template_context = {
                'version': f'{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}',
                'size': size,
                'rows': board.rows,
                'websocket_address': websocket_address,
                'mode': mode,
                'store_minimum': STORE_MINIMUM,
                'black_color': BLACK_COLOR,
                'white_color': WHITE_COLOR,
                'games': games
            }
            return request.Response(text=template.render(**template_context), mime_type='text/html')

    @ssl_decorator
    def show_free_board(self, request):
        return self.show_board(request, 'analysis')

    @ssl_decorator
    def show_board_with_priviledges(self, request):
        return self.show_board(request, 'p')

    @ssl_decorator
    def show_board_11(self, request):
        return self.show_board(request, 'analysis', 11)

    @ssl_decorator
    def show_board_19(self, request):
        return self.show_board(request, 'analysis', 19)


async def get_predicted_action_async(request):
    transfer_ball_up_field_model = PPO2.load(f'static/transfer_ball_up_field.v12')
    body = request.body
    if body:
        obs_json = request.body
        obs = json.loads(obs_json)
        action, _states = transfer_ball_up_field_model.predict(np.array(obs))
    else:
        action = 0
    return request.Response(text=str(action), mime_type='text/json')


async def get_predicted_cross_async(request):
    assist_cross_model = PPO2.load(f'static/assist_cross.v11')
    body = request.body
    if body:
        obs_json = request.body
        obs = json.loads(obs_json)
        action, _states = assist_cross_model.predict(np.array(obs))
    else:
        action = 0
    return request.Response(text=str(action), mime_type='text/json')
