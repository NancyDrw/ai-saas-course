"""Compare approximate token counts for legacy and optimized analysis prompts."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .prompts import (
    build_legacy_transaction_analysis_prompt,
    build_transaction_analysis_prompt,
    estimate_tokens,
)


@dataclass
class SampleTransaction:
    transaction_type: str
    amount: Decimal
    category: str
    occurred_on: date


def build_sample_transactions(count: int) -> list[SampleTransaction]:
    categories = ("AI-сесія", "Premium-звіт", "Вправа")
    start = date(2026, 9, 1)
    transactions = [
        SampleTransaction("income", Decimal("40"), "Бонус", start),
    ]
    for index in range(count - 1):
        transactions.append(
            SampleTransaction(
                "expense",
                Decimal(index % 3 + 1),
                categories[index % len(categories)],
                start + timedelta(days=index),
            )
        )
    return transactions


def print_comparison(name: str, transactions: list[SampleTransaction]) -> None:
    legacy = estimate_tokens(build_legacy_transaction_analysis_prompt(transactions))
    optimized = estimate_tokens(build_transaction_analysis_prompt(transactions))
    saved = legacy - optimized
    percent = (saved / legacy * 100) if legacy else 0
    print(
        f"{name}: legacy={legacy}, optimized={optimized}, "
        f"saved={saved} ({percent:.1f}%)"
    )


if __name__ == "__main__":
    print_comparison("Звичайний сценарій (3 операції)", build_sample_transactions(3))
    print_comparison("Великий сценарій (30 операцій)", build_sample_transactions(30))
