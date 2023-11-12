from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "game" ALTER COLUMN "variant" TYPE SMALLINT USING "variant"::SMALLINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "game" ALTER COLUMN "variant" TYPE SMALLINT USING "variant"::SMALLINT;"""
