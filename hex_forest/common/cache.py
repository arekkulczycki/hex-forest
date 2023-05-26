# -*- coding: utf-8 -*-
from functools import wraps

from cache.lru import LRU


class SingleArgAsyncCache:
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
        async def wrapper(key):
            if not self.on:
                return await func(key)

            if isinstance(key, list):
                if len(key) > self.maxlistlength:
                    return await func(key)

                key = tuple(key)

            if key in self.lru:
                return self.lru[key]
            else:
                self.lru[key] = await func(key)
                return self.lru[key]

        return wrapper

    def invalidate(self, key) -> None:
        if isinstance(key, list):
            key = tuple(key)

        if key in self.lru:
            del self.lru[key]

    def clear(self) -> None:
        self.lru = LRU(maxsize=self.maxsize)
