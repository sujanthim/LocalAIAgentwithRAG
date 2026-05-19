"""
Structured audit logging for HIPAA / SOC 2 compliance.

Every RAG query is logged with: who queried, what role they had,
what they asked, and which source documents were returned.

Logs are written as newline-delimited JSON to audit.log.
In production, ship these to a SIEM (Splunk, Datadog, CloudWatch Logs).
"""

import json
import logging
import os
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Logger setup — append-only JSON lines to audit.log
# ---------------------------------------------------------------------------
_handler = logging.FileHandler("audit.log", mode="a", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(message)s"))

_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)
_audit_logger.addHandler(_handler)
_audit_logger.propagate = False  # don't leak into root logger


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_query(user_id: str, role: str, query: str, retrieved_docs: list) -> None:
    """Log a RAG query and the documents that were retrieved."""
    entry = {
        "event": "rag_query",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "role": role,
        "query": query,
        "retrieved_sources": [
            doc.metadata.get("source", "unknown") for doc in retrieved_docs
        ],
        "doc_count": len(retrieved_docs),
    }
    _audit_logger.info(json.dumps(entry))


def log_login(user_id: str, role: str, email: str) -> None:
    """Log a successful authentication event."""
    entry = {
        "event": "login",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "role": role,
        "email": email,
    }
    _audit_logger.info(json.dumps(entry))


def log_auth_failure(reason: str) -> None:
    """Log a failed authentication attempt."""
    entry = {
        "event": "auth_failure",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    }
    _audit_logger.info(json.dumps(entry))
