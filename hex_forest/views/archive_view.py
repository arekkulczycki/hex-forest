# -*- coding: utf-8 -*-
import asyncio
from re import match
from typing import List, Tuple

import requests
from asyncpg import InterfaceError
from japronto.request.crequest import Request
from japronto.response.py import Response
from tortoise.exceptions import IntegrityError

from hex_forest.common.board import Cell
from hex_forest.constants import LG_IMPORT_OWNER_NAME
from hex_forest.models import Game, Player, Move
from hex_forest.models.archive_record import ArchiveRecord
from hex_forest.models.game import Status
from hex_forest.models.move import FakeMove
from hex_forest.views.base_view import BaseView


class NotEnoughMoves(Exception):
    """"""


class ArchiveView(BaseView):
    """
    Archive views for browsing finished games.
    """

    def __init__(self):
        super().__init__()
        self._routes += [
            ("/archive/lg_import/{game_id}", self.lg_import),
            ("/archive/lg_bulk_import/{player_id}", self.lg_bulk_import),
        ]

    # @route("/game")
    @staticmethod
    async def lg_import(request: Request) -> Response:
        """"""

        game_id = request.match_dict["game_id"]
        response = requests.get(
            f"https://littlegolem.net/servlet/sgf/{game_id}/game{game_id}.hsgf"
        )
        await ArchiveView._lg_import_from_text(response.text)

        asyncio.create_task(ArchiveView._invalidate_for_game(game_id))

        return request.Response(
            code=301,
            mime_type="text/html",
            headers={
                "Cache-Control": "no-store",
                "Location": f"/?warning=game imported",
            },
        )

    @staticmethod
    async def _invalidate_for_game(game_id: int) -> None:
        game = await Game.get(id=game_id)
        await game.invalidate_archive_record_cache()

    @staticmethod
    async def lg_bulk_import(request: Request) -> Response:
        """"""

        player_id = request.match_dict["player_id"].replace("$", "")
        response = requests.get(
            f"https://littlegolem.net/jsp/info/player_game_list_txt.jsp?plid={player_id}&gtid=hex"
        )
        games = response.text.split("\n\n")
        games_n = len(games)

        for i, game_text in enumerate(games):
            print(f"importing {i} of {games_n}")
            if not game_text.strip():
                continue
            try:
                await ArchiveView._lg_import_from_text(game_text)
            except (IntegrityError, NotEnoughMoves) as e:
                # maybe already imported
                print(e)
                continue
            except ValueError as e:
                print(e)

        ArchiveRecord.archive_record_cache.clear()

        return request.Response(
            code=301,
            mime_type="text/html",
            headers={
                "Cache-Control": "no-store",
                "Location": f"/?warning=games imported",
            },
        )

    @staticmethod
    async def _lg_import_from_text(text: str) -> None:
        """"""

        split_text = text.split(";")
        game_data = split_text[1]
        moves = split_text[2:]
        if len(moves) < 20:
            raise NotEnoughMoves

        game_data_pattern = (
            r"FF\[(.*)\]EV\[(.*)\]PB\[(.*)\]PW\[(.*)\]SZ\[(.*)\]RE\[(.*)\]GC\[(.*)\]SO"
        )
        groups = match(game_data_pattern, game_data)
        if not groups:
            raise ValueError(f"pattern not recognized: {game_data}")

        while True:
            try:
                black, white = await asyncio.gather(
                    Player.get_or_create(
                        {"cookie": "lg_import_super_secret_cookie"},
                        name=f"lg_{groups[3]}",
                    ),
                    Player.get_or_create(
                        {"cookie": "lg_import_super_secret_cookie"},
                        name=f"lg_{groups[4]}",
                    ),
                )
            except InterfaceError:
                # get_or_create seems to be faulty TODO: check if fixed on new releases
                continue
            else:
                break

        size = int(groups[5])
        result = groups[6]
        game_id = groups[7].split("#")[1]

        is_resigned = moves[-1][2:8] == "resign"
        if is_resigned:
            moves.pop(-1)

        has_swap = moves[1][2:6] == "swap"
        if has_swap:
            moves.pop(1)

            # reversing colors as all following moves will be treated swapped
            b = black
            black = white
            white = b

        status = (
            Status.WHITE_WON
            if result == "W"
            else Status.BLACK_WON
            if result == "B"
            else None
        )
        if not status:
            raise ValueError(f"Unknown game result: {result}")

        game = await Game.create(
            owner_id=LG_IMPORT_OWNER_NAME,
            white=white[0],
            black=black[0],
            status=status,
            board_size=size,
            swapped=has_swap,
            lg_import_id=game_id,
        )

        db_moves = []
        for i, move in enumerate(moves):
            x = ord(move[2]) - 97
            y = ord(move[3]) - 97
            if has_swap and i != 0:
                x, y = Cell.swap(x, y)

            db_moves.append(Move(game=game, index=i, x=x, y=y))
        await Move.bulk_create(db_moves)

    @staticmethod
    @ArchiveRecord.archive_record_cache
    async def get_archive_games(moves: Tuple[FakeMove, ...], size: int) -> List[ArchiveRecord]:
        """"""

        # TODO: query that joins proper games
        moves_str = ",".join(
            [
                f"'{move.x},{move.y}{'B' if move.index % 2 == 0 else 'W'}'"
                for move in moves
            ]
        )
        n_moves = len(moves)

        if n_moves:
            records = await ArchiveRecord.raw(
                f"""
                select count(id) as number, sum(id) as black_wins, x, y from (
                    select CASE WHEN game.status = {Status.BLACK_WON} THEN 1 ELSE 0 END as id, move.x, move.y from (
                        select count(game_id) c, game_id from (
                            select game_id, concat(x,',', y, CASE WHEN mod(move.index, 2) = 0 THEN 'B' ELSE 'W' END) as crd from move where move.index < {n_moves}
                        ) m where m.crd in ({moves_str})
                        group by game_id
                    ) grouped join game on game.id = grouped.game_id join move on move.index = {n_moves} and move.game_id = grouped.game_id where c = {n_moves}
                ) calculated group by x, y order by number desc limit 10
                """
            )
        else:
            records = await ArchiveRecord.raw(
                f"""
                select count(id) as number, sum(id) as black_wins, x, y from (
                    select CASE WHEN game.status = {Status.BLACK_WON} THEN 1 ELSE 0 END as id, x, y from (
                        select x, y, game_id from move where index = 0 and (x + y < {size - 1} or (x + y = {size - 1} and x <= {int(size/2)}))
                        union all
                        select ({size - 1} - x) as x, ({size - 1} - y) as y, game_id from move where index = 0 and (x + y > {size - 1} or (x + y = {size - 1} and x > {int(size/2)}))
                    ) all_moves join game on all_moves.game_id = game.id where game.board_size = {size}
                ) all_moves_in_game group by x, y order by number desc limit 15
                """
            )

        return records
