# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import wraps
from typing import Awaitable, Callable, List, TYPE_CHECKING, Tuple

from cache.lru import LRU

from hex_forest.constants import MAX_ARCHIVE_RECORD_LENGTH

if TYPE_CHECKING:
    from hex_forest.models import ArchiveRecord
    from hex_forest.models.move import FakeMove


class ArchiveRecordCache:
    """
    Cache async function results that take exactly one argument.
    """

    def __init__(self, maxsize: int = 128):
        """
        :param maxsize: Use maxsize as None for unlimited size cache
        """

        self.maxsize: int = maxsize
        self.lru: LRU = LRU(maxsize=maxsize)

        self.on: bool = True

    def __call__(
        self,
        func: Callable[[Tuple[FakeMove, ...], int], Awaitable[List[ArchiveRecord]]],
    ):
        """"""

        @wraps(func)
        async def wrapper(
            moves: Tuple[FakeMove, ...], size: int
        ) -> List[ArchiveRecord]:
            if not self.on or len(moves) > MAX_ARCHIVE_RECORD_LENGTH:
                return await func(moves, size)

            key = (moves, size)

            if key in self.lru:
                return self.lru[key]
            else:
                self.lru[key] = await func(*key)
                return self.lru[key]

        return wrapper

    def invalidate(self, moves: Tuple[FakeMove, ...], size: int) -> None:
        key = (moves, size)

        if key in self.lru:
            del self.lru[key]

    def clear(self) -> None:
        self.lru = LRU(maxsize=self.maxsize)
