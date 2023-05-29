# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Iterable

from cache import AsyncLRU
from tortoise import Model, fields, BaseDBAsyncClient
from tortoise.timezone import now
from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.constants import LG_IMPORT_OWNER_NAME

ONLINE_THRESHOLD: int = 30  # seconds


class OnlinePlayer:
    websocket: Optional[WebSocketServerProtocol]
    is_guest: bool = False

    async def send(self, message: Dict) -> None:
        await self.websocket.send(json.dumps(message))


class Player(Model, OnlinePlayer):
    """
    Player/user model.
    """

    name: str = fields.CharField(pk=True, max_length=63)
    cookie: str = fields.CharField(max_length=63)
    google_account: str = fields.CharField(max_length=63, null=True)
    # ip: str = fields.CharField(max_length=15, null=True)  # TODO: add validation to prevent creating multiple

    created_at: datetime = fields.DatetimeField(auto_now=True)
    last_heartbeat: datetime = fields.DatetimeField(auto_now=True)

    all_cache = AsyncLRU(1)

    def __str__(self):
        return self.name

    def is_online(self, now_: Optional[datetime] = None) -> bool:
        return (now_ or now()) - self.last_heartbeat < timedelta(
            seconds=ONLINE_THRESHOLD
        )

    async def save(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
        update_fields: Optional[Iterable[str]] = None,
        force_create: bool = False,
        force_update: bool = False,
    ) -> None:
        await super().save(using_db, update_fields, force_create, force_update)

        # TODO: implement invalidation when query is no longer datetime-based
        # if force_create:
        #     asyncio.create_task(Player.invalidate_all_cache())

    @staticmethod
    @all_cache
    async def get_all(_: datetime):
        return await Player.exclude(name__startswith=LG_IMPORT_OWNER_NAME).all()

    @staticmethod
    async def invalidate_all_cache() -> None:
        Player.all_cache.lru.clear()
        await Player.get_all(now())

    @staticmethod
    @AsyncLRU(128)
    async def get_by_cookie(cookie: str) -> Player:
        return await Player.filter(cookie=cookie).first()
