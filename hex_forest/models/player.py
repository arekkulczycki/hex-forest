# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

from tortoise import Model, fields
from tortoise.timezone import now
from websockets.legacy.server import WebSocketServerProtocol

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

    created_at: datetime = fields.DatetimeField(auto_now=True)
    last_heartbeat: datetime = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.name

    def is_online(self, now_: Optional[datetime] = None) -> bool:
        return (now_ or now()) - self.last_heartbeat < timedelta(seconds=ONLINE_THRESHOLD)
