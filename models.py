import json
import os
from decimal import Decimal
from json import JSONEncoder
from time import time

import psycopg2
import boto3
# from sqlalchemy import create_engine, Column, Integer
# from sqlalchemy.ext.declarative import declarative_base
#
# Base = declarative_base()
from boto3.dynamodb.conditions import Key


class Player:

    def __init__(self, id, websocket, name, present=True):
        self.id = id
        self.websocket = websocket
        self.name = name
        self.present = present
        self.turn = 1

    def __str__(self):
        return str(self.id) if self else '...'

    async def send(self, message):
        await self.websocket.send(message)


class DictEncoder(JSONEncoder):
    def default(self, o):
        d = o.__dict__
        try:
            del d['websocket']
        except KeyError:
            pass
        return d


class Board:

    def __init__(self, board_size=13):
        self.board_size = board_size
        self.rows = self.generate_rows(board_size)

    @staticmethod
    def generate_rows(board_size):
        rows = []
        for r in range(board_size):
            cells = []
            for c in range(board_size):
                cell = Cell(r, c)
                cells.append(cell)
            rows.append(cells)
        return rows


class Cell:

    def __init__(self, r, c):
        r = int(r)
        c = int(c)
        if r < 0 or c < 0:
            raise Exception
        self.id = f'{chr(c + 97)}{r + 1}'
        self.points = self.generate_points(r, c)
        self.width = 15.07
        self.state = 0  # 0-empty, 1-black, 2-white

    @classmethod
    def stone_x(cls, r, c):
        return 60.0 + c * 30 + r * 15

    @classmethod
    def stone_y(cls, r):
        return 30 + r * 25.98

    @staticmethod
    def generate_points(r, c):
        a_1 = 60.0 + c * 30 + r * 15
        a_2 = 47.4 + r * 25.98
        b_1 = 75.07 + c * 30 + r * 15
        b_2 = 38.70 + r * 25.98

        c_1 = 75.07 + c * 30 + r * 15
        c_2 = 21.30 + r * 25.98
        d_1 = 60.0 + c * 30 + r * 15
        d_2 = 12.60 + r * 25.98

        e_1 = 44.93 + c * 30 + r * 15
        e_2 = 21.30 + r * 25.98
        f_1 = 44.93 + c * 30 + r * 15
        f_2 = 38.70 + r * 25.98

        points = [
            '{:.2f},{:.2f}'.format(a_1, a_2),
            '{:.2f},{:.2f}'.format(b_1, b_2),
            '{:.2f},{:.2f}'.format(c_1, c_2),
            '{:.2f},{:.2f}'.format(d_1, d_2),
            '{:.2f},{:.2f}'.format(e_1, e_2),
            '{:.2f},{:.2f}'.format(f_1, f_2)
        ]
        return ' '.join(points)


# class Position(Base):
#     __tablename__ = 'positions'
#
#     id = Column(Integer, primary_key=True)


class Position:

    def __init__(self, id):
        self.id = id


class Postgres:

    def __init__(self):
        # self.engine = create_engine(os.environ['DATABASE_URL'])
        self.connection = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
        # self.create_tables()

    @property
    def cursor(self):
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def store_position(self):
        cur = self.cursor
        cur.execute('SQL')
        self.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()

    def create_tables(self):
        self.cursor.execute("create table positions (id id primary key, ...)")


class DynamoDB:

    def __init__(self):
        self.aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        # self.client = boto3.client('dynamodb', aws_access_key_id=self.aws_access_key_id,
        #                            aws_secret_access_key=self.aws_secret_access_key)
        self.client = boto3.resource('dynamodb', region_name='eu-central-1', aws_access_key_id=self.aws_access_key_id,
                                     aws_secret_access_key=self.aws_secret_access_key)

    def get_position_result(self, opening, position, size=13):
        position = sorted(position, key=self.position_sorting_key)
        length = len(position)

        table = self.client.Table('Positions')
        condition = Key('size#opening').eq(f'{size}#{opening}') & Key('length').eq(length)
        try:
            response = table.query(
                KeyConditionExpression=condition
            )
            items = response.get('Items')
        except Exception as e:
            print(e)
            return 0

        for item in items:
            if item.get('all_moves') == position:
                return int(item.get('winner'))
        return 0

    async def get_position_result_async(self, opening, position, size=13):
        return self.get_position_result(opening, position, size)

    def get_positions_for(self, opening, position=None, size=13):
        if position is None:
            condition = Key('size#opening').eq(f'{size}#{opening}') & Key('length').gte(0)
        else:
            # position = sorted(position, key=self.position_sorting_key)
            min_length = len(position)
            print(min_length, position, size, opening)
            condition = Key('size#opening').eq(f'{size}#{opening}') & Key('length').gte(min_length)

        table = self.client.Table('Positions')
        try:
            response = table.query(
                KeyConditionExpression=condition,
                ProjectionExpression='all_moves, winner'
            )
            print(response.get('Items'))
        except Exception as e:
            print(e)
            return []
        return response.get('Items')

    async def get_positions_for_async(self, opening, position=None, size=13):
        return self.get_positions_for(opening, position, size)

    def store_position(self, opening, position, winner, size=13):
        position = sorted(position, key=self.position_sorting_key)

        table = self.client.Table('Positions')
        item = {
            'size#opening': f'{size}#{opening}',
            'length': len(position),
            'all_moves': position,
            'winner': winner
        }
        try:
            response = table.put_item(
                Item=item
            )
        except Exception as e:
            print(e)
            return
        return response

    @staticmethod
    def position_sorting_key(move):
        split = move.split('-')
        if len(split) < 2:
            raise Exception(f'move cannot be handled: {move}')
        return int(split[0]) * 100 + int(split[1])

    @staticmethod
    def position_move_bigger(move_a, move_b):
        split_a = move_a.split('-')
        split_b = move_b.split('-')
        return int(split_a[0]) * 100 + int(split_a[1]) > int(split_b[0]) * 100 + int(split_b[1])

    async def store_position_async(self, opening, position, winner, size=13):
        return self.store_position(opening, position, winner, size)

    def save_game(self, game_id, position, players):
        table = self.client.Table('Games')
        item = {
            'game_id': game_id,
            'timestamp': str(int(time())),
            'position': position,
            'player_1_name': players.get(1).name,
            'player_2_name': players.get(2).name
        }
        response = table.put_item(
            Item=item
        )
        return response

    async def save_game_async(self, game_id, position, players):
        return self.save_game(game_id, position, players)

    def load_game(self, game_id):
        table = self.client.Table('Games')
        condition = Key('game_id').eq(game_id)
        try:
            response = table.query(
                KeyConditionExpression=condition
            )
            items = response.get('Items')
        except Exception as e:
            print(e)
            return None
        return items[0] if items else None

    def load_all_games(self):
        table = self.client.Table('Games')
        try:
            response = table.scan(
                ProjectionExpression='game_id, player_1_name, player_2_name'
            )
            items = response.get('Items', [])
        except Exception as e:
            print(e)
            return []
        return items


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        if isinstance(o, set):
            return list(o)
        return super().default(o)
