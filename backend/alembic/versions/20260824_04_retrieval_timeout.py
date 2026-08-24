"""Allow semantic retrieval to outlast the Supabase API default timeout.

Revision ID: 20260824_04
Revises: 20260824_03
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_04"
down_revision: str | Sequence[str] | None = "20260824_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER FUNCTION semantic_search_chunks(
            vector, integer, text[], integer[], text[]
        ) SET statement_timeout = '30s'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER FUNCTION semantic_search_chunks(
            vector, integer, text[], integer[], text[]
        ) RESET statement_timeout
        """
    )
