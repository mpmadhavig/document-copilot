import uuid
from datetime import date

from app.database.models import DocumentChunk, SourceDocument
from ingest.chunk_documents import ChunkRecord, FilingSpec
from ingest.embed_chunks import EmbeddingBatch
from ingest.import_chunks import (
    PendingDocument,
    split_embedding_requests,
    store_document,
)


class FakeSession:
    def __init__(self) -> None:
        self.executed = []
        self.added = []

    def execute(self, statement) -> None:
        self.executed.append(statement)

    def add(self, value) -> None:
        self.added.append(value)


def test_store_document_replaces_chunks_with_auditable_metadata(tmp_path) -> None:
    document = SourceDocument(
        id=uuid.uuid4(),
        accession_number="accession",
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2021, 10, 29),
        source_url="https://example.com",
        content_markdown="content",
        metadata_={"content_sha256": "hash"},
    )
    filing = FilingSpec("accession", "AAPL", "10-K", 2021, tmp_path / "aapl.md")
    chunks = [
        ChunkRecord(
            chunk_index=0,
            content="PART I\nContent",
            token_count=4,
            section="PART I",
            page=None,
            metadata={"ticker": "AAPL"},
        )
    ]
    pending = PendingDocument(filing, document.id, "hash", chunks)
    embedding = EmbeddingBatch([[0.1] * 1536], 4, 4)
    session = FakeSession()

    store_document(session, pending, embedding)

    assert len(session.executed) == 1
    assert len(session.added) == 1
    stored: DocumentChunk = session.added[0]
    assert stored.document_id == document.id
    assert stored.embedding == [0.1] * 1536
    assert stored.metadata_["content_sha256"] == "hash"
    assert stored.metadata_["embedding_model"] == "text-embedding-3-small"


def test_split_embedding_requests_stays_within_token_limit() -> None:
    chunks = [
        ChunkRecord(0, "first", 6, None, None, {}),
        ChunkRecord(1, "second", 5, None, None, {}),
        ChunkRecord(2, "third", 4, None, None, {}),
    ]

    requests = split_embedding_requests(chunks, max_tokens=10)

    assert [[chunk.chunk_index for chunk in request] for request in requests] == [
        [0],
        [1, 2],
    ]
    assert all(
        sum(chunk.token_count for chunk in request) <= 10 for request in requests
    )
