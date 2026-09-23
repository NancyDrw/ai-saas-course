"""Prompt construction and token estimates for the Intima AI credit analysis."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Protocol, Sequence

import tiktoken


class LedgerEntry(Protocol):
    """The minimal transaction fields needed to build an analysis prompt."""

    transaction_type: str
    amount: Decimal
    category: str
    occurred_on: object


def format_credits(value: Decimal) -> str:
    return f"{value:.2f}"


def build_legacy_transaction_analysis_prompt(transactions: Sequence[LedgerEntry]) -> str:
    """The lesson 9 prompt, retained only to compare token estimates."""
    ledger_rows = "\n".join(
        (
            f"- date={transaction.occurred_on.isoformat()}, "
            f"type={transaction.transaction_type}, "
            f"amount={transaction.amount}, category={transaction.category}"
        )
        for transaction in transactions
    ) or "(Операцій немає.)"

    return f"""
Ти — AI-аналітик навчального сервісу Intima. Аналізуєш лише внутрішні кредити
Intima, а не реальні банківські гроші. Відповідай українською мовою.

Завдання: коротко проаналізуй ledger нарахувань і списань, назви основні
категорії списань, можливі ризики й практичні поради для адміністратора.

Критичні обмеження:
- Використовуй ТІЛЬКИ операції нижче.
- Не вигадуй категорії, суми, дати, факти або причини операцій.
- У top_expense_categories вказуй тільки категорії типу expense та їхню точну
  суму зі вхідних даних.
- Якщо даних недостатньо, прямо скажи про це у summary та поверни порожні
  списки там, де висновок неможливий.
- Не надавай медичних, юридичних чи інвестиційних порад.

Операції ledger:
{ledger_rows}
""".strip()


def build_transaction_analysis_prompt(transactions: Sequence[LedgerEntry]) -> str:
    """Build a compact, fact-only prompt from aggregated Intima credit data."""
    total_income = Decimal("0")
    total_expense = Decimal("0")
    expense_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for transaction in transactions:
        if transaction.transaction_type == "income":
            total_income += transaction.amount
        elif transaction.transaction_type == "expense":
            total_expense += transaction.amount
            expense_totals[transaction.category] += transaction.amount

    expense_rows = "\n".join(
        f"- {category}: {format_credits(amount)} кредитів"
        for category, amount in sorted(
            expense_totals.items(), key=lambda item: item[1], reverse=True
        )
    ) or "- списань немає"

    return f"""
Роль: AI-аналітик внутрішніх кредитів Intima. Відповідай українською.
Задача: дай короткий аналіз лише за фактами нижче.
Правила: не вигадуй суми, категорії, дати чи факти; не давай медичних,
юридичних або інвестиційних порад. Якщо даних мало — скажи це у summary.
Для top_expense_categories використовуй тільки категорії та точні суми зі
списку «Списання за категоріями». Поверни JSON з полями summary,
top_expense_categories, risks, advice.

Факти ledger:
- Операцій: {len(transactions)}
- Нараховано: {format_credits(total_income)} кредитів
- Списано: {format_credits(total_expense)} кредитів
- Баланс: {format_credits(total_income - total_expense)} кредитів
Списання за категоріями:
{expense_rows}
""".strip()


def estimate_tokens(text: str) -> int:
    """Return a cl100k_base estimate; Gemini uses a different tokenizer."""
    return len(tiktoken.get_encoding("cl100k_base").encode(text))
