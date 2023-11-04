# -*- coding: utf-8 -*-
from itertools import groupby
from typing import Tuple


class Cell:

    def __init__(self, x: int, y: int):
        if y < 0 or x < 0:
            raise Exception
        self.id = self.get_id(x, y)
        self.points = self.generate_points(y, x)
        self.width = 15.07
        self.state = 0  # 0-empty, 1-black, 2-white

        self.cx = self.stone_x(y, x)
        self.cy = self.stone_y(y)

    @classmethod
    def get_id(cls, x, y):
        return f'{chr(x + 97)}{y + 1}'

    @classmethod
    def stone_id(cls, x, y, color):
        return f"{cls.get_id(x, y)}-{('w' if  color else 'b')}"

    @classmethod
    def id_to_xy(cls, id_: str):
        groups = groupby(id_, str.isalpha)
        col_str, row_str = ("".join(g[1]) for g in groups)
        return ord(col_str) - 97, int(row_str) - 1

    @classmethod
    def stone_x(cls, y, x):
        return 60.0 + x * 30 + y * 15

    @classmethod
    def stone_y(cls, y):
        return 30 + y * 25.98

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

    @staticmethod
    def render_stone(color: bool, y: int, x: int, order: int = 0) -> str:
        """"""

        id_ = Cell.stone_id(x, y, color)
        text_color = "white" if color else "black"
        cx = Cell.stone_x(y, x)
        cy = Cell.stone_y(y)
        return f'<circle id="{id_}" cx="{cx}" cy="{cy}" r="11.0" fill="{text_color}" order="{order}" ' \
               f'onclick="sendRemoveStone(\'{id_}\')"></circle>'

    @staticmethod
    def render_marker(color: bool, y: int, x: int) -> str:
        """"""

        id_ = f"{x}-{y}-{color}"
        cx = Cell.stone_x(y, x)
        cy = Cell.stone_y(y)
        return f'<circle id="lastMoveMarker" cx="{cx}" cy="{cy}" r="6.0" fill="red" onclick="sendRemoveStone(\'{id_}\')"></circle>'

    @staticmethod
    def reverse(x: int, y: int, size: int) -> Tuple[int, int]:
        """
        Get equivalent move but mirrored across short diagonal (or 180 deg rotation).
        """

        return size - x - 1, size - y - 1

    @staticmethod
    def swap(x: int, y: int) -> Tuple[int, int]:
        """
        Get equivalent move for opposite color, i.e. mirrored across long diagonal.
        """

        return y, x
