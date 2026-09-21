"""Persistence — shared functions for all collectors.

Every collector uses these. No hand-written SQL inserts.
Returns InsertResult so callers know what happened.

Schema authority: shared/db.py is the single source of truth.
DB path authority: shared/db.py::get_db_path() is the single source of truth.
"""

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from powproducts.shared.db import SCHEMA, get_db_path


@dataclass
class InsertResult:
    """Result of inserting a record."""
    inserted: bool
    record_id: str
    duplicate_of: str = ""
    error: str = ""


@dataclass
class RawStoreResult:
    """Result of storing raw content."""
    sha256: str
    inserted: bool
    path: str


@dataclass
class Acquisition:
    """Result of an HTTP acquisition."""
    content: bytes
    requested_url: str
    final_url: str = ""
    status: int = 0
    content_type: str = ""
    etag: str = ""
    last_modified: str = ""
    content_length: int = 0
    error: str = ""


def get_db():
    """Get database connection. Creates tables from canonical schema if needed."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def store_raw(content: bytes, source_id: str, content_type: str = 'application/octet-stream') -> RawStoreResult:
    """Store raw content immutably. Returns RawStoreResult. Idempotent."""
    sha256 = hashlib.sha256(content).hexdigest()
    raw_dir = get_db_path().parent / 'raw' / source_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f'{sha256}.gz'

    inserted = not raw_path.exists()
    if inserted:
        import gzip
        with gzip.open(raw_path, 'wb') as f:
            f.write(content)

    conn = get_db()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO raw_blob (sha256, source_id, content_type, content_length, storage_path) "
        "VALUES (?, ?, ?, ?, ?)",
        (sha256, source_id, content_type, len(content), str(raw_path))
    )
    # rowcount=1 means inserted, 0 means already existed
    if cursor.rowcount == 0:
        inserted = False
    conn.commit()
    conn.close()
    return RawStoreResult(sha256=sha256, inserted=inserted, path=str(raw_path))


def store_acquisition(source_id: str, dataset: str, url: str, http_status: int,
                      sha256: str, content_type: str = '', etag: str = '',
                      last_modified: str = '', content_length: int = 0,
                      final_url: str = '', request_params: str = ''):
    """Store acquisition receipt. Always appends (same blob, different fetch time)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO raw_acquisition "
        "(source_id, dataset, retrieved_at, request_url, final_url, http_status, etag, last_modified, "
        "content_type, content_length, sha256, request_params) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, dataset, datetime.now(timezone.utc).isoformat(),
         url, final_url, http_status, etag, last_modified, content_type, content_length, sha256,
         request_params)
    )
    conn.commit()
    conn.close()


def insert_source_record(source_id: str, dataset: str, native_id: str,
                          normalized: dict, raw_hash: str, parser_id: str,
                          parser_version: str = '1.0.0',
                          event_time: str = '') -> InsertResult:
    """Insert a source record. Returns InsertResult with status.

    Uses INSERT OR IGNORE for idempotency.
    Detects changes by comparing payload_hash against the LATEST version.
    Version IDs use content-addressed payload_hash (no timestamp collisions).
    """
    record_id = f'{source_id}:{native_id}'
    payload_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()

    conn = get_db()

    # Find the LATEST version (by time, not by lexicographic hash ID)
    existing = conn.execute(
        "SELECT source_record_id, payload_hash FROM source_record "
        "WHERE source_record_id = ? OR source_record_id LIKE ? "
        "ORDER BY retrieved_at DESC LIMIT 1",
        (record_id, f'{record_id}:v%')
    ).fetchone()

    if existing:
        if existing[1] == payload_hash:
            # Unchanged from latest version
            conn.close()
            return InsertResult(inserted=False, record_id=existing[0], duplicate_of=existing[0])
        else:
            # Changed — create version with content-addressed ID
            version_id = f'{record_id}:v{payload_hash[:12]}'
            try:
                conn.execute(
                    "INSERT INTO source_record "
                    "(source_record_id, source_id, dataset, source_native_id, event_time, "
                    "retrieved_at, normalized_json, payload_hash, raw_payload_hash, "
                    "parser_id, parser_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (version_id, source_id, dataset, native_id,
                     event_time or normalized.get('event_time', ''),
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps(normalized, default=str), payload_hash,
                     raw_hash, parser_id, parser_version)
                )
                conn.commit()
                conn.close()
                return InsertResult(inserted=True, record_id=version_id, duplicate_of=record_id)
            except sqlite3.IntegrityError:
                # Rare: same payload_hash version already exists
                conn.close()
                return InsertResult(inserted=False, record_id=version_id, duplicate_of=record_id)

    # New record
    try:
        conn.execute(
            "INSERT INTO source_record "
            "(source_record_id, source_id, dataset, source_native_id, event_time, "
            "retrieved_at, normalized_json, payload_hash, raw_payload_hash, "
            "parser_id, parser_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, source_id, dataset, native_id,
             event_time or normalized.get('event_time', ''),
             datetime.now(timezone.utc).isoformat(),
             json.dumps(normalized, default=str), payload_hash,
             raw_hash, parser_id, parser_version)
        )
        conn.commit()
        conn.close()
        return InsertResult(inserted=True, record_id=record_id)
    except sqlite3.IntegrityError:
        conn.close()
        return InsertResult(inserted=False, record_id=record_id, duplicate_of=record_id)


def get_cursor(source_id: str, dataset: str) -> str:
    """Get cursor value."""
    conn = get_db()
    row = conn.execute(
        "SELECT cursor_value FROM source_cursor WHERE source_id=? AND dataset=?",
        (source_id, dataset)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def set_cursor(source_id: str, dataset: str, cursor_value: str):
    """Set cursor value."""
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO source_cursor (source_id, dataset, cursor_type, cursor_value, updated_at) "
        "VALUES (?, ?, 'offset', ?, ?)",
        (source_id, dataset, cursor_value, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def log_run(source_id: str, status: str, raw_fetched: int = 0, raw_new: int = 0,
            records_new: int = 0, records_unchanged: int = 0, records_changed: int = 0,
            records_invalid: int = 0,
            error: str = None, started_at: str = '', finished_at: str = ''):
    """Log a collector run."""
    conn = get_db()
    conn.execute(
        "INSERT INTO collector_run "
        "(source_id, started_at, finished_at, status, raw_fetched, raw_new, "
        "source_records_new, source_records_updated, source_records_invalid, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, started_at or datetime.now(timezone.utc).isoformat(),
         finished_at or datetime.now(timezone.utc).isoformat(),
         status, raw_fetched, raw_new, records_new, records_changed, records_invalid, error)
    )
    conn.commit()
    conn.close()


def store_market_observation(source_record_id: str, observed_at: str,
                              price: float = None, currency: str = 'GBP',
                              bid_price: float = None, exchange_price: float = None,
                              stock: str = None, availability: str = None,
                              condition: str = None, market: str = '',
                              observation_type: str = 'price',
                              acquisition_id: int = None,
                              collector_run_id: int = None,
                              source_native_id: str = '',
                              extra_json: str = ''):
    """Store a market observation snapshot. Always appends — even unchanged prices matter.

    This captures the time dimension: duration at price, availability duration,
    listing visibility, stock persistence.
    """
    conn = get_db()
    conn.execute(
        "INSERT INTO market_observation "
        "(source_record_id, acquisition_id, collector_run_id, source_native_id, "
        "observation_type, observed_at, price, bid_price, exchange_price, currency, "
        "stock, availability, condition, market, extra_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
         (source_record_id, acquisition_id, collector_run_id, source_native_id,
         observation_type, observed_at, price, bid_price, exchange_price, currency,
         stock, availability, condition, market, extra_json)
    )
    conn.commit()
    conn.close()


def persist_health(source_id: str, health: dict):
    """Persist collector health state after every run.

    health dict should match CollectorHealth.to_dict() output.
    """
    conn = get_db()
    conn.execute(
        "INSERT INTO source_health "
        "(source_id, last_attempt, last_success, last_error, "
        "records_seen, records_new, records_changed, records_unchanged, records_invalid, "
        "status, status_reason, computed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id,
         health.get('last_attempt', ''),
         health.get('last_success', ''),
         health.get('last_error'),
         health.get('records_seen', 0),
         health.get('records_new', 0),
         health.get('records_changed', 0),
         health.get('records_unchanged', 0),
         health.get('records_invalid', 0),
         health.get('status', 'unknown'),
         health.get('status_reason'),
         datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def upsert_manufacturer(manufacturer_id: str, canonical_name: str,
                         aliases: list = None, country_code: str = '',
                         website_domain: str = '', external_ids: dict = None):
    """Insert or update a manufacturer."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO manufacturer (manufacturer_id, canonical_name, aliases_json, "
        "country_code, website_domain, external_ids_json, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(manufacturer_id) DO UPDATE SET "
        "canonical_name=excluded.canonical_name, last_seen_at=excluded.last_seen_at",
        (manufacturer_id, canonical_name,
         json.dumps(aliases or []), country_code, website_domain,
         json.dumps(external_ids or {}), now, now)
    )
    conn.commit()
    conn.close()


def upsert_product_model(product_id: str, manufacturer_id: str, canonical_name: str,
                          family_id: str = '', model_number: str = '',
                          product_class: str = '', release_date: str = '',
                          discontinued_date: str = '', declared_status: str = '',
                          country_of_origin: str = '', external_ids: dict = None):
    """Insert or update a product model."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO product_model (product_id, manufacturer_id, family_id, canonical_name, "
        "model_number, product_class, release_date, discontinued_date, declared_status, "
        "country_of_origin, external_ids_json, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(product_id) DO UPDATE SET "
        "canonical_name=excluded.canonical_name, last_seen_at=excluded.last_seen_at",
        (product_id, manufacturer_id, family_id, canonical_name,
         model_number, product_class, release_date, discontinued_date,
         declared_status, country_of_origin, json.dumps(external_ids or {}), now, now)
    )
    conn.commit()
    conn.close()


def upsert_product_variant(variant_id: str, product_id: str,
                            manufacturer_sku: str = '', mpn: str = '',
                            gtin: str = '', ean: str = '', upc: str = '',
                            revision: str = '', capacity: str = '',
                            memory: str = '', packaging: str = '', region: str = '',
                            external_ids: dict = None):
    """Insert or update a product variant."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO product_variant (variant_id, product_id, manufacturer_sku, mpn, "
        "gtin, ean, upc, revision, capacity, memory, packaging, region, "
        "external_ids_json, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(variant_id) DO UPDATE SET "
        "last_seen_at=excluded.last_seen_at",
        (variant_id, product_id, manufacturer_sku, mpn,
         gtin, ean, upc, revision, capacity, memory, packaging, region,
         json.dumps(external_ids or {}), now, now)
    )
    conn.commit()
    conn.close()


def insert_product_identifier(entity_id: str, namespace: str, value: str,
                               source_id: str = '', confidence: float = 1.0):
    """Insert a product identifier. Idempotent on (entity_id, namespace, value)."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO product_identifier (entity_id, namespace, value, source_id, "
        "valid_from, confidence) VALUES (?, ?, ?, ?, ?, ?)",
        (entity_id, namespace, value, source_id, now, confidence)
    )
    conn.commit()
    conn.close()


def insert_product_relation(src_entity_id: str, dst_entity_id: str,
                             relation_type: str, truth_class: str = 'declared',
                             confidence: float = 1.0, source_record_id: str = '',
                             evidence_json: str = '', quantity: float = None,
                             unit: str = ''):
    """Insert a product relation. Uses content-addressed ID."""
    import hashlib as hl
    raw = f'{src_entity_id}:{dst_entity_id}:{relation_type}:{truth_class}'
    relation_id = hl.sha256(raw.encode()).hexdigest()[:16]
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO product_relation (relation_id, src_entity_id, dst_entity_id, "
        "relation_type, quantity, unit, truth_class, confidence, source_record_id, "
        "evidence_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (relation_id, src_entity_id, dst_entity_id, relation_type,
         quantity, unit, truth_class, confidence, source_record_id,
         evidence_json, now)
    )
    conn.commit()
    conn.close()
    return relation_id


def insert_spec_observation(entity_id: str, spec_key: str, value: str,
                             source_id: str = '', truth_class: str = 'declared',
                             numeric_value: float = None, unit: str = '',
                             source_record_id: str = '', parser_version: str = '1.0.0'):
    """Insert a spec observation. Content-addressed ID."""
    import hashlib as hl
    raw = f'{entity_id}:{spec_key}:{value}:{source_id}'
    spec_id = hl.sha256(raw.encode()).hexdigest()[:16]
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO product_spec_observation (spec_observation_id, entity_id, "
        "spec_key, value, numeric_value, unit, source_id, source_record_id, "
        "truth_class, observed_at, parser_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (spec_id, entity_id, spec_key, value, numeric_value, unit,
         source_id, source_record_id, truth_class, now, parser_version)
    )
    conn.commit()
    conn.close()
    return spec_id
