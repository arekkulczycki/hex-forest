# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import traceback
from json import JSONDecodeError
from typing import Dict, Callable, Awaitable

from tortoise.exceptions import DoesNotExist
from websockets.legacy.server import WebSocketServerProtocol

from hex_forest.models import Player
from hex_forest.ws.board_communication import BoardCommunication
from hex_forest.ws.chat_communication import ChatCommunication

PlayerName = str


class WsServer(BoardCommunication, ChatCommunication):
    """
    WebSocket server.
    """

    _actions: [str, Callable[[WsServer, Player, Dict], Awaitable[None]]]

    connected_clients: Dict[WebSocketServerProtocol, Player] = {}
    connected_clients_rev: Dict[PlayerName, WebSocketServerProtocol] = {}

    def __init__(self):
        self._actions = {"assign_player": self._assign_player}
        super().__init__()

    async def listen(
        self, websocket: WebSocketServerProtocol, websocket_path: str
    ) -> None:
        await self._register(websocket)

        async for message in websocket:
            try:
                data = json.loads(message)
            except JSONDecodeError as e:
                print("JSONDecodeError", e, message)
            else:
                try:
                    await self._handle_message(websocket, data)
                except Exception as e:
                    print(e)
                    traceback.print_exc()

        await self._unregister(websocket)

    async def _assign_player(
        self, websocket: WebSocketServerProtocol, data: Dict
    ) -> None:
        """"""

        player = None
        registered = False
        pin = data.get("pin")
        if pin:
            try:
                player = await Player.filter(cookie=pin).first()
            except DoesNotExist:
                pass
            else:
                registered = True
        if not player:
            player = Player(name="guest", cookie="")
            player.is_guest = True

        await self.broadcast(
            {"action": "joined", "player_name": player.name, "registered": registered}
        )
        print(f"broadcasting join of: {player.name}")

        player.websocket = websocket
        self.connected_clients[websocket] = player
        self.connected_clients_rev[player.name] = websocket

    async def _register(self, websocket: WebSocketServerProtocol) -> None:
        """"""

    async def _unregister(self, websocket: WebSocketServerProtocol) -> None:
        """"""

        try:
            player = self.connected_clients[websocket]
        except KeyError:
            print("unknown user unregistered")
            pass
        else:
            del self.connected_clients[websocket]
            del self.connected_clients_rev[player.name]

            await self.broadcast(
                {
                    "action": "leaved",
                    "player_name": player.name,
                    "registered": bool(player.cookie),
                }
            )

    async def _handle_message(
        self, websocket: WebSocketServerProtocol, data: Dict
    ) -> None:
        """"""

        action_name = data["action"]
        action = self._actions.get(action_name)

        if websocket in self.connected_clients:
            player: Player = self.connected_clients[websocket]

            if action:
                print(f"action requested: {action_name} for {player.name}")
                await action(self.connected_clients[websocket], data)
            else:
                raise ValueError(
                    f"Unknown action requested: {action_name} for {player.name}"
                )

        elif action_name == "assign_player":
            await self._assign_player(websocket, data)

        else:
            raise ValueError(f"Action requested for non-assigned player: {action_name}")

    async def broadcast(self, message: Dict) -> None:
        """"""

        message_json = json.dumps(message)
        if self.connected_clients:
            await asyncio.wait(
                [client.send(message_json) for client in self.connected_clients]
            )
