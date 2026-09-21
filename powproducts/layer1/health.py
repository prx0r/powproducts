"""Collector Health — standardized health state for all Layer 1 collectors.

Every collector must emit this after each run.
This is the operational contract for monitoring.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CollectorHealth:
    """Standardized health state for a collector run."""
    collector_id: str = ""
    source_id: str = ""

    # Run state
    last_attempt: str = ""
    last_success: str = ""
    last_error: str = None

    # Records
    records_seen: int = 0
    records_new: int = 0
    records_changed: int = 0
    records_unchanged: int = 0
    records_invalid: int = 0

    # Bytes
    bytes_fetched: int = 0
    bytes_stored: int = 0

    # Schema
    schema_hash: str = ""
    parser_id: str = ""
    parser_version: str = ""

    # Source health
    source_timestamp: str = None
    source_timestamp_field: str = None
    staleness_hours: float = 0.0

    # Derived health
    status: str = "ok"          # ok | degraded | error | blocked | no_key | terms_blocked
    status_reason: str = None

    # Evidence
    raw_hash: str = ""
    acquisition_url: str = ""
    http_status: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)

    def compute_status(self, expected_min_rows: int = 0, max_staleness_hours: float = 0):
        """Compute status from health fields."""
        if self.last_error:
            self.status = "error"
            self.status_reason = self.last_error
        elif self.http_status == 403:
            self.status = "blocked"
            self.status_reason = "IP blocked by source"
        elif self.records_seen == 0 and expected_min_rows > 0:
            self.status = "degraded"
            self.status_reason = f"0 records (expected >= {expected_min_rows})"
        elif self.staleness_hours > max_staleness_hours > 0:
            self.status = "degraded"
            self.status_reason = f"stale by {self.staleness_hours:.1f}h (max {max_staleness_hours}h)"
        else:
            self.status = "ok"
            self.status_reason = None

    @staticmethod
    def schema_hash_from_dict(schema: dict) -> str:
        """Compute a hash of a schema dict."""
        return hashlib.sha256(
            json.dumps(schema, sort_keys=True, default=str).encode()
        ).hexdigest()[:8]


def health_from_run_result(collector_id: str, source_id: str, result) -> CollectorHealth:
    """Create CollectorHealth from a BaseCollector run result."""
    # records_seen = total records processed (not raw fetches)
    records_seen = result.records_new + result.records_changed + result.records_unchanged + result.records_invalid
    health = CollectorHealth(
        collector_id=collector_id,
        source_id=source_id,
        last_attempt=result.finished_at or datetime.now(timezone.utc).isoformat(),
        last_success=result.finished_at if not result.errors else "",
        last_error=json.dumps(result.errors) if result.errors else None,
        records_seen=records_seen,
        records_new=result.records_new,
        records_changed=result.records_changed,
        records_unchanged=result.records_unchanged,
        records_invalid=result.records_invalid,
    )
    health.compute_status()
    return health
