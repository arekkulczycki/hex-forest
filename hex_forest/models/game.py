# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Dict, Optional, List

from tortoise import Model, fields
from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.models.archive_record import ArchiveRecord

if TYPE_CHECKING:
    from hex_forest.models import Move
    from hex_forest.models.move import FakeMove
    from hex_forest.models.player import Player
    from hex_forest.ws_server import PlayerName


class Status(IntEnum):
    PENDING = 0
    IN_PROGRESS = 1
    WHITE_WON = 2
    BLACK_WON = 3


class Game(Model):
    """
    A game created by one of the players.
    """

    id: int = fields.IntField(pk=True)
    owner: Player = fields.ForeignKeyField(
        "models.Player", related_name="games_started"
    )
    white: Optional[Player] = fields.ForeignKeyField(
        "models.Player", related_name="games_white", null=True
    )
    black: Optional[Player] = fields.ForeignKeyField(
        "models.Player", related_name="games_black", null=True
    )
    status: Status = fields.IntEnumField(Status, default=Status.PENDING)
    board_size: int = fields.IntField(default=13)
    swapped: bool = fields.BooleanField(default=False)

    started_at: Optional[datetime] = fields.DatetimeField(null=True)
    finished_at: Optional[datetime] = fields.DatetimeField(null=True)

    # game settings
    timer_seconds: Optional[int] = fields.IntField(null=True)
    increment_seconds: Optional[int] = fields.IntField(null=True)

    lg_import_id = fields.CharField(max_length=7, unique=True, null=True)

    moves: fields.ReverseRelation["Move"]

    _move_count_cache: Optional[int] = None

    async def send(
        self, clients: Dict[PlayerName, WebSocketServerProtocol], message: Dict
    ) -> None:
        """"""

        tasks = []

        message_json = json.dumps(message)

        if self.owner.name in clients:
            try:
                tasks.append(clients[self.owner.name].send(message_json))
            except KeyError:
                pass

        if self.white and self.white != self.owner and self.white.name in clients:
            try:
                tasks.append(clients[self.white.name].send(message_json))
            except KeyError:
                pass

        if self.black and self.black != self.owner and self.black.name in clients:
            try:
                tasks.append(clients[self.black.name].send(message_json))
            except KeyError:
                pass

        if message["action"] == "move":
            if await self.move_count == 0:
                msg_json = json.dumps({"action": "showSwap"})
                try:
                    tasks.append(clients[self.white.name].send(msg_json))
                except KeyError:
                    pass

            self._move_count_cache += 1

        await asyncio.wait(tasks)

    @property
    async def move_count(self) -> int:
        """"""

        if self._move_count_cache is None:
            move_count = await self.moves.all().count()
            self._move_count_cache = move_count

        return self._move_count_cache

    @property
    async def turn(self) -> bool:
        """
        No moves means black turn therefore False, as all other even numbers. Odd numbers return True.
        """

        return await self.move_count % 2 == 1

    async def save(self, *args, **kwargs) -> None:
        await super().save(*args, **kwargs)

        if ArchiveRecord.archive_record_cache.on and self.status in [Status.BLACK_WON, Status.WHITE_WON]:
            await self.invalidate_archive_record_cache()

    async def invalidate_archive_record_cache(self) -> None:
        moves: List[FakeMove] = [move.fake() for move in await self.moves.filter(
            index__lt=ArchiveRecord.archive_record_cache.maxlistlength
        )]

        for i in range(ArchiveRecord.archive_record_cache.maxlistlength):
            ArchiveRecord.archive_record_cache.invalidate(moves[:i+1])
