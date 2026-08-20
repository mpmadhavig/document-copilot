"""Add atomic chat turn persistence function.

Revision ID: 20260820_02
Revises: 20260820_01
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260820_02"
down_revision: str | Sequence[str] | None = "20260820_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION append_chat_turn(
            target_thread_id uuid,
            user_message jsonb,
            assistant_message jsonb,
            assistant_model text
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = public
        AS $$
        DECLARE
            next_sequence bigint;
        BEGIN
            PERFORM 1
            FROM chat_threads
            WHERE id = target_thread_id AND user_id = auth.uid()
            FOR UPDATE;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'chat thread is not accessible'
                    USING ERRCODE = '42501';
            END IF;

            SELECT COALESCE(MAX(sequence), 0) + 1
            INTO next_sequence
            FROM chat_messages
            WHERE thread_id = target_thread_id;

            INSERT INTO chat_messages (thread_id, role, sequence, content)
            VALUES (target_thread_id, 'user', next_sequence, user_message);

            INSERT INTO chat_messages (thread_id, role, sequence, content, model)
            VALUES (
                target_thread_id,
                'assistant',
                next_sequence + 1,
                assistant_message,
                assistant_model
            );

            UPDATE chat_threads SET updated_at = now() WHERE id = target_thread_id;
        END;
        $$;

        REVOKE ALL ON FUNCTION append_chat_turn(uuid, jsonb, jsonb, text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION append_chat_turn(uuid, jsonb, jsonb, text) TO authenticated;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION append_chat_turn(uuid, jsonb, jsonb, text)")
