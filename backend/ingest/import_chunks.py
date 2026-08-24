"""Embed hierarchical chunks and atomically store them per source document."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentChunk, SourceDocument
from ingest.chunk_documents import (
    ChunkRecord,
    FilingSpec,
    chunk_filing,
    load_filing_specs,
)
from ingest.embed_chunks import EmbeddingBatch, embed_batch

MAX_EMBEDDING_INPUTS = 2048
MAX_EMBEDDING_REQUEST_TOKENS = 300_000
DEFAULT_REQUEST_TOKEN_LIMIT = 30_000


@dataclass(frozen=True)
class PendingDocument:
    filing: FilingSpec
    document_id: Any
    content_sha256: str
    chunks: list[ChunkRecord]

    @property
    def token_count(self) -> int:
        return sum(chunk.token_count for chunk in self.chunks)


def _is_current(
    session: Session,
    document: SourceDocument,
    chunks: list[ChunkRecord],
    content_sha256: str,
) -> bool:
    stored = session.execute(
        select(DocumentChunk.chunk_index, DocumentChunk.metadata_)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    return len(stored) == len(chunks) and all(
        chunk_index == expected_index
        and metadata.get("content_sha256") == content_sha256
        and metadata.get("embedding_model") == settings.openai_embedding_model
        for expected_index, (chunk_index, metadata) in enumerate(stored)
    )


def prepare_documents(
    session: Session, filings: list[FilingSpec]
) -> tuple[list[PendingDocument], int]:
    documents = {
        document.accession_number: document
        for document in session.scalars(select(SourceDocument))
    }
    pending: list[PendingDocument] = []
    skipped = 0

    for filing in filings:
        document = documents.get(filing.accession_number)
        if document is None:
            raise ValueError(
                f"source document is missing for accession {filing.accession_number}"
            )
        content_sha256 = document.metadata_.get("content_sha256")
        if not isinstance(content_sha256, str):
            raise TypeError(
                f"source document {filing.accession_number} has no content_sha256"
            )

        chunks = chunk_filing(filing)
        if len(chunks) > MAX_EMBEDDING_INPUTS:
            raise ValueError(
                f"{filing.accession_number} has {len(chunks)} chunks; "
                f"request limit is {MAX_EMBEDDING_INPUTS}"
            )
        token_count = sum(chunk.token_count for chunk in chunks)
        if token_count > MAX_EMBEDDING_REQUEST_TOKENS:
            raise ValueError(
                f"{filing.accession_number} has {token_count} tokens; "
                f"request limit is {MAX_EMBEDDING_REQUEST_TOKENS}"
            )

        if _is_current(session, document, chunks, content_sha256):
            skipped += 1
            print(f"skip {filing.ticker} {filing.year}: {len(chunks)} current chunks")
            continue

        pending.append(
            PendingDocument(
                filing=filing,
                document_id=document.id,
                content_sha256=content_sha256,
                chunks=chunks,
            )
        )
        print(
            f"pending {filing.ticker} {filing.year}: "
            f"{len(chunks)} chunks, {token_count} tokens"
        )

    return pending, skipped


def store_document(
    session: Session, pending: PendingDocument, embedding: EmbeddingBatch
) -> None:
    if len(embedding.vectors) != len(pending.chunks):
        raise ValueError("embedding count does not match chunk count")

    session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == pending.document_id)
    )
    for chunk, vector in zip(pending.chunks, embedding.vectors, strict=True):
        metadata = {
            **chunk.metadata,
            "content_sha256": pending.content_sha256,
            "embedding_model": settings.openai_embedding_model,
        }
        session.add(
            DocumentChunk(
                document_id=pending.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                section=chunk.section,
                page=chunk.page,
                token_count=chunk.token_count,
                embedding=vector,
                metadata_=metadata,
            )
        )


def split_embedding_requests(
    chunks: list[ChunkRecord], *, max_tokens: int
) -> list[list[ChunkRecord]]:
    if max_tokens <= 0:
        raise ValueError("request token limit must be positive")
    requests: list[list[ChunkRecord]] = []
    current: list[ChunkRecord] = []
    current_tokens = 0
    for chunk in chunks:
        if chunk.token_count > max_tokens:
            raise ValueError(
                f"chunk {chunk.chunk_index} has {chunk.token_count} tokens; "
                f"request budget is {max_tokens}"
            )
        if current and current_tokens + chunk.token_count > max_tokens:
            requests.append(current)
            current = []
            current_tokens = 0
        current.append(chunk)
        current_tokens += chunk.token_count
    if current:
        requests.append(current)
    return requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("markdown_dir", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true")
    mode.add_argument("--all", action="store_true")
    parser.add_argument(
        "--max-total-tokens",
        type=int,
        help="Required spending guard for --all; no calls occur if estimate exceeds it.",
    )
    parser.add_argument(
        "--tokens-per-minute",
        type=int,
        help="Required account TPM limit for --all; controls request pacing.",
    )
    args = parser.parse_args()
    if args.all and args.max_total_tokens is None:
        parser.error("--all requires --max-total-tokens")
    if args.all and args.tokens_per_minute is None:
        parser.error("--all requires --tokens-per-minute")
    if args.tokens_per_minute is not None and args.tokens_per_minute <= 0:
        parser.error("--tokens-per-minute must be positive")

    engine = create_engine(settings.sqlalchemy_database_url)
    try:
        with Session(engine) as session:
            pending, skipped = prepare_documents(
                session, load_filing_specs(args.manifest, args.markdown_dir)
            )

        total_chunks = sum(len(document.chunks) for document in pending)
        total_tokens = sum(document.token_count for document in pending)
        print(
            f"estimate: {len(pending)} pending documents, {skipped} skipped, "
            f"{total_chunks} chunks, {total_tokens} tokens"
        )
        if args.estimate or not pending:
            return
        if total_tokens > args.max_total_tokens:
            raise ValueError(
                f"estimate {total_tokens} exceeds budget {args.max_total_tokens}; "
                "no embedding calls made"
            )

        client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(), max_retries=0
        )
        used_tokens = 0
        stored_chunks = 0
        previous_request_tokens = 0
        for index, document in enumerate(pending, start=1):
            vectors: list[list[float]] = []
            document_tokens = 0
            requests = split_embedding_requests(
                document.chunks,
                max_tokens=min(
                    DEFAULT_REQUEST_TOKEN_LIMIT,
                    args.tokens_per_minute * 3 // 4,
                ),
            )
            for request_index, request_chunks in enumerate(requests, start=1):
                if previous_request_tokens:
                    wait_seconds = (
                        previous_request_tokens / args.tokens_per_minute * 60 + 1
                    )
                    print(
                        f"rate-limit wait: {wait_seconds:.1f}s before "
                        f"{document.filing.ticker} {document.filing.year} "
                        f"request {request_index}/{len(requests)}"
                    )
                    time.sleep(wait_seconds)
                request_tokens = sum(chunk.token_count for chunk in request_chunks)
                result = embed_batch(client, request_chunks)
                vectors.extend(result.vectors)
                document_tokens += result.total_tokens
                previous_request_tokens = request_tokens

            embedding = EmbeddingBatch(
                vectors=vectors,
                prompt_tokens=document_tokens,
                total_tokens=document_tokens,
            )
            with Session(engine) as session, session.begin():
                store_document(session, document, embedding)
            used_tokens += embedding.total_tokens
            stored_chunks += len(document.chunks)
            print(
                f"stored {index}/{len(pending)} {document.filing.ticker} "
                f"{document.filing.year}: {len(document.chunks)} chunks, "
                f"{embedding.total_tokens} API tokens, {len(requests)} requests"
            )

        print(f"complete: {stored_chunks} chunks stored, {used_tokens} API tokens used")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
