"""Create one idempotent, non-personal demo profile for an admin presentation."""

import asyncio
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from .database import Base, CreditTransaction, User, create_database_engine


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEMO_TELEGRAM_ID = 9_900_000_001
DEMO_USERNAME = "intima_demo"
DEMO_CREDITS = Decimal("5.00")
DEMO_BONUS_CATEGORY = "Демо-бонус"
DEMO_BONUS_DESCRIPTION = "Стартові кредити для презентації Intima"


async def seed_demo_profile() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url == "your_database_url_here":
        raise RuntimeError("DATABASE_URL is not configured.")

    engine = create_database_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == DEMO_TELEGRAM_ID)
            )
            created_profile = user is None
            if user is None:
                user = User(
                    telegram_id=DEMO_TELEGRAM_ID,
                    username=DEMO_USERNAME,
                    first_name="Intima Demo",
                )
                session.add(user)
                await session.flush()

            demo_bonus = await session.scalar(
                select(CreditTransaction).where(
                    CreditTransaction.user_id == user.id,
                    CreditTransaction.category == DEMO_BONUS_CATEGORY,
                    CreditTransaction.description == DEMO_BONUS_DESCRIPTION,
                )
            )
            if demo_bonus is None:
                session.add(
                    CreditTransaction(
                        user_id=user.id,
                        transaction_type="income",
                        amount=DEMO_CREDITS,
                        category=DEMO_BONUS_CATEGORY,
                        description=DEMO_BONUS_DESCRIPTION,
                        occurred_on=date.today(),
                    )
                )
            await session.commit()

        status = "створено" if created_profile else "вже існував"
        print(f"Демо-профіль {status}: Telegram ID {DEMO_TELEGRAM_ID}; стартовий баланс: 5 кредитів.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_profile())
