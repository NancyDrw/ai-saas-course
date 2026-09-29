"""Validation checks for confirmation-gated Intima AI actions."""

import unittest

from pydantic import ValidationError

from app.ai_actions import CONTROLLED_ACTION_TOOLS, CreditTransactionActionPayload


class ControlledActionTests(unittest.TestCase):
    def test_accepts_a_valid_intima_credit_draft(self) -> None:
        payload = CreditTransactionActionPayload.model_validate(
            {
                "type": "expense",
                "amount": "3",
                "category": "AI-сесія",
                "description": "Списано кредити за AI-сесію.",
                "date": "2026-09-29",
            }
        )

        self.assertEqual(payload.category, "AI-сесія")
        self.assertEqual(payload.amount, 3)

    def test_rejects_invalid_or_extra_action_data(self) -> None:
        with self.assertRaises(ValidationError):
            CreditTransactionActionPayload.model_validate(
                {
                    "type": "expense",
                    "amount": 0,
                    "category": " ",
                    "date": "not-a-date",
                    "unexpected": "field",
                }
            )

    def test_declares_only_a_confirmation_gated_action_tool(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in CONTROLLED_ACTION_TOOLS],
            ["prepare_credit_transaction"],
        )


if __name__ == "__main__":
    unittest.main()
