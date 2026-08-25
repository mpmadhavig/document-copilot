"""Add atomic grounded chat persistence and chat UUID defaults.

Revision ID: 20260824_05
Revises: 20260824_04
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_05"
down_revision: str | Sequence[str] | None = "20260824_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_threads ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE chat_messages ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE message_citations ALTER COLUMN id SET DEFAULT gen_random_uuid();

        CREATE FUNCTION append_grounded_chat_turn(
            target_thread_id uuid,
            user_message jsonb,
            assistant_message jsonb,
            assistant_model text,
            assistant_usage jsonb,
            citations jsonb
        ) RETURNS uuid
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = public
        AS $$
        DECLARE
            next_sequence bigint;
            assistant_message_id uuid;
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

            INSERT INTO chat_messages (id, thread_id, role, sequence, content)
            VALUES (
                gen_random_uuid(),
                target_thread_id,
                'user',
                next_sequence,
                user_message
            );

            INSERT INTO chat_messages (
                id, thread_id, role, sequence, content, model, usage
            ) VALUES (
                gen_random_uuid(),
                target_thread_id,
                'assistant',
                next_sequence + 1,
                assistant_message,
                assistant_model,
                assistant_usage
            ) RETURNING id INTO assistant_message_id;

            INSERT INTO message_citations (
                id, message_id, chunk_id, position, quote
            )
            SELECT
                gen_random_uuid(),
                assistant_message_id,
                (citation->>'chunk_id')::uuid,
                (citation->>'position')::integer,
                citation->>'quote'
            FROM jsonb_array_elements(citations) AS citation;

            UPDATE chat_threads SET updated_at = now() WHERE id = target_thread_id;
            RETURN assistant_message_id;
        END;
        $$;

        REVOKE ALL ON FUNCTION append_grounded_chat_turn(
            uuid, jsonb, jsonb, text, jsonb, jsonb
        ) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION append_grounded_chat_turn(
            uuid, jsonb, jsonb, text, jsonb, jsonb
        ) TO authenticated;
        """
    )


def downgrade() -> None:
    op.execute(
        """DROP FUNCTION append_grounded_chat_turn(
            uuid, jsonb, jsonb, text, jsonb, jsonb
        )"""
    )
    op.execute(
        """
        ALTER TABLE message_citations ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE chat_messages ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE chat_threads ALTER COLUMN id DROP DEFAULT;
        """
    )
