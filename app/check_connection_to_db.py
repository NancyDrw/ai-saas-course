"""Check async connection to PostgreSQL without exposing secrets."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import create_database_engine


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url == "your_database_url_here":
        logger.error("DATABASE_URL is not set. Add it to the local .env file.")
        return 1

    engine = None
    try:
        engine = create_database_engine(database_url)
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, TypeError, ValueError):
        logger.error("Database is unavailable. Check DATABASE_URL and Neon status.")
        return 1
    finally:
        if engine is not None:
            await engine.dispose()

    logger.info("Database connection is available.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
