"""API for the Intima credits admin dashboard."""

import os
import secrets
import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from google import genai
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .chat_memory import ChatMessage, create_chat_graph
from .chat_tools import GEMINI_INSIGHT_TOOLS, execute_insight_tool
from .database import Base, CreditTransaction, create_database_engine
from .prompts import build_transaction_analysis_prompt


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_RATE_LIMIT_MESSAGE = "Ліміт запитів Gemini тимчасово вичерпано. Спробуйте ще раз трохи пізніше."

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


class AdminAccessResponse(BaseModel):
    authorized: bool


class ExpenseCategoryAnalysis(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0)


class TransactionAiAnalysis(BaseModel):
    summary: str = Field(min_length=1, max_length=600)
    top_expense_categories: list[ExpenseCategoryAnalysis] = Field(max_length=5)
    risks: list[str] = Field(max_length=5)
    advice: list[str] = Field(max_length=5)


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    thread_id: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{32}$",
        description="A backend-created identifier for one short-term chat thread.",
    )

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Message must not be empty.")
        return message


class AiChatResponse(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)
    thread_id: str = Field(pattern=r"^[a-f0-9]{32}$")


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


async def require_admin(
    password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> None:
    """Provide minimal local protection for the learning admin dashboard."""
    expected_password = os.getenv("ADMIN_PASSWORD")
    if not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PASSWORD is not configured on the server.",
        )
    if password is None or not secrets.compare_digest(password, expected_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password.",
        )


@app.post("/api/admin/access", response_model=AdminAccessResponse)
async def verify_admin_access(_: None = Depends(require_admin)) -> AdminAccessResponse:
    """Validate the password before loading the admin dashboard."""
    return AdminAccessResponse(authorized=True)


def serialize_transaction(transaction: CreditTransaction) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        date=transaction.occurred_on,
        type=transaction.transaction_type,
        amount=transaction.amount,
        category=transaction.category,
        description=transaction.description,
    )


def is_gemini_rate_limit_error(error: Exception) -> bool:
    """Recognize the SDK's rate-limit response without returning internals."""
    return type(error).__name__ == "RateLimitError" or getattr(error, "status_code", None) == 429


def validate_analysis(
    analysis: TransactionAiAnalysis,
    transactions: list[CreditTransaction],
) -> TransactionAiAnalysis:
    """Reject categories or sums that do not exactly match the credit ledger."""
    expense_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for transaction in transactions:
        if transaction.transaction_type == "expense":
            expense_totals[transaction.category] += transaction.amount

    for category in analysis.top_expense_categories:
        if category.category not in expense_totals:
            raise ValueError("The AI returned an unknown expense category.")
        if category.amount != expense_totals[category.category]:
            raise ValueError("The AI returned an incorrect expense amount.")

    return analysis


def generate_transaction_analysis(
    api_key: str,
    transactions: list[CreditTransaction],
) -> TransactionAiAnalysis:
    """Call Gemini synchronously; the API route runs this function in a thread."""
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=build_transaction_analysis_prompt(transactions),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TransactionAiAnalysis.model_json_schema(),
        },
    )
    if not interaction.output_text:
        raise ValueError("Gemini returned an empty response.")
    return TransactionAiAnalysis.model_validate_json(interaction.output_text)


def build_insight_chat_input(messages: list[ChatMessage]) -> str:
    """Create a bounded, tool-first prompt for AI INSIGHT."""
    conversation = "\n".join(
        f"{'Користувач' if message['role'] == 'user' else 'Помічник'}: {message['content']}"
        for message in messages[-12:]
    )
    return f"""
Ти — AI INSIGHT, помічник з аналізу внутрішніх кредитів Intima, а не реальних
банківських грошей. Відповідай українською, доброзичливо й стисло.

Для будь-якого питання про операції, баланс, списання, категорії або період
обов'язково викликай один чи кілька read-only tools. Якщо період не названо,
використовуй all. Після tool-виклику використовуй лише перевірені факти з його
результату: не вигадуй суми, категорії, дати чи операції.

Ти можеш тільки аналізувати. Не додавай і не видаляй операції, не змінюй суми
чи категорії, не виконуй SQL і не запитуй доступ до .env.

Історія поточного діалогу:
{conversation}
""".strip()


def create_insight_chat_interaction(api_key: str, messages: list[ChatMessage]):
    """Start one Gemini interaction that can select only financial read tools."""
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=build_insight_chat_input(messages),
        tools=GEMINI_INSIGHT_TOOLS,
        store=False,
    )
    return client, interaction


def write_insight_answer_from_tool_results(
    client, messages: list[ChatMessage], tool_outputs: list[dict[str, object]]
):
    """Ask Gemini for a final answer using only trusted backend tool output."""
    facts = json.dumps(tool_outputs, ensure_ascii=False)
    return client.interactions.create(
        model=GEMINI_MODEL,
        input=(
            f"{build_insight_chat_input(messages)}\n\n"
            "Перевірені результати backend tools:\n"
            f"{facts}\n\n"
            "Сформуй коротку відповідь лише на основі цих фактів."
        ),
        store=False,
    )


async def generate_insight_chat_answer(messages: list[ChatMessage]) -> str:
    """Run Gemini -> allow-listed tool -> Gemini, with no write access."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client, interaction = await asyncio.to_thread(
        create_insight_chat_interaction, api_key, messages
    )
    tool_calls = [
        step for step in (interaction.steps or []) if getattr(step, "type", None) == "function_call"
    ]
    if not tool_calls:
        if not interaction.output_text:
            raise ValueError("Gemini returned an empty chat response.")
        return interaction.output_text.strip()

    tool_outputs: list[dict[str, object]] = []
    for tool_call in tool_calls:
        arguments = getattr(tool_call, "arguments", None)
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            result = await execute_insight_tool(session_factory, tool_call.name, arguments)
        except (TypeError, ValueError):
            result = {"error": "Не вдалося безпечно прочитати дані кредитів."}
        tool_outputs.append({"tool": tool_call.name, "result": result})

    final_interaction = await asyncio.to_thread(
        write_insight_answer_from_tool_results,
        client,
        messages,
        tool_outputs,
    )
    if not final_interaction.output_text:
        raise ValueError("Gemini returned an empty chat response after tool results.")
    return final_interaction.output_text.strip()


insight_chat_graph = create_chat_graph(generate_insight_chat_answer)


@app.get("/api/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
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
    _: None = Depends(require_admin),
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
    _: None = Depends(require_admin),
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
    _: None = Depends(require_admin),
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


@app.post(
    "/api/ai/analyze-transactions",
    response_model=TransactionAiAnalysis,
)
async def analyze_transactions(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> TransactionAiAnalysis:
    """Analyze Intima credit operations with Gemini on the backend only."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    result = await session.execute(
        select(CreditTransaction).order_by(
            CreditTransaction.occurred_on.desc(), CreditTransaction.id.desc()
        )
    )
    transactions = list(result.scalars())

    try:
        analysis = await asyncio.to_thread(
            generate_transaction_analysis,
            api_key,
            transactions,
        )
        return validate_analysis(analysis, transactions)
    except ValueError:
        logger.warning("Gemini returned an invalid transaction analysis.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an invalid analysis. Please try again.",
        ) from None
    except Exception as error:
        if is_gemini_rate_limit_error(error):
            logger.warning("Gemini transaction analysis rate limit reached.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=GEMINI_RATE_LIMIT_MESSAGE,
            ) from None
        logger.error("Gemini transaction analysis failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis is temporarily unavailable. Please try again.",
        ) from None


@app.post("/api/ai/chat", response_model=AiChatResponse)
async def chat_with_ai_insight(
    payload: AiChatRequest,
    _: None = Depends(require_admin),
) -> AiChatResponse:
    """Continue one short-term, tool-assisted AI INSIGHT conversation."""
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    thread_id = payload.thread_id or uuid4().hex
    try:
        result = await insight_chat_graph.ainvoke(
            {"messages": [{"role": "user", "content": payload.message}], "answer": ""},
            config={"configurable": {"thread_id": thread_id}},
        )
        return AiChatResponse(answer=result["answer"], thread_id=thread_id)
    except ValueError:
        logger.warning("AI INSIGHT chat returned an invalid response.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI INSIGHT returned an invalid response. Please try again.",
        ) from None
    except Exception as error:
        if is_gemini_rate_limit_error(error):
            logger.warning("AI INSIGHT chat rate limit reached.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=GEMINI_RATE_LIMIT_MESSAGE,
            ) from None
        logger.error("AI INSIGHT chat failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI INSIGHT is temporarily unavailable. Please try again.",
        ) from None
