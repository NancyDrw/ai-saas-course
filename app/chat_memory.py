"""LangGraph short-term memory for AI INSIGHT conversations."""

from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class ChatMessage(TypedDict):
    """A serializable message stored in one chat thread checkpoint."""

    role: str
    content: str


class ChatState(TypedDict):
    """The short-term state for one AI INSIGHT thread."""

    messages: Annotated[list[ChatMessage], operator.add]
    answer: str


AnswerBuilder = Callable[[list[ChatMessage]], Awaitable[str]]


def create_chat_graph(answer_builder: AnswerBuilder):
    """Create a graph whose checkpointer keeps one thread's message context."""

    async def answer_user(state: ChatState) -> dict[str, object]:
        answer = await answer_builder(state["messages"])
        return {
            "messages": [{"role": "assistant", "content": answer}],
            "answer": answer,
        }

    builder = StateGraph(ChatState)
    builder.add_node("answer_user", answer_user)
    builder.add_edge(START, "answer_user")
    builder.add_edge("answer_user", END)
    return builder.compile(checkpointer=InMemorySaver())
