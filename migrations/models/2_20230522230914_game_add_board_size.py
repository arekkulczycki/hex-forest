from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        INSERT INTO "player" (name, cookie) VALUES ('lg', 'lg_import_super_secret_cookie');
        ALTER TABLE "game" ADD "board_size" INT NOT NULL  DEFAULT 13;
        ALTER TABLE "game" ADD "lg_import_id" VARCHAR(7)  UNIQUE;
        CREATE UNIQUE INDEX "uid_game_lg_impo_709873" ON "game" ("lg_import_id");
        CREATE UNIQUE INDEX "uid_move_game_id_3fb6d9" ON "move" ("game_id", "index");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "player" where name='lg';
        DROP INDEX "uid_move_game_id_3fb6d9";
        DROP INDEX "idx_game_lg_impo_709873";
        ALTER TABLE "game" DROP COLUMN "board_size";
        ALTER TABLE "game" DROP COLUMN "lg_import_id";"""
