"""Read-only API for the Intima admin dashboard."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import (
    Base,
    Category,
    Couple,
    User,
    UserTransaction,
    create_database_engine,
)


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

database_url = os.getenv("DATABASE_URL")
if not database_url or database_url == "your_database_url_here":
    raise RuntimeError("DATABASE_URL is not set. Add it to the local .env file.")

engine = create_database_engine(database_url)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class TransactionResponse(BaseModel):
    id: int
    date: datetime
    type: str
    category: str
    description: str | None
    couple_id: int | None


class SummaryResponse(BaseModel):
    total_users: int
    total_couples: int
    total_activities: int


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Intima Admin API",
    description="Read-only API for dashboard activity metrics.",
    version="0.1.0",
    lifespan=lifespan,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@app.get("/api/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    session: AsyncSession = Depends(get_session),
) -> list[TransactionResponse]:
    """Return safe activity metadata for the admin dashboard."""
    result = await session.execute(
        select(UserTransaction, Category.title)
        .join(Category, UserTransaction.category_id == Category.id)
        .order_by(UserTransaction.created_at.desc())
    )

    return [
        TransactionResponse(
            id=transaction.id,
            date=transaction.created_at,
            type=transaction.action_type,
            category=category_title,
            description=transaction.content_summary,
            couple_id=transaction.couple_id,
        )
        for transaction, category_title in result.all()
    ]


@app.get("/api/summary", response_model=SummaryResponse)
async def get_summary(
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Return dashboard counts: users, created couples and activity events."""
    total_users = await session.scalar(select(func.count()).select_from(User))
    total_couples = await session.scalar(select(func.count()).select_from(Couple))
    total_activities = await session.scalar(
        select(func.count()).select_from(UserTransaction)
    )

    return SummaryResponse(
        total_users=total_users or 0,
        total_couples=total_couples or 0,
        total_activities=total_activities or 0,
    )
