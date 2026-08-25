"""Chat message model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base
from app.database.models.message_role import MessageRole

if TYPE_CHECKING:
    from app.database.models.chat_thread import ChatThread
    from app.database.models.message_citation import MessageCitation


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role in ('user', 'assistant', 'system')",
            name="ck_chat_messages_role",
        ),
        UniqueConstraint("thread_id", "sequence", name="uq_chat_messages_sequence"),
        Index("ix_chat_messages_thread_created", "thread_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    thread: Mapped["ChatThread"] = relationship(back_populates="messages")
    citations: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
