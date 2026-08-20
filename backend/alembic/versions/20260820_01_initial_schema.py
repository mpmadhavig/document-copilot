"""Create the initial application schema.

Revision ID: 20260820_01
Revises:
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260820_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accession_number", sa.String(length=30), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("company_name", sa.String(length=300), nullable=False),
        sa.Column("filing_type", sa.String(length=30), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_number"),
    )
    op.create_index(
        "ix_source_documents_ticker_filing_date",
        "source_documents",
        ["ticker", "filing_date"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0", name="ck_document_chunks_index_nonnegative"
        ),
        sa.CheckConstraint(
            "token_count > 0", name="ck_document_chunks_token_count_positive"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["source_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_position"
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"]
    )
    op.create_index(
        "ix_document_chunks_metadata",
        "document_chunks",
        ["metadata"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_threads_user_updated", "chat_threads", ["user_id", "updated_at"]
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("usage", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role in ('user', 'assistant', 'system')", name="ck_chat_messages_role"
        ),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "sequence", name="uq_chat_messages_sequence"),
    )
    op.create_index(
        "ix_chat_messages_thread_created", "chat_messages", ["thread_id", "created_at"]
    )

    op.create_table(
        "message_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_message_citations_position_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "position", name="uq_message_citations_position"
        ),
    )

    _enable_row_level_security()


def downgrade() -> None:
    op.drop_table("message_citations")
    op.drop_index("ix_chat_messages_thread_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_threads_user_updated", table_name="chat_threads")
    op.drop_table("chat_threads")
    op.drop_index(
        "ix_document_chunks_embedding_hnsw",
        table_name="document_chunks",
        postgresql_using="hnsw",
    )
    op.drop_index(
        "ix_document_chunks_search_vector",
        table_name="document_chunks",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_document_chunks_metadata",
        table_name="document_chunks",
        postgresql_using="gin",
    )
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index(
        "ix_source_documents_ticker_filing_date", table_name="source_documents"
    )
    op.drop_table("source_documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")


def _enable_row_level_security() -> None:
    for table in (
        "users",
        "source_documents",
        "document_chunks",
        "chat_threads",
        "chat_messages",
        "message_citations",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY users_select_own ON users FOR SELECT TO authenticated USING (auth.uid() = id)"
    )
    op.execute(
        "CREATE POLICY users_update_own ON users FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id)"
    )
    op.execute(
        "CREATE POLICY source_documents_select_authenticated ON source_documents FOR SELECT TO authenticated USING (true)"
    )
    op.execute(
        "CREATE POLICY document_chunks_select_authenticated ON document_chunks FOR SELECT TO authenticated USING (true)"
    )

    for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        policy = f"chat_threads_{action.lower()}_own"
        if action == "INSERT":
            clause = "WITH CHECK (auth.uid() = user_id)"
        elif action == "UPDATE":
            clause = "USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)"
        else:
            clause = "USING (auth.uid() = user_id)"
        op.execute(
            f"CREATE POLICY {policy} ON chat_threads FOR {action} TO authenticated {clause}"
        )

    thread_owner = "EXISTS (SELECT 1 FROM chat_threads WHERE chat_threads.id = chat_messages.thread_id AND chat_threads.user_id = auth.uid())"
    for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        policy = f"chat_messages_{action.lower()}_own"
        if action == "INSERT":
            clause = f"WITH CHECK ({thread_owner})"
        elif action == "UPDATE":
            clause = f"USING ({thread_owner}) WITH CHECK ({thread_owner})"
        else:
            clause = f"USING ({thread_owner})"
        op.execute(
            f"CREATE POLICY {policy} ON chat_messages FOR {action} TO authenticated {clause}"
        )

    message_owner = "EXISTS (SELECT 1 FROM chat_messages JOIN chat_threads ON chat_threads.id = chat_messages.thread_id WHERE chat_messages.id = message_citations.message_id AND chat_threads.user_id = auth.uid())"
    for action in ("SELECT", "INSERT", "DELETE"):
        policy = f"message_citations_{action.lower()}_own"
        clause = (
            f"WITH CHECK ({message_owner})"
            if action == "INSERT"
            else f"USING ({message_owner})"
        )
        op.execute(
            f"CREATE POLICY {policy} ON message_citations FOR {action} TO authenticated {clause}"
        )
