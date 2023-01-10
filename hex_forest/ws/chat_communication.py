# -*- coding: utf-8 -*-
from typing import Awaitable, Callable, Dict

from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.models import Player


class ChatCommunication:
    """
    WebSocket communication related to Chat events.
    """

    _actions: Dict[str, Callable[[WebSocketServerProtocol, Dict, str], Awaitable[None]]]

    def __init__(self):
        """"""

        super().__init__()
        self._actions.update(
            **{
                "chat_message": self._handle_chat_message,
            }
        )

    async def _handle_chat_message(self, player: Player, data: Dict) -> None:
        """"""

        await self.broadcast({
            "action": "chat_message",
            "player_name": player.name,
            "message": data["message"],
        })
