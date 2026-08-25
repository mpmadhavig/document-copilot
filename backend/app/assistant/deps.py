"""Request-scoped dependencies supplied to the document agent."""

import uuid
from dataclasses import dataclass

from app.assistant.evidence import EvidenceStore


@dataclass(frozen=True)
class DocumentAgentDeps:
    user_id: uuid.UUID
    thread_id: uuid.UUID
    evidence: EvidenceStore
