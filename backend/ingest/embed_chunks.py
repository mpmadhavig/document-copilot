"""Generate one review-only OpenAI embedding without database writes."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import settings
from ingest.chunk_documents import (
    ChunkRecord,
    chunk_filing,
    load_filing_specs,
    select_filing,
)


@dataclass(frozen=True)
class EmbeddingReview:
    model: str
    dimensions: int
    prompt_tokens: int
    total_tokens: int
    vector_preview: list[float]


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    prompt_tokens: int
    total_tokens: int


def embed_batch(client: Any, chunks: list[ChunkRecord]) -> EmbeddingBatch:
    if not chunks:
        raise ValueError("cannot embed an empty batch")
    response = client.embeddings.create(
        input=[chunk.content for chunk in chunks],
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
        encoding_format="float",
    )
    if len(response.data) != len(chunks):
        raise ValueError(f"expected {len(chunks)} embeddings, got {len(response.data)}")
    vectors = [
        item.embedding for item in sorted(response.data, key=lambda item: item.index)
    ]
    invalid_dimensions = {
        len(vector)
        for vector in vectors
        if len(vector) != settings.openai_embedding_dimensions
    }
    if invalid_dimensions:
        raise ValueError(
            f"expected {settings.openai_embedding_dimensions} dimensions, "
            f"got {sorted(invalid_dimensions)}"
        )
    return EmbeddingBatch(
        vectors=vectors,
        prompt_tokens=response.usage.prompt_tokens,
        total_tokens=response.usage.total_tokens,
    )


def embed_one(client: Any, chunk: ChunkRecord) -> EmbeddingReview:
    response = client.embeddings.create(
        input=chunk.content,
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
        encoding_format="float",
    )
    if len(response.data) != 1:
        raise ValueError(f"expected one embedding, got {len(response.data)}")
    vector = response.data[0].embedding
    if len(vector) != settings.openai_embedding_dimensions:
        raise ValueError(
            f"expected {settings.openai_embedding_dimensions} dimensions, "
            f"got {len(vector)}"
        )
    return EmbeddingReview(
        model=response.model,
        dimensions=len(vector),
        prompt_tokens=response.usage.prompt_tokens,
        total_tokens=response.usage.total_tokens,
        vector_preview=vector[:8],
    )


def _print_input(chunk: ChunkRecord) -> None:
    print("embedding request (one chunk, no database write)")
    print(
        json.dumps(
            {
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "section": chunk.section,
                "page": chunk.page,
                "metadata": chunk.metadata,
            },
            indent=2,
        )
    )
    print("\nexact embedding input")
    print(chunk.content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("markdown_dir", type=Path)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--chunk-index", required=True, type=int)
    parser.add_argument(
        "--confirm-one-api-call",
        action="store_true",
        help="Required acknowledgement that this command makes one paid API call.",
    )
    args = parser.parse_args()

    filing = select_filing(
        load_filing_specs(args.manifest, args.markdown_dir), args.ticker, args.year
    )
    chunks = chunk_filing(filing)
    if args.chunk_index < 0 or args.chunk_index >= len(chunks):
        raise ValueError(f"chunk index must be between 0 and {len(chunks) - 1}")
    chunk = chunks[args.chunk_index]
    _print_input(chunk)

    if not args.confirm_one_api_call:
        print(
            "\nNo API call made. Add --confirm-one-api-call after reviewing this input."
        )
        return

    review = embed_one(
        OpenAI(api_key=settings.openai_api_key.get_secret_value()), chunk
    )
    print("\nembedding response")
    print(
        json.dumps(
            {
                "model": review.model,
                "dimensions": review.dimensions,
                "prompt_tokens": review.prompt_tokens,
                "total_tokens": review.total_tokens,
                "vector_preview": review.vector_preview,
                "database_write": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
