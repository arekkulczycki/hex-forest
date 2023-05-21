# -*- coding: utf-8 -*-
from pydantic import BaseSettings, Field

VERSION_MAJOR: int = 0
VERSION_MINOR: int = 2
VERSION_PATCH: int = 4


class Config(BaseSettings):
    """
    Project settings.
    """

    http_port: int
    ws_host: str
    ws_port: int
    db_url: str  # postgres://postgres:pass@db.host:5432/somedb

    @property
    def version(self) -> str:
        return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

    class Config:
        """
        Settings config.
        """

        env_file = ".env"


config = Config()

TORTOISE_ORM = {
    "connections": {"default": config.db_url},
    "apps": {
        "models": {
            "models": ["hex_forest.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
