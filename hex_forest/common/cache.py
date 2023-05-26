# -*- coding: utf-8 -*-
from functools import wraps
from typing import Tuple

from cache.lru import LRU


class ArchiveRecordCache:
    """
    Cache async function results that take exactly one argument.
    """

    def __init__(self, maxsize=128, maxlistlength=12):
        """
        :param maxsize: Use maxsize as None for unlimited size cache
        """

        self.maxlistlength = maxlistlength
        self.maxsize = maxsize
        self.lru = LRU(maxsize=maxsize)

        self.on = True

    def __call__(self, func):
        """"""

        @wraps(func)
        async def wrapper(moves, size):
            if not self.on or len(moves) > self.maxlistlength:
                return await func(moves, size)

            key = (moves, size)

            if key in self.lru:
                return self.lru[key]
            else:
                self.lru[key] = await func(*key)
                return self.lru[key]

        return wrapper

    def invalidate(self, moves: Tuple, size: int) -> None:
        key = (moves, size)

        if key in self.lru:
            del self.lru[key]

    def clear(self) -> None:
        self.lru = LRU(maxsize=self.maxsize)
