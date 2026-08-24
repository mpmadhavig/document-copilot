from types import SimpleNamespace

from ingest.chunk_documents import ChunkRecord
from ingest.embed_chunks import embed_batch, embed_one


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.25] * 1536)],
            model="text-embedding-3-small",
            usage=SimpleNamespace(prompt_tokens=12, total_tokens=12),
        )


class FakeBatchEmbeddings:
    def create(self, **kwargs):
        assert kwargs["input"] == ["first", "second"]
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.2] * 1536),
                SimpleNamespace(index=0, embedding=[0.1] * 1536),
            ],
            usage=SimpleNamespace(prompt_tokens=7, total_tokens=7),
        )


def test_embed_one_sends_exactly_one_chunk_and_returns_review() -> None:
    embeddings = FakeEmbeddings()
    client = SimpleNamespace(embeddings=embeddings)
    chunk = ChunkRecord(
        chunk_index=3,
        content="ITEM 1. BUSINESS\nApple designs products.",
        token_count=9,
        section="ITEM 1. BUSINESS",
        page=None,
        metadata={},
    )

    review = embed_one(client, chunk)

    assert len(embeddings.calls) == 1
    assert embeddings.calls[0]["input"] == chunk.content
    assert embeddings.calls[0]["dimensions"] == 1536
    assert review.dimensions == 1536
    assert review.prompt_tokens == 12
    assert review.vector_preview == [0.25] * 8


def test_embed_batch_preserves_chunk_order() -> None:
    client = SimpleNamespace(embeddings=FakeBatchEmbeddings())
    chunks = [
        ChunkRecord(0, "first", 1, None, None, {}),
        ChunkRecord(1, "second", 1, None, None, {}),
    ]

    result = embed_batch(client, chunks)

    assert len(result.vectors) == 2
    assert result.vectors[0][0] == 0.1
    assert result.vectors[1][0] == 0.2
    assert result.total_tokens == 7
