"""API for the Intima credits admin dashboard."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import Base, CreditTransaction, create_database_engine


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

database_url = os.getenv("DATABASE_URL")
if not database_url or database_url == "your_database_url_here":
    raise RuntimeError("DATABASE_URL is not set. Add it to the local .env file.")

engine = create_database_engine(database_url)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class TransactionResponse(BaseModel):
    id: int
    date: date
    type: Literal["income", "expense"]
    amount: Decimal
    category: str
    description: str | None


class TransactionCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    date: date

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        category = value.strip()
        if not category:
            raise ValueError("Category must not be empty.")
        return category

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class SummaryResponse(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Intima Admin API",
    description="Admin API for the Intima credits ledger.",
    version="0.2.0",
    lifespan=lifespan,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def serialize_transaction(transaction: CreditTransaction) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        date=transaction.occurred_on,
        type=transaction.transaction_type,
        amount=transaction.amount,
        category=transaction.category,
        description=transaction.description,
    )


@app.get("/api/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    session: AsyncSession = Depends(get_session),
) -> list[TransactionResponse]:
    """Return Intima credit ledger entries, newest first."""
    result = await session.execute(
        select(CreditTransaction).order_by(
            CreditTransaction.occurred_on.desc(), CreditTransaction.id.desc()
        )
    )
    return [serialize_transaction(transaction) for transaction in result.scalars()]


@app.post(
    "/api/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: TransactionCreate,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """Create a validated credit income or expense entry."""
    transaction = CreditTransaction(
        transaction_type=payload.type,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        occurred_on=payload.date,
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return serialize_transaction(transaction)


@app.delete("/api/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove one credit ledger entry."""
    transaction = await session.get(CreditTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    await session.delete(transaction)
    await session.commit()


@app.get("/api/summary", response_model=SummaryResponse)
async def get_summary(
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Return credit income, expenses, and the current balance."""
    result = await session.execute(
        select(CreditTransaction.transaction_type, CreditTransaction.amount)
    )
    total_income = Decimal("0")
    total_expense = Decimal("0")
    for transaction_type, amount in result.all():
        if transaction_type == "income":
            total_income += amount
        else:
            total_expense += amount

    return SummaryResponse(
        total_income=total_income,
        total_expense=total_expense,
        balance=total_income - total_expense,
    )
