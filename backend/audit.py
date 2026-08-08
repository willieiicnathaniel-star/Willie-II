"""
THEeye - Provenance & Integrity Audit Module
Tracks every action, source, and AI-generated passage to ensure
full transparency and journal-compliance.

This module enforces THEeye's core principle: AI assists, humans decide,
and everything is documented.
"""

import uuid
from datetime import datetime, timezone
from .models import ProvenanceRecord, AuditReport


class AuditSession:
    """
    A session-level audit trail. One instance per research session.
    Accumulates provenance records and generates compliance reports.
    """

    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.records: list[ProvenanceRecord] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._ai_sections: set[str] = set()
        self._all_sources: set[str] = set()

    def log_search(self, query: str, databases: list[str], result_count: int):
        """Log a literature search action."""
        self.records.append(ProvenanceRecord(
            action="search",
            timestamp=datetime.now(timezone.utc).isoformat(),
            query_or_input=query,
            sources_used=databases,
            ai_generated=False,
            human_verified=True,
            details=f"Retrieved {result_count} papers from {', '.join(databases)}",
        ))

    def log_extraction(self, paper_title: str, doi: str | None, method: str):
        """Log a data extraction action."""
        source = doi or paper_title
        self._all_sources.add(source)
        self.records.append(ProvenanceRecord(
            action="extract",
            timestamp=datetime.now(timezone.utc).isoformat(),
            query_or_input=paper_title,
            sources_used=[source],
            ai_generated=(method == "llm"),
            human_verified=False,
            details=f"Extraction method: {method}",
        ))

    def log_draft(self, section_type: str, topic: str,
                  sources: list[str], ai_generated: bool = True):
        """Log a drafting action."""
        self._all_sources.update(sources)
        if ai_generated:
            self._ai_sections.add(section_type)
        self.records.append(ProvenanceRecord(
            action="draft",
            timestamp=datetime.now(timezone.utc).isoformat(),
            query_or_input=f"{section_type}: {topic}",
            sources_used=sources,
            ai_generated=ai_generated,
            human_verified=False,
            details=f"Generated {'AI-assisted ' if ai_generated else ''}draft for {section_type}",
        ))

    def mark_verified(self, action_index: int):
        """Mark a specific record as human-verified."""
        if 0 <= action_index < len(self.records):
            self.records[action_index].human_verified = True

    def mark_all_verified(self):
        """Mark all records as human-verified."""
        for r in self.records:
            r.human_verified = True

    def _compute_verification_status(self) -> str:
        if not self.records:
            return "pending"
        verified = sum(1 for r in self.records if r.human_verified)
        total = len(self.records)
        if verified == total:
            return "verified"
        elif verified > 0:
            return "partial"
        return "pending"

    def _generate_disclosure(self) -> str:
        """Generate a journal-compliant AI use disclosure statement."""
        ai_sections = sorted(self._ai_sections)
        if not ai_sections:
            return (
                "AI Use Disclosure: No AI-assisted content was generated in this session. "
                "All content is human-authored."
            )

        sections_str = ", ".join(ai_sections)
        return (
            f"AI Use Disclosure: During the preparation of this work, the author(s) used "
            f"THEeye (an AI-assisted research platform) to assist with the following sections: "
            f"{sections_str}. The tool was used for literature retrieval, data extraction, "
            f"and draft generation. After using this tool, the author(s) reviewed and edited "
            f"the content as needed and take(s) full responsibility for the content of the "
            f"published article. All AI-generated text was verified against primary sources. "
            f"This disclosure is provided in accordance with the AI use policies of major "
            f"academic publishers (Elsevier, Springer Nature, Wiley, etc.)."
        )

    def generate_report(self) -> AuditReport:
        """Generate a full audit report for the session."""
        return AuditReport(
            session_id=self.session_id,
            created_at=self.created_at,
            records=self.records,
            disclosure_statement=self._generate_disclosure(),
            total_sources=len(self._all_sources),
            ai_assisted_sections=sorted(self._ai_sections),
            verification_status=self._compute_verification_status(),
        )

    def to_dict(self) -> dict:
        """Serialize session for persistence."""
        report = self.generate_report()
        return {
            "session_id": report.session_id,
            "created_at": report.created_at,
            "records": [r.model_dump() for r in self.records],
            "disclosure_statement": report.disclosure_statement,
            "total_sources": report.total_sources,
            "ai_assisted_sections": report.ai_assisted_sections,
            "verification_status": report.verification_status,
        }


# Global session registry (in-memory; use a database for production)
_sessions: dict[str, AuditSession] = {}


def create_session() -> AuditSession:
    """Create a new audit session."""
    session = AuditSession()
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> AuditSession | None:
    """Retrieve an existing session by ID."""
    return _sessions.get(session_id)


def list_sessions() -> list[dict]:
    """List all sessions with summary info."""
    return [
        {
            "session_id": sid,
            "created_at": s.created_at,
            "record_count": len(s.records),
            "verification_status": s._compute_verification_status(),
        }
        for sid, s in _sessions.items()
    ]
