# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from tortoise import Model, fields

if TYPE_CHECKING:
    from hex_forest.models import Game, Player

Color: bool
"""True for white, False for black"""


class Move(Model):
    """
    A move played in an existing game.
    """

    game: Game = fields.ForeignKeyField("models.Game", related_name="moves")
    index: int = fields.IntField()
    x: int = fields.IntField()
    y: int = fields.IntField()

    done_at: datetime = fields.DatetimeField(auto_now=True)
    seconds_left: Optional[int] = fields.IntField(null=True)

    @property
    def color(self) -> Color:
        """
        Color of the stone placed in that move. First stone (0) is black, therefore even numbers return False.
        """

        return self.index % 2 != 0

    @property
    def player(self) -> Player:
        return self.game.white if self.color else self.game.black
