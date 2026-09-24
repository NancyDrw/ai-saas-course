"""Controlled read-only Neon tools available to AI INSIGHT."""

from __future__ import annotations

import re
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import CreditTransaction


PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

GEMINI_INSIGHT_TOOLS = [
    {
        "type": "function",
        "name": "get_transactions_summary",
        "description": "Read-only Intima credits summary: additions, spending and balance for a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "A calendar month in YYYY-MM or all for the whole ledger.",
                }
            },
            "required": ["period"],
        },
    },
    {
        "type": "function",
        "name": "get_category_totals",
        "description": "Read-only total Intima credit spending by category for a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "A calendar month in YYYY-MM or all for the whole ledger.",
                }
            },
            "required": ["period"],
        },
    },
    {
        "type": "function",
        "name": "get_top_expenses",
        "description": "Read-only largest individual Intima credit expenses for a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "A calendar month in YYYY-MM or all for the whole ledger.",
                },
                "limit": {
                    "type": "integer",
                    "description": "How many expenses to return, from 1 to 5.",
                },
            },
            "required": ["period", "limit"],
        },
    },
]


def normalize_period(period: object) -> str:
    """Validate period input before it can reach a database query."""
    normalized = str(period or "all").strip().lower()
    if normalized == "all" or PERIOD_PATTERN.fullmatch(normalized):
        return normalized
    raise ValueError("Period must be all or YYYY-MM.")


def period_bounds(period: str) -> tuple[date, date] | None:
    """Return inclusive month dates for a validated period."""
    if period == "all":
        return None
    year, month = (int(part) for part in period.split("-"))
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def format_credits(amount: Decimal) -> str:
    return f"{amount:.2f}"


async def fetch_transactions(
    session_factory: async_sessionmaker[AsyncSession], period: str
) -> list[CreditTransaction]:
    """Use a fixed SQLAlchemy select; AI never receives raw SQL access."""
    statement = select(CreditTransaction)
    bounds = period_bounds(period)
    if bounds:
        statement = statement.where(CreditTransaction.occurred_on.between(*bounds))
    statement = statement.order_by(CreditTransaction.occurred_on.desc(), CreditTransaction.id.desc())

    async with session_factory() as session:
        result = await session.execute(statement)
        return list(result.scalars())


async def get_transactions_summary(
    session_factory: async_sessionmaker[AsyncSession], period: object
) -> dict[str, object]:
    """Return aggregate, read-only ledger facts."""
    normalized_period = normalize_period(period)
    transactions = await fetch_transactions(session_factory, normalized_period)
    income = sum(
        (transaction.amount for transaction in transactions if transaction.transaction_type == "income"),
        Decimal("0"),
    )
    expense = sum(
        (transaction.amount for transaction in transactions if transaction.transaction_type == "expense"),
        Decimal("0"),
    )
    return {
        "period": normalized_period,
        "operations": len(transactions),
        "credits_added": format_credits(income),
        "credits_spent": format_credits(expense),
        "balance": format_credits(income - expense),
    }


async def get_category_totals(
    session_factory: async_sessionmaker[AsyncSession], period: object
) -> dict[str, object]:
    """Return read-only expense category totals."""
    normalized_period = normalize_period(period)
    totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for transaction in await fetch_transactions(session_factory, normalized_period):
        if transaction.transaction_type == "expense":
            totals[transaction.category] += transaction.amount
    return {
        "period": normalized_period,
        "categories": [
            {"category": category, "credits_spent": format_credits(amount)}
            for category, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ],
    }


async def get_top_expenses(
    session_factory: async_sessionmaker[AsyncSession], period: object, limit: object
) -> dict[str, object]:
    """Return a maximum of five expense rows, without writing anything."""
    normalized_period = normalize_period(period)
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError) as error:
        raise ValueError("Limit must be an integer.") from error
    if not 1 <= normalized_limit <= 5:
        raise ValueError("Limit must be between 1 and 5.")

    expenses = [
        transaction
        for transaction in await fetch_transactions(session_factory, normalized_period)
        if transaction.transaction_type == "expense"
    ]
    expenses.sort(key=lambda transaction: transaction.amount, reverse=True)
    return {
        "period": normalized_period,
        "expenses": [
            {
                "date": transaction.occurred_on.isoformat(),
                "category": transaction.category,
                "credits_spent": format_credits(transaction.amount),
            }
            for transaction in expenses[:normalized_limit]
        ],
    }


async def execute_insight_tool(
    session_factory: async_sessionmaker[AsyncSession], name: str, arguments: dict[str, object]
) -> dict[str, object]:
    """Dispatch only allow-listed, read-only functions with typed inputs."""
    if name == "get_transactions_summary":
        return await get_transactions_summary(session_factory, arguments.get("period"))
    if name == "get_category_totals":
        return await get_category_totals(session_factory, arguments.get("period"))
    if name == "get_top_expenses":
        return await get_top_expenses(
            session_factory,
            arguments.get("period"),
            arguments.get("limit"),
        )
    raise ValueError("Unknown read-only tool.")
