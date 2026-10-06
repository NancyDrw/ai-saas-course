"""Async SQLAlchemy models and Neon connection helpers."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, func, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class Couple(Base):
    __tablename__ = "couples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", server_default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserTransaction(Base):
    """A safe activity event, not a financial transaction."""

    __tablename__ = "user_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    couple_id: Mapped[int | None] = mapped_column(ForeignKey("couples.id"))
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_profile: Mapped[str | None] = mapped_column(String(50))
    content_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CreditTransaction(Base):
    """An admin-managed ledger entry for Intima credits."""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PendingAiAction(Base):
    """A proposed Intima credit change that needs explicit user confirmation."""

    __tablename__ = "pending_ai_actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiActionAuditLog(Base):
    """Audit trail for pending AI actions; it never stores application secrets."""

    __tablename__ = "ai_action_audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("pending_ai_actions.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event: Mapped[str] = mapped_column(String(30), nullable=False)
    result: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

def create_database_engine(database_url: str) -> AsyncEngine:
    """Create an async PostgreSQL engine with asyncpg for Neon."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode:
        query.setdefault("ssl", sslmode)
    url = url.set(query=query)

    return create_async_engine(url, connect_args={"timeout": 10}, pool_pre_ping=True)


async def apply_identity_schema_migration(connection) -> None:
    """Add nullable owner columns without assigning any legacy ledger data."""
    statements = (
        "ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id)",
        "ALTER TABLE pending_ai_actions ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id)",
        "ALTER TABLE ai_action_audit_logs ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id)",
        "CREATE INDEX IF NOT EXISTS ix_credit_transactions_user_id ON credit_transactions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_pending_ai_actions_user_id ON pending_ai_actions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ai_action_audit_logs_user_id ON ai_action_audit_logs (user_id)",
    )
    for statement in statements:
        await connection.execute(text(statement))
