"""API for the Intima credits admin dashboard."""

import os
import secrets
import asyncio
import base64
import hashlib
import hmac
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .ai_actions import (
    CANCELLED,
    CONFIRMED,
    CONTROLLED_ACTION_TOOLS,
    CREATE_CREDIT_TRANSACTION,
    PENDING,
    CreditTransactionActionPayload,
    cancel_pending_action,
    confirm_credit_transaction,
    prepare_credit_transaction,
    serialize_pending_action,
)
from .chat_memory import ChatMessage, create_chat_graph
from .chat_tools import GEMINI_INSIGHT_TOOLS, execute_insight_tool
from .database import (
    Base,
    Couple,
    CreditTransaction,
    PendingAiAction,
    User,
    apply_identity_schema_migration,
    create_database_engine,
)
from .telegram_auth import TelegramAuthError, TelegramIdentity, validate_webapp_init_data


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_RATE_LIMIT_MESSAGE = "Ліміт запитів Gemini тимчасово вичерпано. Спробуйте ще раз трохи пізніше."
SESSION_COOKIE_NAME = "intima_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7

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
    telegram_id: int | None = Field(default=None, gt=0)
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


class TelegramWebAppAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=10_000)


class CurrentUserResponse(BaseModel):
    telegram_id: int
    first_name: str | None
    username: str | None


class TelegramIdentityResponse(CurrentUserResponse):
    couples: list[dict[str, object]]


class PendingActionRequest(BaseModel):
    telegram_id: int | None = Field(default=None, gt=0)


class AiChatRequest(BaseModel):
    telegram_id: int | None = Field(default=None, gt=0)
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
    pending_action: "PendingActionResponse | None" = None


class PendingActionResponse(BaseModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    thread_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    action_type: Literal["create_credit_transaction"]
    payload: CreditTransactionActionPayload
    status: Literal["pending", "confirmed", "cancelled", "failed"]
    created_at: datetime | None


class ActionConfirmationResponse(BaseModel):
    action: PendingActionResponse
    transaction: TransactionResponse | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await apply_identity_schema_migration(connection)
    yield
    await engine.dispose()


app = FastAPI(
    title="Intima Admin API",
    description="Admin API for the Intima credits ledger.",
    version="0.2.0",
    lifespan=lifespan,
)

public_web_origin = os.getenv("PUBLIC_WEB_ORIGIN", "").rstrip("/")
if public_web_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[public_web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-Admin-Password"],
    )


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Small unauthenticated readiness endpoint for Render health checks."""
    return {"status": "ok"}


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User:
    """Resolve a bot-registered identity selected by an authenticated admin."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram-користувача не знайдено. Він або вона має спершу надіслати /start боту Intima.",
        )
    return user


def session_signing_key() -> bytes:
    """Derive a distinct cookie-signing key without exposing BOT_TOKEN."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured.")
    return hmac.new(bot_token.encode(), b"intima-web-session", hashlib.sha256).digest()


def encode_session(user_id: int, issued_at: int) -> str:
    payload = json.dumps(
        {"user_id": user_id, "expires_at": issued_at + SESSION_TTL_SECONDS},
        separators=(",", ":"),
    ).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(session_signing_key(), encoded_payload, hashlib.sha256).hexdigest()
    return f"{encoded_payload.decode()}.{signature}"


def decode_session(token: str | None) -> int:
    """Return one authenticated user ID or reject altered/expired cookies."""
    if not token or "." not in token:
        raise ValueError("Missing session.")
    encoded_payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        session_signing_key(), encoded_payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid session signature.")
    try:
        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload))
        user_id = int(payload["user_id"])
        expires_at = int(payload["expires_at"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid session payload.") from error
    if user_id <= 0 or expires_at < int(datetime.now().timestamp()):
        raise ValueError("Expired session.")
    return user_id


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    signed_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User:
    try:
        user_id = decode_session(signed_session)
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram login is required.") from None
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram session is no longer valid.")
    return user


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


async def upsert_telegram_user(session: AsyncSession, identity: TelegramIdentity) -> User:
    """Store only Telegram profile fields already verified by Telegram's signature."""
    user = await session.scalar(select(User).where(User.telegram_id == identity.telegram_id))
    if user is None:
        user = User(
            telegram_id=identity.telegram_id,
            username=identity.username,
            first_name=identity.first_name,
        )
        session.add(user)
    else:
        user.username = identity.username
        user.first_name = identity.first_name
    await session.commit()
    await session.refresh(user)
    return user


@app.post("/api/auth/telegram", response_model=CurrentUserResponse)
async def authenticate_telegram_webapp(
    payload: TelegramWebAppAuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> CurrentUserResponse:
    """Verify Telegram Mini App data and establish a signed HttpOnly session."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram login is temporarily unavailable.",
        )
    try:
        identity = validate_webapp_init_data(payload.init_data, bot_token)
    except TelegramAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram login data could not be verified. Reopen Intima from the bot.",
        ) from None

    user = await upsert_telegram_user(session, identity)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=encode_session(user.id, int(datetime.now().timestamp())),
        httponly=True,
        secure=os.getenv("APP_ENV") == "production",
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return CurrentUserResponse(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        username=user.username,
    )


@app.get("/api/me", response_model=CurrentUserResponse)
async def get_me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Return only the identity associated with the verified browser session."""
    return CurrentUserResponse(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        username=user.username,
    )


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_telegram_webapp(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


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

Якщо користувач прямо просить додати нарахування або списання кредитів Intima,
виклич prepare_credit_transaction лише коли відомі type, amount, category і
date. Сьогоднішня дата: {date.today().isoformat()}. Це створює лише pending
action, а не операцію в ledger. Якщо будь-якого поля бракує — постав одне
коротке уточнювальне питання й не викликай tool.

Ніколи не виконуй дію самостійно: не додавай і не видаляй операції, не змінюй
суми чи категорії, не виконуй SQL і не запитуй доступ до .env. Після створення
pending action повідом користувача, що він або вона має перевірити картку й
явно підтвердити або скасувати дію.

Історія поточного діалогу:
{conversation}
""".strip()


def create_insight_chat_interaction(api_key: str, messages: list[ChatMessage]):
    """Start one Gemini interaction that can select only financial read tools."""
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=build_insight_chat_input(messages),
        tools=GEMINI_INSIGHT_TOOLS + CONTROLLED_ACTION_TOOLS,
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


async def generate_insight_chat_answer(
    messages: list[ChatMessage], thread_id: str, user_id: int | None
) -> dict[str, object]:
    """Run Gemini tools; only a pending action may be written before confirm."""
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
        return {"answer": interaction.output_text.strip(), "pending_action": None}

    tool_outputs: list[dict[str, object]] = []
    pending_action: dict[str, object] | None = None
    for tool_call in tool_calls:
        arguments = getattr(tool_call, "arguments", None)
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            if tool_call.name == "prepare_credit_transaction":
                result = await prepare_credit_transaction(session_factory, thread_id, user_id, arguments)
                action = result.get("pending_action")
                if isinstance(action, dict):
                    pending_action = action
            else:
                result = await execute_insight_tool(session_factory, user_id, tool_call.name, arguments)
        except (TypeError, ValueError):
            result = {"error": "Не вдалося безпечно підготувати або прочитати дані кредитів."}
        tool_outputs.append({"tool": tool_call.name, "result": result})

    final_interaction = await asyncio.to_thread(
        write_insight_answer_from_tool_results,
        client,
        messages,
        tool_outputs,
    )
    if not final_interaction.output_text:
        raise ValueError("Gemini returned an empty chat response after tool results.")
    return {"answer": final_interaction.output_text.strip(), "pending_action": pending_action}


insight_chat_graph = create_chat_graph(generate_insight_chat_answer)


@app.get("/api/identities/telegram/{telegram_id}", response_model=TelegramIdentityResponse)
async def get_telegram_identity(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> TelegramIdentityResponse:
    """Show a profile only after an admin has explicitly selected its Telegram ID."""
    user = await get_user_by_telegram_id(session, telegram_id)
    couples = await session.execute(
        select(Couple).where(Couple.created_by_user_id == user.id).order_by(Couple.created_at.desc())
    )
    return TelegramIdentityResponse(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        username=user.username,
        couples=[{"id": couple.id, "title": couple.title} for couple in couples.scalars()],
    )


@app.get("/api/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    telegram_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> list[TransactionResponse]:
    """Return Intima credit ledger entries, newest first."""
    statement = select(CreditTransaction)
    if telegram_id is not None:
        user = await get_user_by_telegram_id(session, telegram_id)
        statement = statement.where(CreditTransaction.user_id == user.id)
    result = await session.execute(
        statement.order_by(
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
    user = await get_user_by_telegram_id(session, payload.telegram_id) if payload.telegram_id else None
    transaction = CreditTransaction(
        user_id=user.id if user else None,
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
    telegram_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> None:
    """Remove one credit ledger entry."""
    transaction = await session.get(CreditTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if telegram_id is not None:
        user = await get_user_by_telegram_id(session, telegram_id)
        if transaction.user_id != user.id:
            raise HTTPException(status_code=404, detail="Transaction not found.")

    await session.delete(transaction)
    await session.commit()


@app.get("/api/summary", response_model=SummaryResponse)
async def get_summary(
    telegram_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> SummaryResponse:
    """Return credit income, expenses, and the current balance."""
    statement = select(CreditTransaction.transaction_type, CreditTransaction.amount)
    if telegram_id is not None:
        user = await get_user_by_telegram_id(session, telegram_id)
        statement = statement.where(CreditTransaction.user_id == user.id)
    result = await session.execute(statement)
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


@app.post("/api/ai/chat", response_model=AiChatResponse)
async def chat_with_ai_insight(
    payload: AiChatRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> AiChatResponse:
    """Continue one short-term, tool-assisted AI INSIGHT conversation."""
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    selected_user = await get_user_by_telegram_id(session, payload.telegram_id) if payload.telegram_id else None
    user_id = selected_user.id if selected_user else None
    thread_id = payload.thread_id or uuid4().hex
    try:
        result = await insight_chat_graph.ainvoke(
            {
                "messages": [{"role": "user", "content": payload.message}],
                "answer": "",
                "pending_action": None,
                "thread_id": thread_id,
                "user_id": user_id,
            },
            config={"configurable": {"thread_id": f"user-{user_id or 'all'}-{thread_id}"}},
        )
        return AiChatResponse(
            answer=result["answer"],
            thread_id=thread_id,
            pending_action=result.get("pending_action"),
        )
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


async def get_pending_action_or_404(
    session: AsyncSession, action_id: str, user_id: int | None
) -> PendingAiAction:
    action = await session.get(PendingAiAction, action_id)
    if action is None or action.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending action not found.")
    return action


def pending_action_response(action: PendingAiAction) -> PendingActionResponse:
    return PendingActionResponse.model_validate(serialize_pending_action(action))


@app.post(
    "/api/ai/actions/{action_id}/confirm",
    response_model=ActionConfirmationResponse,
)
async def confirm_ai_action(
    action_id: str,
    payload: PendingActionRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> ActionConfirmationResponse:
    """Execute one validated pending action after explicit admin confirmation."""
    user = await get_user_by_telegram_id(session, payload.telegram_id) if payload.telegram_id else None
    action = await get_pending_action_or_404(session, action_id, user.id if user else None)
    if action.status != PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending actions can be confirmed.",
        )
    if action.action_type != CREATE_CREDIT_TRANSACTION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Action is not allowed.")

    try:
        transaction = await confirm_credit_transaction(session, action)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Pending action payload is invalid and was marked as failed.",
        ) from None
    await session.refresh(action)
    return ActionConfirmationResponse(
        action=pending_action_response(action),
        transaction=serialize_transaction(transaction),
    )


@app.post(
    "/api/ai/actions/{action_id}/cancel",
    response_model=PendingActionResponse,
)
async def cancel_ai_action(
    action_id: str,
    payload: PendingActionRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> PendingActionResponse:
    """Cancel a pending action without changing the Intima credits ledger."""
    user = await get_user_by_telegram_id(session, payload.telegram_id) if payload.telegram_id else None
    action = await get_pending_action_or_404(session, action_id, user.id if user else None)
    if action.status != PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending actions can be cancelled.",
        )
    await cancel_pending_action(session, action)
    await session.refresh(action)
    return pending_action_response(action)
