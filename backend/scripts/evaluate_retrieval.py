"""Run focused retrieval probes derived from the client-brief questions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.database.supabase import create_service_role_client
from app.retrieval.models import RetrievalFilters
from app.retrieval.retriever import DocumentRetriever


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    query: str
    filters: RetrievalFilters
    expected_terms: tuple[str, ...]


CASES = (
    EvaluationCase(
        "Apple revenue mix",
        "iPhone Services Mac iPad Wearables net sales revenue mix",
        RetrievalFilters(tickers=("AAPL",), years=(2021, 2022, 2023, 2024, 2025)),
        ("iphone", "services"),
    ),
    EvaluationCase(
        "Amazon segment profitability",
        "AWS North America International net sales operating income margin",
        RetrievalFilters(tickers=("AMZN",), years=(2021, 2022, 2023, 2024, 2025)),
        ("aws", "operating income"),
    ),
    EvaluationCase(
        "NVIDIA Data Center constraints",
        "Data Center demand customer concentration supply constraints",
        RetrievalFilters(tickers=("NVDA",), years=(2021, 2022, 2023, 2024, 2025)),
        ("data center", "supply"),
    ),
    EvaluationCase(
        "Microsoft cloud capacity",
        "Azure AI infrastructure cloud capacity constraints",
        RetrievalFilters(tickers=("MSFT",), years=(2021, 2022, 2023, 2024, 2025)),
        ("azure", "capacity"),
    ),
    EvaluationCase(
        "Alphabet revenue trends",
        "Google Search YouTube ads Google Network Google Cloud revenue",
        RetrievalFilters(tickers=("GOOGL",), years=(2021, 2022, 2023, 2024, 2025)),
        ("google search", "google cloud"),
    ),
    EvaluationCase(
        "Changing risk factors",
        "risk factors artificial intelligence export controls supply chain regulation",
        RetrievalFilters(years=(2021, 2025), filing_types=("10-K",)),
        ("risk", "export"),
    ),
    EvaluationCase(
        "Manufacturing concentration",
        "supplier concentration dependence third-party manufacturing",
        RetrievalFilters(tickers=("AAPL", "NVDA"), filing_types=("10-K",)),
        ("supplier", "manufactur"),
    ),
    EvaluationCase(
        "AI infrastructure investment",
        "capital expenditures purchase commitments AI cloud infrastructure investment",
        RetrievalFilters(tickers=("MSFT", "GOOGL", "AMZN", "NVDA")),
        ("capital expenditure", "purchase commitment"),
    ),
    EvaluationCase(
        "Geographic revenue exposure",
        "geographic net sales revenue United States international markets",
        RetrievalFilters(years=(2025,), filing_types=("10-K",)),
        ("geographic", "international"),
    ),
    EvaluationCase(
        "Generative AI and margins",
        "generative AI effect on operating margin profitability evidence",
        RetrievalFilters(filing_types=("10-K",)),
        ("generative ai", "margin"),
    ),
)


async def main() -> None:
    client = await create_service_role_client()
    retriever = DocumentRetriever(client)
    failed: list[str] = []

    for case in CASES:
        print(f"RUN {case.name}", flush=True)
        results = await retriever.retrieve(case.query, filters=case.filters)
        combined = "\n".join(result.passage.content.casefold() for result in results)
        matched = [term for term in case.expected_terms if term in combined]
        status = "PASS" if matched else "REVIEW"
        if not matched:
            failed.append(case.name)
        print(f"{status} {case.name}: {len(results)} passages")
        for result in results[:3]:
            passage = result.passage
            year = passage.chunk_metadata.get("year", "?")
            print(
                f"  {passage.ticker} {year} {passage.filing_type} "
                f"page {passage.page or '?'} chunk {passage.chunk_index} "
                f"rrf={result.fused_score:.5f}"
            )

    if failed:
        names = ", ".join(failed)
        raise SystemExit(f"retrieval cases requiring review: {names}")


if __name__ == "__main__":
    asyncio.run(main())
