# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from typing import Iterable, TYPE_CHECKING, Optional, Tuple

from tortoise import Model, fields

from hex_forest.common import BitBoard

if TYPE_CHECKING:
    from hex_forest.models import Game, Player

Color: bool
"""True for white, False for black"""


class Move(Model):
    """
    A move played in an existing game.
    """

    id: int = fields.IntField(pk=True)
    game: Game = fields.ForeignKeyField("models.Game", related_name="moves")
    index: int = fields.IntField()
    x: int = fields.IntField()
    y: int = fields.IntField()

    done_at: datetime = fields.DatetimeField(auto_now=True)
    seconds_left: Optional[int] = fields.IntField(null=True)

    class Meta:
        unique_together = (("game", "index"), )

    @property
    def color(self) -> Color:
        """
        Color of the stone placed in that move. First stone (0) is black, therefore even numbers return False.
        """

        return self.index % 2 != 0

    @property
    def player(self) -> Player:
        return self.game.white if self.color else self.game.black

    def fake(self) -> FakeMove:
        return FakeMove(index=self.index, x=self.x, y=self.y)

    def get_mask(self, size: Optional[int] = None) -> BitBoard:
        return 1 << ((self.x - 1) + self.y * (size or self.game.board_size))


@dataclass
class FakeMove:
    index: int
    x: int
    y: int

    @property
    def color(self) -> Color:
        return self.index % 2 != 0

    def get_mask(self, size: int) -> BitBoard:
        return 1 << ((self.x - 1) + self.y * size)

    def __hash__(self):  # TODO: add proper type hint
        return hash((self.index, self.x, self.y))

    def get_coord(self) -> str:
        """"""

        return f"{chr(self.x + 97)}{self.y}"

    @classmethod
    def from_coord(cls, index: int, coord: str) -> FakeMove:
        """"""

        groups = groupby(coord, str.isalpha)
        col_str, row_str = ("".join(g[1]) for g in groups)

        return cls(index, ord(col_str) - 97, int(row_str))

    @staticmethod
    def mask_from_coord(coord: str, size: int) -> BitBoard:
        """"""

        col_str: str
        row_str: str
        g: Tuple[bool, Iterable]

        groups = groupby(coord, str.isalpha)
        col_str, row_str = ("".join(g[1]) for g in groups)

        # a1 => (0, 0) => 0b1
        return 1 << (ord(col_str) - 97 + size * (int(row_str) - 1))
