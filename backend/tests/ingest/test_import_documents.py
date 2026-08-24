import hashlib
import json
from datetime import date

from app.database.models import SourceDocument
from ingest.import_documents import DocumentRecord, _update_document, load_records


def record(*, content: str = "content") -> DocumentRecord:
    return DocumentRecord(
        accession_number="0000320193-25-000079",
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2025, 10, 31),
        source_url="https://example.com/filing.htm",
        content_markdown=content,
        metadata={"content_sha256": hashlib.sha256(content.encode()).hexdigest()},
    )


def test_load_records_reads_manifest_and_markdown(tmp_path) -> None:
    markdown_dir = tmp_path / "markdown"
    markdown_path = markdown_dir / "2025" / "aapl.md"
    markdown_path.parent.mkdir(parents=True)
    markdown_path.write_text("# Apple filing\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "SEC EDGAR",
                "downloaded_count": 1,
                "filings": [
                    {
                        "ticker": "AAPL",
                        "cik": "0000320193",
                        "form": "10-K",
                        "filing_date": "2025-10-31",
                        "report_date": "2025-09-27",
                        "accession_number": "0000320193-25-000079",
                        "primary_document": "aapl.htm",
                        "source_url": "https://example.com/aapl.htm",
                        "local_path": "2025/aapl.htm",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    records = load_records(manifest_path, markdown_dir)

    assert len(records) == 1
    assert records[0].company_name == "Apple Inc."
    assert records[0].content_markdown == "# Apple filing\n"
    assert records[0].metadata["local_path"] == "2025/aapl.md"
    assert records[0].metadata["content_sha256"] == hashlib.sha256(
        b"# Apple filing\n"
    ).hexdigest()


def test_update_document_is_idempotent() -> None:
    source = record()
    document = SourceDocument(
        accession_number=source.accession_number,
        ticker=source.ticker,
        company_name=source.company_name,
        filing_type=source.filing_type,
        filing_date=source.filing_date,
        source_url=source.source_url,
        content_markdown=source.content_markdown,
        metadata_=source.metadata,
    )

    assert _update_document(document, source) is False


def test_update_document_replaces_changed_markdown() -> None:
    source = record(content="new content")
    document = SourceDocument(
        accession_number=source.accession_number,
        ticker=source.ticker,
        company_name=source.company_name,
        filing_type=source.filing_type,
        filing_date=source.filing_date,
        source_url=source.source_url,
        content_markdown="old content",
        metadata_={},
    )

    assert _update_document(document, source) is True
    assert document.content_markdown == "new content"
    assert document.metadata_ == source.metadata
    assert document.updated_at is not None
