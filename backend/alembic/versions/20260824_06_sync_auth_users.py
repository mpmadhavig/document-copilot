"""Sync Supabase Auth users into the application users table.

Revision ID: 20260824_06
Revises: 20260824_05
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_06"
down_revision: str | Sequence[str] | None = "20260824_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION public.sync_auth_user_to_public_users()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = ''
        AS $$
        BEGIN
            IF NEW.email IS NULL THEN
                RETURN NEW;
            END IF;

            INSERT INTO public.users (
                id,
                email,
                display_name,
                created_at,
                updated_at
            ) VALUES (
                NEW.id,
                NEW.email,
                NULLIF(
                    COALESCE(
                        NEW.raw_user_meta_data->>'display_name',
                        NEW.raw_user_meta_data->>'full_name'
                    ),
                    ''
                ),
                COALESCE(NEW.created_at, now()),
                now()
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                display_name = COALESCE(
                    public.users.display_name,
                    EXCLUDED.display_name
                ),
                updated_at = now();

            RETURN NEW;
        END;
        $$;

        REVOKE ALL ON FUNCTION public.sync_auth_user_to_public_users()
        FROM PUBLIC, anon, authenticated;

        CREATE TRIGGER on_auth_user_created_or_updated
        AFTER INSERT OR UPDATE OF email, raw_user_meta_data ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.sync_auth_user_to_public_users();

        INSERT INTO public.users (
            id,
            email,
            display_name,
            created_at,
            updated_at
        )
        SELECT
            id,
            email,
            NULLIF(
                COALESCE(
                    raw_user_meta_data->>'display_name',
                    raw_user_meta_data->>'full_name'
                ),
                ''
            ),
            COALESCE(created_at, now()),
            COALESCE(updated_at, now())
        FROM auth.users
        WHERE email IS NOT NULL
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            display_name = COALESCE(
                public.users.display_name,
                EXCLUDED.display_name
            ),
            updated_at = now();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS on_auth_user_created_or_updated ON auth.users;
        DROP FUNCTION IF EXISTS public.sync_auth_user_to_public_users();
        """
    )
