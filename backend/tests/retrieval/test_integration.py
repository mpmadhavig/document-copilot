import pytest

from app.config import settings
from app.database.supabase import create_service_role_client
from app.retrieval.models import RetrievalFilters
from app.retrieval.retriever import DocumentRetriever


@pytest.mark.integration
@pytest.mark.anyio
async def test_retrieves_apple_services_passage_from_live_corpus() -> None:
    if str(settings.supabase_url).startswith("https://example."):
        pytest.skip("export live Supabase and OpenAI settings to run this test")

    client = await create_service_role_client()
    retriever = DocumentRetriever(client)

    results = await retriever.retrieve(
        "How did Services net sales change compared with iPhone net sales?",
        filters=RetrievalFilters(tickers=("AAPL",), filing_types=("10-K",)),
    )

    assert results
    assert all(result.passage.ticker == "AAPL" for result in results)
    assert any("services" in result.passage.content.casefold() for result in results)
