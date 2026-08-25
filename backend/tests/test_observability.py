import json
import logging

import structlog

from app.observability import configure_logging, new_error_reference


def test_error_references_are_safe_and_compact() -> None:
    reference = new_error_reference()

    assert reference.startswith("be-")
    assert len(reference) == 15


def test_configured_logger_writes_structured_error(tmp_path) -> None:
    log_path = tmp_path / "backend.log"
    configure_logging(log_path, "INFO")

    structlog.get_logger("test").error(
        "test_failure", error_reference="be-test-reference"
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["event"] == "test_failure"
    assert entry["error_reference"] == "be-test-reference"
