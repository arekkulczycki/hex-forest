from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE "player" (
    "name" TEXT NOT NULL  PRIMARY KEY,
    "cookie" TEXT NOT NULL
);
COMMENT ON TABLE "player" IS 'Player/user model.';
CREATE TABLE "game" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "result" SMALLINT NOT NULL,
    "started_at" TIMESTAMPTZ,
    "finished_at" TIMESTAMPTZ,
    "black_id" TEXT REFERENCES "player" ("name") ON DELETE CASCADE,
    "white_id" TEXT REFERENCES "player" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "game"."result" IS 'PENDING: 0\nIN_PROGRESS: 1\nWHITE_WIN: 2\nBLACK_WIN: 3';
COMMENT ON TABLE "game" IS 'A game created by one of the players.';
CREATE TABLE "move" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "x" INT NOT NULL,
    "y" INT NOT NULL,
    "game_id" INT NOT NULL REFERENCES "game" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "move" IS 'A move played in an existing game.';
CREATE TABLE "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
