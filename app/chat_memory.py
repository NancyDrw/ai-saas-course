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
    pending_action: dict[str, object] | None
    thread_id: str


class ChatGeneration(TypedDict):
    """The text answer and optional pending action created during one turn."""

    answer: str
    pending_action: dict[str, object] | None


AnswerBuilder = Callable[[list[ChatMessage], str], Awaitable[ChatGeneration]]


def create_chat_graph(answer_builder: AnswerBuilder):
    """Create a graph whose checkpointer keeps one thread's message context."""

    async def answer_user(state: ChatState) -> dict[str, object]:
        generation = await answer_builder(state["messages"], state["thread_id"])
        return {
            "messages": [{"role": "assistant", "content": generation["answer"]}],
            "answer": generation["answer"],
            "pending_action": generation["pending_action"],
        }

    builder = StateGraph(ChatState)
    builder.add_node("answer_user", answer_user)
    builder.add_edge(START, "answer_user")
    builder.add_edge("answer_user", END)
    return builder.compile(checkpointer=InMemorySaver())
