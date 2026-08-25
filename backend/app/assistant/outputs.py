"""Structured output contract for grounded answers."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID = Field(
        description="Exact chunk UUID returned by an evidence tool."
    )
    quote: str = Field(
        min_length=1,
        max_length=1200,
        description=(
            "Short, contiguous, verbatim substring copied from the cited chunk "
            "content; never paraphrased, combined, or edited."
        ),
    )


class GroundedStatement(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=4000)
    citations: tuple[EvidenceCitation, ...] = Field(min_length=1, max_length=8)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["answered", "insufficient_evidence", "refused"]
    statements: tuple[GroundedStatement, ...] = Field(default=(), max_length=20)
    message: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_status_shape(self) -> "GroundedAnswer":
        if self.status == "answered":
            if not self.statements:
                raise ValueError("answered output must contain grounded statements")
            if self.message is not None:
                raise ValueError("answered output must not contain a separate message")
        else:
            if self.statements:
                raise ValueError(f"{self.status} output must not contain statements")
            if self.message is None or not self.message.strip():
                raise ValueError(f"{self.status} output must contain a message")
        return self
