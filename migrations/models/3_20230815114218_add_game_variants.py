from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "archiverecord" (
    "number" SERIAL NOT NULL PRIMARY KEY,
    "black_wins" INT NOT NULL,
    "x" INT NOT NULL,
    "y" INT NOT NULL
);
COMMENT ON TABLE "archiverecord" IS 'DON''T WRITE! This is utility model only to query archive data, but is not represented by any table.';;
        ALTER TABLE "game" ADD "variant" SMALLINT NOT NULL  DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "game" DROP COLUMN "variant";
        DROP TABLE IF EXISTS "archiverecord";"""
