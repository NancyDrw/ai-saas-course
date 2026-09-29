"""Validated, confirmation-gated AI actions for the Intima credits ledger."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import AiActionAuditLog, CreditTransaction, PendingAiAction


CREATE_CREDIT_TRANSACTION = "create_credit_transaction"
PENDING = "pending"
CONFIRMED = "confirmed"
CANCELLED = "cancelled"
FAILED = "failed"

CONTROLLED_ACTION_TOOLS = [
    {
        "type": "function",
        "name": "prepare_credit_transaction",
        "description": (
            "Prepare, but never execute, an Intima credits ledger transaction. "
            "This creates a pending action that needs user confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["income", "expense"],
                    "description": "income for a credit addition or expense for a credit charge.",
                },
                "amount": {"type": "number", "description": "Positive number of Intima credits."},
                "category": {
                    "type": "string",
                    "description": "A non-empty Intima category, e.g. AI-сесія or Бонус.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional brief explanation for the ledger.",
                },
                "date": {
                    "type": "string",
                    "description": "Operation date in YYYY-MM-DD format.",
                },
            },
            "required": ["type", "amount", "category", "date"],
            "additionalProperties": False,
        },
    }
]


class CreditTransactionActionPayload(BaseModel):
    """Strict payload accepted by the pending credit action."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    date: date

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
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


def serialize_pending_action(action: PendingAiAction) -> dict[str, object]:
    """Expose only action data that a user needs to review and confirm."""
    return {
        "id": action.id,
        "thread_id": action.thread_id,
        "action_type": action.action_type,
        "payload": action.payload,
        "status": action.status,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


async def prepare_credit_transaction(
    session_factory: async_sessionmaker[AsyncSession],
    thread_id: str,
    arguments: dict[str, object],
) -> dict[str, object]:
    """Persist a validated pending action, never a ledger transaction itself."""
    payload = CreditTransactionActionPayload.model_validate(arguments)
    serialized_payload = payload.model_dump(mode="json")

    async with session_factory() as session:
        existing_actions = await session.execute(
            select(PendingAiAction)
            .where(
                PendingAiAction.thread_id == thread_id,
                PendingAiAction.action_type == CREATE_CREDIT_TRANSACTION,
                PendingAiAction.status == PENDING,
            )
            .order_by(PendingAiAction.created_at.desc())
        )
        for existing in existing_actions.scalars():
            if existing.payload == serialized_payload:
                return {"pending_action": serialize_pending_action(existing), "duplicate": True}

        action = PendingAiAction(
            id=uuid4().hex,
            thread_id=thread_id,
            action_type=CREATE_CREDIT_TRANSACTION,
            payload=serialized_payload,
            status=PENDING,
        )
        session.add(action)
        session.add(
            AiActionAuditLog(
                action_id=action.id,
                thread_id=thread_id,
                action_type=CREATE_CREDIT_TRANSACTION,
                event="created",
                result={"status": PENDING},
            )
        )
        await session.commit()
        await session.refresh(action)
        return {"pending_action": serialize_pending_action(action), "duplicate": False}


async def confirm_credit_transaction(
    session: AsyncSession, action: PendingAiAction
) -> CreditTransaction:
    """Validate a pending action again and atomically create the ledger row."""
    try:
        payload = CreditTransactionActionPayload.model_validate(action.payload)
    except Exception as error:
        action.status = FAILED
        action.error_message = "Pending action payload did not pass validation."
        session.add(
            AiActionAuditLog(
                action_id=action.id,
                thread_id=action.thread_id,
                action_type=action.action_type,
                event=FAILED,
                result={"reason": "payload_validation"},
            )
        )
        await session.commit()
        raise ValueError("Pending action payload is invalid.") from error

    transaction = CreditTransaction(
        transaction_type=payload.type,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        occurred_on=payload.date,
    )
    action.status = CONFIRMED
    action.confirmed_at = datetime.now(timezone.utc)
    session.add(transaction)
    session.add(
        AiActionAuditLog(
            action_id=action.id,
            thread_id=action.thread_id,
            action_type=action.action_type,
            event=CONFIRMED,
            result={"status": CONFIRMED},
        )
    )
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def cancel_pending_action(session: AsyncSession, action: PendingAiAction) -> None:
    """Cancel a pending action without changing the credits ledger."""
    action.status = CANCELLED
    action.cancelled_at = datetime.now(timezone.utc)
    session.add(
        AiActionAuditLog(
            action_id=action.id,
            thread_id=action.thread_id,
            action_type=action.action_type,
            event=CANCELLED,
            result={"status": CANCELLED},
        )
    )
    await session.commit()
