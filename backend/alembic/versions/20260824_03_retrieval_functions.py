"""Add ranked retrieval functions.

Revision ID: 20260824_03
Revises: 20260820_02
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_03"
down_revision: str | Sequence[str] | None = "20260820_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION semantic_search_chunks(
            p_query_embedding vector(1536),
            p_match_count integer DEFAULT 30,
            p_tickers text[] DEFAULT NULL,
            p_years integer[] DEFAULT NULL,
            p_filing_types text[] DEFAULT NULL
        ) RETURNS TABLE (
            chunk_id uuid,
            document_id uuid,
            chunk_index integer,
            content text,
            section text,
            page integer,
            chunk_metadata jsonb,
            accession_number text,
            ticker text,
            company_name text,
            filing_type text,
            filing_date date,
            source_url text,
            document_metadata jsonb,
            score double precision
        )
        LANGUAGE sql
        STABLE
        SECURITY INVOKER
        SET search_path = public
        AS $$
            SELECT
                chunk.id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.content,
                chunk.section,
                chunk.page,
                chunk.metadata,
                document.accession_number::text,
                document.ticker::text,
                document.company_name::text,
                document.filing_type::text,
                document.filing_date,
                document.source_url,
                document.metadata,
                (1 - (chunk.embedding <=> p_query_embedding))::double precision
            FROM document_chunks AS chunk
            JOIN source_documents AS document ON document.id = chunk.document_id
            WHERE (p_tickers IS NULL OR document.ticker = ANY(p_tickers))
              AND (
                  p_years IS NULL
                  OR (chunk.metadata ->> 'year')::integer = ANY(p_years)
              )
              AND (
                  p_filing_types IS NULL
                  OR document.filing_type = ANY(p_filing_types)
              )
            ORDER BY chunk.embedding <=> p_query_embedding
            LIMIT LEAST(GREATEST(COALESCE(p_match_count, 30), 1), 100);
        $$;

        CREATE FUNCTION full_text_search_chunks(
            p_query_text text,
            p_match_count integer DEFAULT 30,
            p_tickers text[] DEFAULT NULL,
            p_years integer[] DEFAULT NULL,
            p_filing_types text[] DEFAULT NULL
        ) RETURNS TABLE (
            chunk_id uuid,
            document_id uuid,
            chunk_index integer,
            content text,
            section text,
            page integer,
            chunk_metadata jsonb,
            accession_number text,
            ticker text,
            company_name text,
            filing_type text,
            filing_date date,
            source_url text,
            document_metadata jsonb,
            score real
        )
        LANGUAGE sql
        STABLE
        SECURITY INVOKER
        SET search_path = public
        AS $$
            WITH parsed_query AS (
                SELECT websearch_to_tsquery('english', p_query_text) AS value
            )
            SELECT
                chunk.id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.content,
                chunk.section,
                chunk.page,
                chunk.metadata,
                document.accession_number::text,
                document.ticker::text,
                document.company_name::text,
                document.filing_type::text,
                document.filing_date,
                document.source_url,
                document.metadata,
                ts_rank_cd(chunk.search_vector, parsed_query.value, 32)
            FROM document_chunks AS chunk
            JOIN source_documents AS document ON document.id = chunk.document_id
            CROSS JOIN parsed_query
            WHERE chunk.search_vector @@ parsed_query.value
              AND (p_tickers IS NULL OR document.ticker = ANY(p_tickers))
              AND (
                  p_years IS NULL
                  OR (chunk.metadata ->> 'year')::integer = ANY(p_years)
              )
              AND (
                  p_filing_types IS NULL
                  OR document.filing_type = ANY(p_filing_types)
              )
            ORDER BY
                ts_rank_cd(chunk.search_vector, parsed_query.value, 32) DESC,
                chunk.id
            LIMIT LEAST(GREATEST(COALESCE(p_match_count, 30), 1), 100);
        $$;

        CREATE FUNCTION get_chunk_neighbors(
            p_seed_chunk_ids uuid[],
            p_window integer DEFAULT 1
        ) RETURNS TABLE (
            seed_chunk_id uuid,
            chunk_id uuid,
            document_id uuid,
            chunk_index integer,
            content text,
            section text,
            page integer,
            chunk_metadata jsonb,
            accession_number text,
            ticker text,
            company_name text,
            filing_type text,
            filing_date date,
            source_url text,
            document_metadata jsonb
        )
        LANGUAGE sql
        STABLE
        SECURITY INVOKER
        SET search_path = public
        AS $$
            SELECT
                seed.id,
                neighbor.id,
                neighbor.document_id,
                neighbor.chunk_index,
                neighbor.content,
                neighbor.section,
                neighbor.page,
                neighbor.metadata,
                document.accession_number::text,
                document.ticker::text,
                document.company_name::text,
                document.filing_type::text,
                document.filing_date,
                document.source_url,
                document.metadata
            FROM document_chunks AS seed
            JOIN document_chunks AS neighbor
              ON neighbor.document_id = seed.document_id
             AND neighbor.chunk_index BETWEEN
                 seed.chunk_index - LEAST(GREATEST(COALESCE(p_window, 1), 0), 3)
                 AND seed.chunk_index + LEAST(GREATEST(COALESCE(p_window, 1), 0), 3)
             AND neighbor.id <> seed.id
            JOIN source_documents AS document ON document.id = neighbor.document_id
            WHERE seed.id = ANY(p_seed_chunk_ids)
            ORDER BY seed.id, neighbor.chunk_index;
        $$;

        REVOKE ALL ON FUNCTION semantic_search_chunks(vector, integer, text[], integer[], text[]) FROM PUBLIC;
        REVOKE ALL ON FUNCTION full_text_search_chunks(text, integer, text[], integer[], text[]) FROM PUBLIC;
        REVOKE ALL ON FUNCTION get_chunk_neighbors(uuid[], integer) FROM PUBLIC;

        GRANT EXECUTE ON FUNCTION semantic_search_chunks(vector, integer, text[], integer[], text[]) TO authenticated, service_role;
        GRANT EXECUTE ON FUNCTION full_text_search_chunks(text, integer, text[], integer[], text[]) TO authenticated, service_role;
        GRANT EXECUTE ON FUNCTION get_chunk_neighbors(uuid[], integer) TO authenticated, service_role;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION get_chunk_neighbors(uuid[], integer)")
    op.execute(
        "DROP FUNCTION full_text_search_chunks(text, integer, text[], integer[], text[])"
    )
    op.execute(
        "DROP FUNCTION semantic_search_chunks(vector, integer, text[], integer[], text[])"
    )
