

from configs.logger_config import logger
import os
import asyncpg

db_pool = None
logger.info("DB_HOST: %s", os.environ["DB_HOST"])

async def get_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(
                host=os.environ["DB_HOST"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
                database=os.environ["DB_NAME"],
                port=int(os.environ.get("DB_PORT", 5432)),
                min_size=1,
                max_size=2
            )
            logger.info("Successfully connected to PostgreSQL")
        except Exception as exc:
            logger.error("Database connection failed: %s", exc)
            raise

    return db_pool
