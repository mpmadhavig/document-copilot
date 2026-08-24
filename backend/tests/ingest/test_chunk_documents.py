import json
from pathlib import Path

import pytest
from docling.document_converter import DocumentConverter

from ingest.chunk_documents import (
    FilingSpec,
    chunk_document,
    load_filing_specs,
    print_preview,
    select_filing,
)


def filing(path: Path) -> FilingSpec:
    return FilingSpec(
        accession_number="0000320193-21-000105",
        ticker="AAPL",
        filing_type="10-K",
        year=2021,
        markdown_path=path,
    )


def test_chunk_document_preserves_hierarchy_and_filing_metadata(tmp_path) -> None:
    path = tmp_path / "filing.md"
    path.write_text(
        """# Apple Inc.

## ITEM 1. BUSINESS

Apple designs and sells products.

- iPhone
- Mac

## ITEM 1A. RISK FACTORS

Demand may be affected by economic conditions.
""",
        encoding="utf-8",
    )
    document = DocumentConverter().convert(path).document

    chunks = chunk_document(document, filing(path), lambda text: len(text.split()))

    business = next(chunk for chunk in chunks if "designs and sells" in chunk.content)
    assert business.section == "ITEM 1. BUSINESS"
    assert business.page is None
    assert business.metadata["ticker"] == "AAPL"
    assert business.metadata["filing_type"] == "10-K"
    assert business.metadata["year"] == 2021
    assert business.metadata["headings"] == ["Apple Inc.", "ITEM 1. BUSINESS"]
    assert business.content.startswith("Apple Inc.\nITEM 1. BUSINESS\n")
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunk_document_rejects_oversized_chunk(tmp_path) -> None:
    path = tmp_path / "filing.md"
    path.write_text("# Heading\n\nA paragraph.", encoding="utf-8")
    document = DocumentConverter().convert(path).document

    with pytest.raises(ValueError, match="limit is 1"):
        chunk_document(document, filing(path), lambda _: 2, max_tokens=1)


def test_load_and_select_filing(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "filings": [
                    {
                        "accession_number": "accession",
                        "ticker": "AAPL",
                        "form": "10-K",
                        "report_date": "2021-09-25",
                        "local_path": "2021/aapl.htm",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    filings = load_filing_specs(manifest_path, tmp_path / "markdown")
    selected = select_filing(filings, "aapl", 2021)

    assert selected.markdown_path == tmp_path / "markdown/2021/aapl.md"
    assert selected.year == 2021


def test_preview_does_not_call_external_services(tmp_path, capsys) -> None:
    path = tmp_path / "filing.md"
    selected = filing(path)
    path.write_text("# Heading\n\nKnown passage.", encoding="utf-8")
    document = DocumentConverter().convert(path).document
    chunks = chunk_document(document, selected, lambda text: len(text.split()))

    print_preview(selected, chunks, find_text="known passage")

    output = capsys.readouterr().out
    assert "embedding input" in output
    assert "Known passage." in output
