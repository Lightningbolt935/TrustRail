"""
Append-Only Audit Log System
Every gate decision, score update, and system failure is immutably recorded.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    log_id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: str
    event_type: str  # "gate_decision" | "score_update" | "system_failure" | "retry"
    decision: str    # "allowed" | "blocked" | "error"
    reason: str      # Human-readable rule explanation
    score_before: int
    score_after: int
    tier_before: str
    tier_after: str
    txn_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    def __init__(self, log_filepath: Optional[str] = None):
        self._entries: List[AuditLogEntry] = []
        if log_filepath is None:
            # Default to storage in backend directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.log_filepath = os.path.join(base_dir, "audit_trail.jsonl")
        else:
            self.log_filepath = log_filepath

        # Load existing entries if present
        self._load_existing_logs()

    def _load_existing_logs(self):
        if os.path.exists(self.log_filepath):
            try:
                with open(self.log_filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry_dict = json.loads(line)
                            self._entries.append(AuditLogEntry(**entry_dict))
            except Exception:
                pass

    def log_event(self, entry: AuditLogEntry) -> AuditLogEntry:
        """Append event to in-memory list and write to JSONL file."""
        self._entries.append(entry)
        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            print(f"[AuditLogger Error] Failed to write log to disk: {e}")
        return entry

    def get_entries(self, agent_id: Optional[str] = None, limit: int = 100) -> List[AuditLogEntry]:
        """Fetch audit log entries, newest first."""
        filtered = self._entries
        if agent_id:
            filtered = [e for e in filtered if e.agent_id == agent_id]
        return list(reversed(filtered))[:limit]

    def get_agent_score_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Extract score progression over time for charting."""
        history = []
        agent_entries = [e for e in self._entries if e.agent_id == agent_id]
        for e in agent_entries:
            history.append({
                "timestamp": e.timestamp,
                "score_before": e.score_before,
                "score_after": e.score_after,
                "tier": e.tier_after,
                "event_type": e.event_type,
                "decision": e.decision,
                "reason": e.reason,
            })
        return history

    def clear(self):
        """Clear logs (for test resets)."""
        self._entries.clear()
        if os.path.exists(self.log_filepath):
            try:
                os.remove(self.log_filepath)
            except Exception:
                pass


# Global singleton audit logger
audit_logger = AuditLogger()
