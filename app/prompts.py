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
    recent_expenses = sorted(
        (transaction for transaction in transactions if transaction.transaction_type == "expense"),
        key=lambda transaction: transaction.occurred_on,
        reverse=True,
    )[:3]
    recent_expense_rows = "\n".join(
        (
            f"- {transaction.occurred_on.isoformat()}: {transaction.category} — "
            f"{format_credits(transaction.amount)} кредитів"
        )
        for transaction in recent_expenses
    ) or "- списань немає"

    return f"""
Роль: AI-аналітик внутрішніх кредитів Intima. Відповідай українською.
Задача: дай короткий фактичний огляд операцій, балансу, останніх списань і
найбільших категорій витрат лише за фактами нижче.
Правила: не вигадуй суми, категорії, дати чи факти; не давай медичних,
юридичних або інвестиційних порад. У summary назви кількість операцій, баланс
і, якщо вони є, останні списання. Не пиши, що обсяг даних обмежений або що
даних недостатньо. Якщо операцій або списань немає, просто вкажи цей факт.
Для top_expense_categories використовуй тільки категорії та точні суми зі
списку «Списання за категоріями». Поверни JSON з полями summary,
top_expense_categories, risks, advice. Поверни порожній список risks або advice,
якщо для нього немає фактичної підстави; не пояснюй це браком даних.

Факти ledger:
- Операцій: {len(transactions)}
- Нараховано: {format_credits(total_income)} кредитів
- Списано: {format_credits(total_expense)} кредитів
- Баланс: {format_credits(total_income - total_expense)} кредитів
Списання за категоріями:
{expense_rows}
Останні списання:
{recent_expense_rows}
""".strip()


def estimate_tokens(text: str) -> int:
    """Return a cl100k_base estimate; Gemini uses a different tokenizer."""
    return len(tiktoken.get_encoding("cl100k_base").encode(text))
