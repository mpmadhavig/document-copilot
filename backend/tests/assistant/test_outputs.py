import pytest
from pydantic import ValidationError

from app.assistant.outputs import GroundedAnswer


def test_answered_output_requires_grounded_statements() -> None:
    with pytest.raises(ValidationError, match="grounded statements"):
        GroundedAnswer(status="answered")


def test_non_answer_output_requires_message_and_forbids_statements() -> None:
    with pytest.raises(ValidationError, match="must contain a message"):
        GroundedAnswer(status="insufficient_evidence")


def test_refusal_accepts_message_without_citations() -> None:
    answer = GroundedAnswer(status="refused", message="I cannot recommend a stock.")

    assert answer.statements == ()
