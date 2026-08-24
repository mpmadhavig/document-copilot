"""Typed retrieval inputs and outputs."""

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RetrievalFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    tickers: tuple[str, ...] | None = None
    years: tuple[int, ...] | None = None
    filing_types: tuple[str, ...] | None = None

    @field_validator("tickers", "filing_types")
    @classmethod
    def normalize_text_filters(
        cls, values: tuple[str, ...] | None
    ) -> tuple[str, ...] | None:
        if values is None:
            return None
        normalized = tuple(value.strip().upper() for value in values if value.strip())
        return normalized or None

    @field_validator("years")
    @classmethod
    def validate_years(cls, years: tuple[int, ...] | None) -> tuple[int, ...] | None:
        if years is None:
            return None
        if any(year < 1900 or year > 2100 for year in years):
            raise ValueError("years must be between 1900 and 2100")
        return years or None


class SourcePassage(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    section: str | None
    page: int | None
    chunk_metadata: dict[str, Any]
    accession_number: str
    ticker: str
    company_name: str
    filing_type: str
    filing_date: date
    source_url: str
    document_metadata: dict[str, Any]


class SearchHit(SourcePassage):
    score: float


class NeighborRow(SourcePassage):
    seed_chunk_id: uuid.UUID


class RankedPassage(BaseModel):
    model_config = ConfigDict(frozen=True)

    passage: SourcePassage
    fused_score: float = Field(gt=0)
    semantic_rank: int | None = Field(default=None, ge=1)
    lexical_rank: int | None = Field(default=None, ge=1)
    semantic_score: float | None = None
    lexical_score: float | None = None
    neighbors: tuple[SourcePassage, ...] = ()
