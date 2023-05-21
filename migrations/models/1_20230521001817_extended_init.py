from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "game" ADD "timer_seconds" INT;
        ALTER TABLE "game" ADD "swapped" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "game" ADD "status" SMALLINT NOT NULL  DEFAULT 0;
        ALTER TABLE "game" ADD "increment_seconds" INT;
        ALTER TABLE "game" ADD "owner_id" VARCHAR(63) NOT NULL;
        ALTER TABLE "game" DROP COLUMN "result";
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE VARCHAR(63) USING "black_id"::VARCHAR(63);
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE VARCHAR(63) USING "black_id"::VARCHAR(63);
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE VARCHAR(63) USING "black_id"::VARCHAR(63);
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE VARCHAR(63) USING "white_id"::VARCHAR(63);
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE VARCHAR(63) USING "white_id"::VARCHAR(63);
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE VARCHAR(63) USING "white_id"::VARCHAR(63);
        ALTER TABLE "move" ADD "seconds_left" INT;
        ALTER TABLE "move" ADD "index" INT NOT NULL;
        ALTER TABLE "move" ADD "done_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "player" ADD "google_account" VARCHAR(63);
        ALTER TABLE "player" ADD "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "player" ADD "last_heartbeat" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE VARCHAR(63) USING "cookie"::VARCHAR(63);
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE VARCHAR(63) USING "cookie"::VARCHAR(63);
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE VARCHAR(63) USING "cookie"::VARCHAR(63);
        ALTER TABLE "game" ADD CONSTRAINT "fk_game_player_8c520076" FOREIGN KEY ("owner_id") REFERENCES "player" ("name") ON DELETE CASCADE;"""

"""
CREATE SEQUENCE "game_id_seq" OWNED BY "game.id";
ALTER TABLE "game" ALTER COLUMN "id" SET DEFAULT nextval('game_id_seq');
"""

async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "game" DROP CONSTRAINT "fk_game_player_8c520076";
        ALTER TABLE "game" ADD "result" SMALLINT NOT NULL;
        ALTER TABLE "game" DROP COLUMN "timer_seconds";
        ALTER TABLE "game" DROP COLUMN "swapped";
        ALTER TABLE "game" DROP COLUMN "status";
        ALTER TABLE "game" DROP COLUMN "increment_seconds";
        ALTER TABLE "game" DROP COLUMN "owner_id";
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE TEXT USING "black_id"::TEXT;
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE TEXT USING "black_id"::TEXT;
        ALTER TABLE "game" ALTER COLUMN "black_id" TYPE TEXT USING "black_id"::TEXT;
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE TEXT USING "white_id"::TEXT;
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE TEXT USING "white_id"::TEXT;
        ALTER TABLE "game" ALTER COLUMN "white_id" TYPE TEXT USING "white_id"::TEXT;
        ALTER TABLE "move" DROP COLUMN "seconds_left";
        ALTER TABLE "move" DROP COLUMN "index";
        ALTER TABLE "move" DROP COLUMN "done_at";
        ALTER TABLE "player" DROP COLUMN "google_account";
        ALTER TABLE "player" DROP COLUMN "created_at";
        ALTER TABLE "player" DROP COLUMN "last_heartbeat";
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE TEXT USING "cookie"::TEXT;
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE TEXT USING "cookie"::TEXT;
        ALTER TABLE "player" ALTER COLUMN "cookie" TYPE TEXT USING "cookie"::TEXT;"""
