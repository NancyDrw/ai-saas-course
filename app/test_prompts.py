"""Focused checks for optimized transaction-analysis prompts."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.prompts import build_transaction_analysis_prompt, estimate_tokens


def transaction(transaction_type: str, amount: str, category: str) -> SimpleNamespace:
    return SimpleNamespace(
        transaction_type=transaction_type,
        amount=Decimal(amount),
        category=category,
        occurred_on=date(2026, 9, 15),
    )


class TransactionAnalysisPromptTests(unittest.TestCase):
    def test_uses_aggregated_facts_for_a_regular_ledger(self) -> None:
        prompt = build_transaction_analysis_prompt(
            [
                transaction("income", "10", "Бонус"),
                transaction("expense", "2", "AI-сесія"),
                transaction("expense", "1", "AI-сесія"),
            ]
        )

        self.assertIn("Операцій: 3", prompt)
        self.assertIn("Нараховано: 10.00", prompt)
        self.assertIn("AI-сесія: 3.00", prompt)
        self.assertIn("Баланс: 7.00", prompt)
        self.assertIn("Останні списання:", prompt)
        self.assertIn("2026-09-15: AI-сесія — 2.00", prompt)

    def test_handles_an_empty_ledger_without_inventing_facts(self) -> None:
        prompt = build_transaction_analysis_prompt([])

        self.assertIn("Операцій: 0", prompt)
        self.assertIn("списань немає", prompt)
        self.assertIn("не вигадуй суми, категорії, дати чи факти", prompt)
        self.assertIn("Не пиши, що обсяг даних обмежений", prompt)
        self.assertGreater(estimate_tokens(prompt), 0)


if __name__ == "__main__":
    unittest.main()
