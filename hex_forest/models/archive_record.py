# -*- coding: utf-8 -*-
from tortoise import Model, fields

from hex_forest.common.cache import SingleArgAsyncCache


class ArchiveRecord(Model):
    """
    DON'T WRITE! This is utility model only to query archive data, but is not represented by any table.
    """

    number: int = fields.IntField(pk=True)
    black_wins: int = fields.IntField()
    x: int = fields.IntField()
    y: int = fields.IntField()

    archive_record_cache: SingleArgAsyncCache = SingleArgAsyncCache(maxsize=4**8)
    """Each key equals to ~ 50 bytes, therefore equalling to cached memory in total ~ 3 MB."""

    @property
    def black_prc(self) -> int:
        return int(self.black_wins / self.number * 100)

    @property
    def next_move(self) -> str:
        return f"{chr(self.y + 97)}{self.x + 1}"
