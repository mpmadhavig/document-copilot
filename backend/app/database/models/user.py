"""Application user model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.chat_thread import ChatThread


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # This UUID matches the user managed by Supabase Auth. The cross-schema
    # foreign key to auth.users belongs in the migration.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))

    chat_threads: Mapped[list["ChatThread"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
