"""Create and inspect structure-aware chunks from normalized filing Markdown."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import tiktoken
from docling.chunking import HierarchicalChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.doc_chunk import DocChunk
from docling_core.types.doc.document import DoclingDocument

from app.config import settings

EMBEDDING_INPUT_TOKEN_LIMIT = 8192


@dataclass(frozen=True)
class FilingSpec:
    accession_number: str
    ticker: str
    filing_type: str
    year: int
    markdown_path: Path


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    content: str
    token_count: int
    section: str | None
    page: int | None
    metadata: dict[str, object]


def load_filing_specs(manifest_path: Path, markdown_dir: Path) -> list[FilingSpec]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        FilingSpec(
            accession_number=filing["accession_number"],
            ticker=filing["ticker"],
            filing_type=filing["form"],
            year=int(filing["report_date"][:4]),
            markdown_path=markdown_dir / Path(filing["local_path"]).with_suffix(".md"),
        )
        for filing in manifest["filings"]
    ]


def _pages(chunk: DocChunk) -> list[int]:
    return sorted(
        {
            provenance.page_no
            for item in chunk.meta.doc_items
            for provenance in item.prov
        }
    )


def chunk_document(
    document: DoclingDocument,
    filing: FilingSpec,
    count_tokens: Callable[[str], int],
    *,
    max_tokens: int = EMBEDDING_INPUT_TOKEN_LIMIT,
) -> list[ChunkRecord]:
    chunker = HierarchicalChunker(merge_list_items=True)
    records: list[ChunkRecord] = []

    for index, chunk in enumerate(chunker.chunk(document)):
        if not isinstance(chunk, DocChunk):
            raise TypeError(f"expected DocChunk, got {type(chunk).__name__}")

        content = chunker.contextualize(chunk).strip()
        if not content:
            raise ValueError(f"empty chunk at index {index}")

        token_count = count_tokens(content)
        if token_count > max_tokens:
            raise ValueError(
                f"chunk {index} has {token_count} tokens; limit is {max_tokens}"
            )

        headings = list(chunk.meta.headings or [])
        pages = _pages(chunk)
        records.append(
            ChunkRecord(
                chunk_index=index,
                content=content,
                token_count=token_count,
                section=headings[-1] if headings else None,
                page=pages[0] if pages else None,
                metadata={
                    "accession_number": filing.accession_number,
                    "ticker": filing.ticker,
                    "filing_type": filing.filing_type,
                    "year": filing.year,
                    "headings": headings,
                    "pages": pages,
                    "doc_item_refs": [item.self_ref for item in chunk.meta.doc_items],
                    "chunking_strategy": "docling_hierarchical",
                },
            )
        )

    return records


def chunk_filing(
    filing: FilingSpec,
    *,
    converter: DocumentConverter | None = None,
) -> list[ChunkRecord]:
    encoding = tiktoken.encoding_for_model(settings.openai_embedding_model)
    document = (converter or DocumentConverter()).convert(filing.markdown_path).document
    return chunk_document(document, filing, lambda text: len(encoding.encode(text)))


def select_filing(filings: Iterable[FilingSpec], ticker: str, year: int) -> FilingSpec:
    matches = [
        filing
        for filing in filings
        if filing.ticker == ticker.upper() and filing.year == year
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one filing for {ticker.upper()} {year}, found {len(matches)}"
        )
    return matches[0]


def print_preview(
    filing: FilingSpec,
    chunks: list[ChunkRecord],
    *,
    chunk_index: int | None = None,
    find_text: str | None = None,
) -> None:
    if not chunks:
        raise ValueError("filing produced no chunks")

    counts = [chunk.token_count for chunk in chunks]
    print(f"filing: {filing.ticker} {filing.filing_type} {filing.year}")
    print(f"accession: {filing.accession_number}")
    print(f"chunks: {len(chunks)}")
    print(f"tokens: min={min(counts)}, average={mean(counts):.1f}, max={max(counts)}")
    print(f"chunks with pages: {sum(chunk.page is not None for chunk in chunks)}")

    selected: ChunkRecord | None = None
    if chunk_index is not None:
        if chunk_index < 0 or chunk_index >= len(chunks):
            raise ValueError(f"chunk index must be between 0 and {len(chunks) - 1}")
        selected = chunks[chunk_index]
    elif find_text:
        needle = find_text.casefold()
        selected = next(
            (chunk for chunk in chunks if needle in chunk.content.casefold()), None
        )
        if selected is None:
            raise ValueError(f"no chunk contains {find_text!r}")

    if selected is None:
        return

    print("\nselected chunk")
    print(
        json.dumps(
            {
                "chunk_index": selected.chunk_index,
                "token_count": selected.token_count,
                "section": selected.section,
                "page": selected.page,
                "metadata": selected.metadata,
            },
            indent=2,
        )
    )
    print("\nembedding input")
    print(selected.content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("markdown_dir", type=Path)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--year", required=True, type=int)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--chunk-index", type=int)
    selection.add_argument("--find")
    args = parser.parse_args()

    filing = select_filing(
        load_filing_specs(args.manifest, args.markdown_dir), args.ticker, args.year
    )
    chunks = chunk_filing(filing)
    print_preview(
        filing,
        chunks,
        chunk_index=args.chunk_index,
        find_text=args.find,
    )


if __name__ == "__main__":
    main()
