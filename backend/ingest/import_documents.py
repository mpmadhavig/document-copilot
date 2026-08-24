"""Import normalized filing Markdown into the source_documents table."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import SourceDocument

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
}


@dataclass(frozen=True)
class DocumentRecord:
    accession_number: str
    ticker: str
    company_name: str
    filing_type: str
    filing_date: date
    source_url: str
    content_markdown: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    updated: int
    unchanged: int


def _markdown_path(markdown_dir: Path, local_path: str) -> Path:
    return markdown_dir / Path(local_path).with_suffix(".md")


def load_records(manifest_path: Path, markdown_dir: Path) -> list[DocumentRecord]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    filings = manifest["filings"]
    records: list[DocumentRecord] = []
    accessions: set[str] = set()

    for filing in filings:
        accession_number = filing["accession_number"]
        if accession_number in accessions:
            raise ValueError(f"duplicate accession number: {accession_number}")
        accessions.add(accession_number)

        ticker = filing["ticker"]
        path = _markdown_path(markdown_dir, filing["local_path"])
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"Markdown document is empty: {path}")

        markdown_local_path = str(path.relative_to(markdown_dir))
        records.append(
            DocumentRecord(
                accession_number=accession_number,
                ticker=ticker,
                company_name=COMPANY_NAMES[ticker],
                filing_type=filing["form"],
                filing_date=date.fromisoformat(filing["filing_date"]),
                source_url=filing["source_url"],
                content_markdown=content,
                metadata={
                    "cik": filing["cik"],
                    "report_date": filing["report_date"],
                    "primary_document": filing["primary_document"],
                    "local_path": markdown_local_path,
                    "source": manifest["source"],
                    "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                },
            )
        )

    expected_count = manifest["downloaded_count"]
    if len(records) != expected_count:
        raise ValueError(
            f"manifest declares {expected_count} filings but contains {len(records)}"
        )
    return records


def _document_values(record: DocumentRecord) -> dict[str, Any]:
    return {
        "ticker": record.ticker,
        "company_name": record.company_name,
        "filing_type": record.filing_type,
        "filing_date": record.filing_date,
        "source_url": record.source_url,
        "content_markdown": record.content_markdown,
        "metadata_": record.metadata,
    }


def _update_document(document: SourceDocument, record: DocumentRecord) -> bool:
    values = _document_values(record)
    changed = any(getattr(document, key) != value for key, value in values.items())
    if not changed:
        return False

    for key, value in values.items():
        setattr(document, key, value)
    document.updated_at = datetime.now(UTC)
    return True


def import_records(session: Session, records: list[DocumentRecord]) -> ImportResult:
    accessions = [record.accession_number for record in records]
    existing = {
        document.accession_number: document
        for document in session.scalars(
            select(SourceDocument).where(
                SourceDocument.accession_number.in_(accessions)
            )
        )
    }

    inserted = updated = unchanged = 0
    for record in records:
        document = existing.get(record.accession_number)
        if document is None:
            session.add(
                SourceDocument(
                    accession_number=record.accession_number,
                    **_document_values(record),
                )
            )
            inserted += 1
        elif _update_document(document, record):
            updated += 1
        else:
            unchanged += 1

    return ImportResult(inserted=inserted, updated=updated, unchanged=unchanged)


def import_corpus(manifest_path: Path, markdown_dir: Path) -> ImportResult:
    records = load_records(manifest_path, markdown_dir)
    engine = create_engine(settings.sqlalchemy_database_url)
    try:
        with Session(engine) as session, session.begin():
            result = import_records(session, records)
    finally:
        engine.dispose()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("markdown_dir", type=Path)
    args = parser.parse_args()
    result = import_corpus(args.manifest, args.markdown_dir)
    print(
        f"source_documents: {result.inserted} inserted, "
        f"{result.updated} updated, {result.unchanged} unchanged"
    )


if __name__ == "__main__":
    main()
