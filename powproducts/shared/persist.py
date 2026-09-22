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
from typing import Optional

from powproducts.shared.db import SCHEMA, get_db_path, _enable_foreign_keys


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
    sha256: str = ""
    acquisition_id: int = 0


def get_db():
    """Get database connection with foreign keys enabled."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    _enable_foreign_keys(conn)
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
    if cursor.rowcount == 0:
        inserted = False
    conn.commit()
    conn.close()
    return RawStoreResult(sha256=sha256, inserted=inserted, path=str(raw_path))


def store_acquisition(source_id: str, dataset: str, url: str, http_status: int,
                      sha256: str, content_type: str = '', etag: str = '',
                      last_modified: str = '', content_length: int = 0,
                      final_url: str = '', request_params: str = '') -> int:
    """Store acquisition receipt. Always appends. Returns acquisition_id."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO raw_acquisition "
        "(source_id, dataset, retrieved_at, request_url, final_url, http_status, etag, last_modified, "
        "content_type, content_length, sha256, request_params) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, dataset, datetime.now(timezone.utc).isoformat(),
         url, final_url, http_status, etag, last_modified, content_type, content_length, sha256,
         request_params)
    )
    acquisition_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return acquisition_id


def insert_source_record(source_id: str, dataset: str, native_id: str,
                          normalized: dict, raw_hash: str, parser_id: str,
                          parser_version: str = '1.0.0',
                          event_time: str = '',
                          acquisition_id: int = None) -> InsertResult:
    """Insert a source record. Returns InsertResult with status.

    Links to actual acquisition evidence when provided.
    """
    record_id = f'{source_id}:{native_id}'
    payload_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()

    conn = get_db()

    existing = conn.execute(
        "SELECT source_record_id, payload_hash FROM source_record "
        "WHERE source_record_id = ? OR source_record_id LIKE ? "
        "ORDER BY retrieved_at DESC LIMIT 1",
        (record_id, f'{record_id}:v%')
    ).fetchone()

    if existing:
        if existing[1] == payload_hash:
            conn.close()
            return InsertResult(inserted=False, record_id=existing[0], duplicate_of=existing[0])
        else:
            version_id = f'{record_id}:v{payload_hash[:12]}'
            try:
                conn.execute(
                    "INSERT INTO source_record "
                    "(source_record_id, source_id, dataset, source_native_id, event_time, "
                    "retrieved_at, normalized_json, payload_hash, raw_payload_hash, "
                    "acquisition_id, parser_id, parser_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (version_id, source_id, dataset, native_id,
                     event_time or normalized.get('event_time', ''),
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps(normalized, default=str), payload_hash,
                     raw_hash, acquisition_id, parser_id, parser_version)
                )
                conn.commit()
                conn.close()
                return InsertResult(inserted=True, record_id=version_id, duplicate_of=record_id)
            except sqlite3.IntegrityError:
                conn.close()
                return InsertResult(inserted=False, record_id=version_id, duplicate_of=record_id)

    try:
        conn.execute(
            "INSERT INTO source_record "
            "(source_record_id, source_id, dataset, source_native_id, event_time, "
            "retrieved_at, normalized_json, payload_hash, raw_payload_hash, "
            "acquisition_id, parser_id, parser_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, source_id, dataset, native_id,
             event_time or normalized.get('event_time', ''),
             datetime.now(timezone.utc).isoformat(),
             json.dumps(normalized, default=str), payload_hash,
             raw_hash, acquisition_id, parser_id, parser_version)
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
            requests_attempted: int = 0, requests_200: int = 0,
            requests_403: int = 0, requests_404: int = 0,
            requests_429: int = 0, requests_failed: int = 0,
            error: str = None, started_at: str = '', finished_at: str = ''):
    """Log a collector run."""
    conn = get_db()
    conn.execute(
        "INSERT INTO collector_run "
        "(source_id, started_at, finished_at, status, raw_fetched, raw_new, "
        "requests_attempted, requests_200, requests_403, requests_404, requests_429, requests_failed, "
        "source_records_new, source_records_updated, source_records_invalid, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, started_at or datetime.now(timezone.utc).isoformat(),
         finished_at or datetime.now(timezone.utc).isoformat(),
         status, raw_fetched, raw_new,
         requests_attempted, requests_200, requests_403, requests_404, requests_429, requests_failed,
         records_new, records_changed, records_invalid, error)
    )
    conn.commit()
    conn.close()


def store_market_observation(source_record_id: str, observed_at: str,
                              price: float = None, currency: str = 'GBP',
                              bid_price: float = None, exchange_price: float = None,
                              stock: str = None, availability: str = None,
                              condition: str = None, market: str = '',
                              observation_type: str = 'price',
                              price_type: str = None,
                              acquisition_id: int = None,
                              collector_run_id: int = None,
                              source_native_id: str = '',
                              extra_json: str = ''):
    """Store a market observation snapshot. Always appends."""
    conn = get_db()
    conn.execute(
        "INSERT INTO market_observation "
        "(source_record_id, acquisition_id, collector_run_id, source_native_id, "
        "observation_type, price_type, observed_at, price, bid_price, exchange_price, currency, "
        "stock, availability, condition, market, extra_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
         (source_record_id, acquisition_id, collector_run_id, source_native_id,
         observation_type, price_type, observed_at, price, bid_price, exchange_price, currency,
         stock, availability, condition, market, extra_json)
    )
    conn.commit()
    conn.close()


def persist_health(source_id: str, health: dict):
    """Persist collector health state after every run."""
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


def check_source_rights(source_id: str) -> dict:
    """Check if a source is allowed to run in production."""
    conn = get_db()
    row = conn.execute(
        "SELECT status FROM source_rights WHERE source_id=?", (source_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return {'allowed': False, 'status': 'not_registered',
                'reason': f'Source {source_id} not in source_rights table'}
    status = row[0]
    if status in ('open', 'approved'):
        return {'allowed': True, 'status': status}
    return {'allowed': False, 'status': status,
            'reason': f'Source status is {status}'}


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
                            variant_manufacturer_id: str = '',
                            manufacturer_sku: str = '', mpn: str = '',
                            gtin: str = '', ean: str = '', upc: str = '',
                            revision: str = '', capacity: str = '',
                            memory: str = '', packaging: str = '', region: str = '',
                            external_ids: dict = None):
    """Insert or update a product variant."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO product_variant (variant_id, product_id, variant_manufacturer_id, "
        "manufacturer_sku, mpn, gtin, ean, upc, revision, capacity, memory, packaging, region, "
        "external_ids_json, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(variant_id) DO UPDATE SET "
        "last_seen_at=excluded.last_seen_at",
        (variant_id, product_id, variant_manufacturer_id,
         manufacturer_sku, mpn,
         gtin, ean, upc, revision, capacity, memory, packaging, region,
         json.dumps(external_ids or {}), now, now)
    )
    conn.commit()
    conn.close()


def insert_product_identifier(entity_id: str, namespace: str, value: str,
                               source_record_id: str = '', confidence: float = 1.0):
    """Insert a product identifier. UNIQUE on (namespace, normalized_value, entity_id)."""
    normalized = value.strip().upper() if value else ''
    if not normalized or not entity_id:
        return
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO product_identifier (namespace, normalized_value, entity_id, "
            "source_record_id, valid_from, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (namespace, normalized, entity_id, source_record_id, now, confidence)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already exists
    finally:
        conn.close()


def insert_product_relation(src_entity_id: str, dst_entity_id: str,
                             relation_type: str,
                             source_record_id: str = '',
                             truth_class: str = 'declared',
                             confidence: float = 1.0,
                             quantity: float = None,
                             unit: str = '',
                             evidence_json: str = '') -> str:
    """Insert a product relation edge + assertion. Preserves all evidence."""
    raw = f'{src_entity_id}:{dst_entity_id}:{relation_type}'
    relation_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Upsert the canonical edge
    try:
        conn.execute(
            "INSERT INTO product_relation (relation_id, src_entity_id, dst_entity_id, "
            "relation_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (relation_id, src_entity_id, dst_entity_id, relation_type, now)
        )
    except sqlite3.IntegrityError:
        pass  # Edge already exists

    # Add the evidence assertion
    try:
        conn.execute(
            "INSERT INTO product_relation_assertion "
            "(relation_id, source_record_id, truth_class, confidence, quantity, unit, "
            "evidence_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (relation_id, source_record_id, truth_class, confidence,
             quantity, unit, evidence_json, now)
        )
    except sqlite3.IntegrityError:
        pass  # Same source already asserted this

    conn.commit()
    conn.close()
    return relation_id


def insert_spec_observation(entity_id: str, spec_key: str, value: str,
                             source_id: str = '', truth_class: str = 'declared',
                             numeric_value: float = None, unit: str = '',
                             source_record_id: str = '', parser_version: str = '1.0.0'):
    """Insert a spec observation. Content-addressed ID."""
    raw = f'{entity_id}:{spec_key}:{value}:{source_id}'
    spec_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
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
