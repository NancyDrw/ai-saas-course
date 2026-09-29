"""Focused checks for AI INSIGHT memory and tool validation."""

import asyncio
import unittest

from app.chat_memory import create_chat_graph
from app.chat_tools import GEMINI_INSIGHT_TOOLS, normalize_period, period_bounds


class ChatMemoryTests(unittest.TestCase):
    def test_thread_keeps_context_between_messages(self) -> None:
        async def answer_builder(messages, thread_id):
            return {
                "answer": f"Контекст: {messages[-1]['content']}",
                "pending_action": None,
            }

        async def scenario():
            graph = create_chat_graph(answer_builder)
            config = {"configurable": {"thread_id": "test-thread"}}
            await graph.ainvoke(
                {
                    "messages": [{"role": "user", "content": "Який баланс?"}],
                    "answer": "",
                    "pending_action": None,
                    "thread_id": "test-thread",
                },
                config=config,
            )
            return await graph.ainvoke(
                {"messages": [{"role": "user", "content": "А найбільші списання?"}]},
                config=config,
            )

        result = asyncio.run(scenario())

        self.assertIn("найбільші списання", result["answer"])
        self.assertEqual(len(result["messages"]), 4)


class InsightToolsTests(unittest.TestCase):
    def test_tools_only_allow_fixed_periods_and_expected_names(self) -> None:
        self.assertEqual(normalize_period("2026-06"), "2026-06")
        self.assertEqual(
            tuple(bound.isoformat() for bound in period_bounds("2026-02")),
            ("2026-02-01", "2026-02-28"),
        )
        self.assertRaises(ValueError, normalize_period, "June")
        self.assertEqual(
            {tool["name"] for tool in GEMINI_INSIGHT_TOOLS},
            {"get_transactions_summary", "get_category_totals", "get_top_expenses"},
        )


if __name__ == "__main__":
    unittest.main()
