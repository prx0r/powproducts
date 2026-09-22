"""Database — canonical schema for PowProducts.

Three layers: RAW → source_record → canonical entities/observations.
All writes are append-only. Observations are immutable.

Single authority for DB path: get_db_path() respects POWPRODUCTS_DB env var.
"""

import os
import sqlite3
from pathlib import Path


SCHEMA_VERSION = 2


def get_db_path() -> Path:
    """Single source of truth for database path."""
    return Path(os.environ.get('POWPRODUCTS_DB', str(Path(__file__).parent.parent.parent / 'warehouse' / 'powproducts.db')))


SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Layer A: RAW blobs (content-addressed)
CREATE TABLE IF NOT EXISTS raw_blob (
    sha256 TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    content_type TEXT,
    content_length INTEGER,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Layer A: Raw acquisition receipts (one per HTTP response)
CREATE TABLE IF NOT EXISTS raw_acquisition (
    acquisition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    request_url TEXT,
    final_url TEXT,
    http_status INTEGER,
    etag TEXT,
    last_modified TEXT,
    content_type TEXT,
    content_length INTEGER,
    sha256 TEXT NOT NULL,
    request_params TEXT,
    FOREIGN KEY (sha256) REFERENCES raw_blob(sha256)
);

-- Layer B: Source records (normalized from raw)
CREATE TABLE IF NOT EXISTS source_record (
    source_record_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    source_native_id TEXT,
    event_time TEXT,
    retrieved_at TEXT NOT NULL,
    normalized_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    raw_payload_hash TEXT NOT NULL,
    acquisition_id INTEGER,
    parser_id TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    valid INTEGER NOT NULL DEFAULT 1,
    validation_errors_json TEXT,
    FOREIGN KEY (acquisition_id) REFERENCES raw_acquisition(acquisition_id)
);

-- Layer C: Canonical observations
CREATE TABLE IF NOT EXISTS observation (
    observation_id TEXT PRIMARY KEY,
    source_record_id TEXT,
    source_id TEXT NOT NULL,
    entity_id TEXT,
    metric TEXT NOT NULL,
    value TEXT,
    value_type TEXT DEFAULT 'text',
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    truth_class TEXT DEFAULT 'observed',
    parent_observation_ids TEXT,
    raw_payload_hash TEXT,
    FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
);

-- Source cursors (for resumable backfill)
CREATE TABLE IF NOT EXISTS source_cursor (
    source_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    cursor_type TEXT,
    cursor_value TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_id, dataset)
);

-- Collector run history
CREATE TABLE IF NOT EXISTS collector_run (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    status TEXT DEFAULT 'running',
    mode TEXT DEFAULT 'incremental',
    raw_fetched INTEGER DEFAULT 0,
    raw_new INTEGER DEFAULT 0,
    requests_attempted INTEGER DEFAULT 0,
    requests_200 INTEGER DEFAULT 0,
    requests_403 INTEGER DEFAULT 0,
    requests_404 INTEGER DEFAULT 0,
    requests_429 INTEGER DEFAULT 0,
    requests_failed INTEGER DEFAULT 0,
    source_records_new INTEGER DEFAULT 0,
    source_records_updated INTEGER DEFAULT 0,
    source_records_invalid INTEGER DEFAULT 0,
    observations_new INTEGER DEFAULT 0,
    error TEXT,
    duration_seconds REAL
);

-- Market observations (ephemeral time-series for marketplace tapes)
CREATE TABLE IF NOT EXISTS market_observation (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id TEXT NOT NULL,
    acquisition_id INTEGER,
    collector_run_id INTEGER,
    source_native_id TEXT,
    observation_type TEXT DEFAULT 'price',
    price_type TEXT,
    observed_at TEXT NOT NULL,
    price REAL,
    bid_price REAL,
    exchange_price REAL,
    currency TEXT DEFAULT 'GBP',
    stock TEXT,
    availability TEXT,
    condition TEXT,
    market TEXT,
    extra_json TEXT,
    FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id),
    FOREIGN KEY (acquisition_id) REFERENCES raw_acquisition(acquisition_id),
    FOREIGN KEY (collector_run_id) REFERENCES collector_run(run_id)
);

-- Market events (deterministic state transitions)
CREATE TABLE IF NOT EXISTS market_event (
    event_id TEXT PRIMARY KEY,
    listing_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    before_observation_id INTEGER,
    after_observation_id INTEGER,
    method_version TEXT DEFAULT '1.0.0',
    FOREIGN KEY (listing_id) REFERENCES market_listing(listing_id),
    FOREIGN KEY (before_observation_id) REFERENCES market_observation(observation_id),
    FOREIGN KEY (after_observation_id) REFERENCES market_observation(observation_id)
);

-- Listing run membership (for disappearance detection)
CREATE TABLE IF NOT EXISTS listing_seen (
    collector_run_id INTEGER NOT NULL,
    listing_id TEXT NOT NULL,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (collector_run_id, listing_id),
    FOREIGN KEY (collector_run_id) REFERENCES collector_run(run_id),
    FOREIGN KEY (listing_id) REFERENCES market_listing(listing_id)
);

-- Collector health (persisted after every run)
CREATE TABLE IF NOT EXISTS source_health (
    health_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    last_attempt TEXT,
    last_success TEXT,
    last_error TEXT,
    records_seen INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_changed INTEGER DEFAULT 0,
    records_unchanged INTEGER DEFAULT 0,
    records_invalid INTEGER DEFAULT 0,
    status TEXT DEFAULT 'unknown',
    status_reason TEXT,
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Product canonical identity (PowProducts Layer 1)
CREATE TABLE IF NOT EXISTS manufacturer (
    manufacturer_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    aliases_json TEXT,
    country_code TEXT,
    website_domain TEXT,
    external_ids_json TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_family (
    family_id TEXT PRIMARY KEY,
    manufacturer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    product_class TEXT,
    parent_family_id TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturer(manufacturer_id)
);

CREATE TABLE IF NOT EXISTS product_model (
    product_id TEXT PRIMARY KEY,
    manufacturer_id TEXT NOT NULL,
    family_id TEXT,
    canonical_name TEXT NOT NULL,
    model_number TEXT,
    product_class TEXT,
    release_date TEXT,
    discontinued_date TEXT,
    declared_status TEXT,
    country_of_origin TEXT,
    external_ids_json TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturer(manufacturer_id),
    FOREIGN KEY (family_id) REFERENCES product_family(family_id)
);

CREATE TABLE IF NOT EXISTS product_variant (
    variant_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    variant_manufacturer_id TEXT,
    manufacturer_sku TEXT,
    mpn TEXT,
    gtin TEXT,
    ean TEXT,
    upc TEXT,
    revision TEXT,
    capacity TEXT,
    memory TEXT,
    packaging TEXT,
    region TEXT,
    external_ids_json TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES product_model(product_id),
    FOREIGN KEY (variant_manufacturer_id) REFERENCES manufacturer(manufacturer_id)
);

-- Product identifiers (canonical, with source assertions)
CREATE TABLE IF NOT EXISTS product_identifier (
    identifier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_record_id TEXT,
    valid_from TEXT,
    valid_to TEXT,
    confidence REAL DEFAULT 1.0,
    UNIQUE(namespace, normalized_value, entity_id)
);

-- Product relations (canonical edges)
CREATE TABLE IF NOT EXISTS product_relation (
    relation_id TEXT PRIMARY KEY,
    src_entity_id TEXT NOT NULL,
    dst_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(src_entity_id, dst_entity_id, relation_type)
);

-- Product relation assertions (evidence per source)
CREATE TABLE IF NOT EXISTS product_relation_assertion (
    assertion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id TEXT NOT NULL,
    source_record_id TEXT,
    truth_class TEXT DEFAULT 'declared',
    confidence REAL DEFAULT 1.0,
    quantity REAL,
    unit TEXT,
    valid_from TEXT,
    valid_to TEXT,
    evidence_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (relation_id) REFERENCES product_relation(relation_id),
    UNIQUE(relation_id, source_record_id)
);

CREATE TABLE IF NOT EXISTS product_spec_observation (
    spec_observation_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    spec_key TEXT NOT NULL,
    value TEXT,
    numeric_value REAL,
    unit TEXT,
    source_id TEXT,
    source_record_id TEXT,
    truth_class TEXT DEFAULT 'declared',
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    effective_at TEXT,
    parser_version TEXT
);

-- Market listings (resolved to canonical products)
CREATE TABLE IF NOT EXISTS market_listing (
    listing_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_native_id TEXT NOT NULL,
    resolved_product_id TEXT,
    resolved_variant_id TEXT,
    title TEXT,
    description TEXT,
    market TEXT,
    market_country TEXT,
    seller_id TEXT,
    seller_location TEXT,
    listing_type TEXT,
    condition TEXT,
    scope TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_url_ref TEXT,
    FOREIGN KEY (resolved_product_id) REFERENCES product_model(product_id),
    FOREIGN KEY (resolved_variant_id) REFERENCES product_variant(variant_id)
);

-- Lifecycle events
CREATE TABLE IF NOT EXISTS lifecycle_event (
    event_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_id TEXT,
    evidence TEXT
);

-- Benchmark observations
CREATE TABLE IF NOT EXISTS benchmark_observation (
    benchmark_observation_id TEXT PRIMARY KEY,
    product_id TEXT,
    variant_id TEXT,
    benchmark_family TEXT,
    benchmark_name TEXT,
    workload TEXT,
    score REAL,
    unit TEXT,
    hardware_count INTEGER,
    power_mode TEXT,
    software TEXT,
    software_version TEXT,
    source_id TEXT,
    source_record_id TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    benchmark_date TEXT,
    FOREIGN KEY (product_id) REFERENCES product_model(product_id)
);

-- Robot descriptions
CREATE TABLE IF NOT EXISTS robot_description (
    robot_description_id TEXT PRIMARY KEY,
    product_id TEXT,
    format TEXT,
    source_id TEXT,
    source_version TEXT,
    upstream_repo TEXT,
    upstream_version TEXT,
    licence TEXT,
    description_hash TEXT,
    links_json TEXT,
    joints_json TEXT,
    raw_ref TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES product_model(product_id)
);

-- Jev semantic annotations
CREATE TABLE IF NOT EXISTS jev_decision (
    jev_decision_id TEXT PRIMARY KEY,
    source_record_id TEXT,
    input_hash TEXT,
    question_schema_id TEXT,
    question_schema_version TEXT,
    model_id TEXT,
    model_version TEXT,
    options_json TEXT,
    probabilities_json TEXT,
    selected_option TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Source rights (machine-readable)
CREATE TABLE IF NOT EXISTS source_rights (
    source_id TEXT PRIMARY KEY,
    access_type TEXT,
    licence TEXT,
    terms_url_ref TEXT,
    raw_retention TEXT,
    normalized_retention TEXT,
    derivatives TEXT,
    redistribution TEXT,
    commercial_use TEXT,
    automated_access TEXT,
    status TEXT NOT NULL DEFAULT 'terms_review',
    reviewed_at TEXT,
    notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_source_record_source ON source_record(source_id);
CREATE INDEX IF NOT EXISTS idx_source_record_native ON source_record(source_native_id);
CREATE INDEX IF NOT EXISTS idx_source_record_retrieved ON source_record(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_observation_source ON observation(source_id);
CREATE INDEX IF NOT EXISTS idx_observation_entity ON observation(entity_id);
CREATE INDEX IF NOT EXISTS idx_observation_metric ON observation(metric);
CREATE INDEX IF NOT EXISTS idx_raw_acq_source ON raw_acquisition(source_id);
CREATE INDEX IF NOT EXISTS idx_market_obs_record ON market_observation(source_record_id);
CREATE INDEX IF NOT EXISTS idx_market_obs_time ON market_observation(observed_at);
CREATE INDEX IF NOT EXISTS idx_market_obs_native ON market_observation(source_native_id);
CREATE INDEX IF NOT EXISTS idx_product_identifier_entity ON product_identifier(entity_id);
CREATE INDEX IF NOT EXISTS idx_product_identifier_ns ON product_identifier(namespace, normalized_value);
CREATE INDEX IF NOT EXISTS idx_product_relation_src ON product_relation(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_product_relation_dst ON product_relation(dst_entity_id);
CREATE INDEX IF NOT EXISTS idx_product_relation_type ON product_relation(relation_type);
CREATE INDEX IF NOT EXISTS idx_relation_assertion_rel ON product_relation_assertion(relation_id);
CREATE INDEX IF NOT EXISTS idx_spec_obs_entity ON product_spec_observation(entity_id);
CREATE INDEX IF NOT EXISTS idx_spec_obs_key ON product_spec_observation(spec_key);
CREATE INDEX IF NOT EXISTS idx_market_listing_product ON market_listing(resolved_product_id);
CREATE INDEX IF NOT EXISTS idx_market_listing_source ON market_listing(source_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_entity ON lifecycle_event(entity_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_product ON benchmark_observation(product_id);
CREATE INDEX IF NOT EXISTS idx_market_event_listing ON market_event(listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_seen_run ON listing_seen(collector_run_id);
"""


def _enable_foreign_keys(conn):
    """Enable foreign key enforcement on a connection."""
    conn.execute("PRAGMA foreign_keys=ON")


def _get_schema_version(conn) -> int:
    """Get current schema version."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row and row[0] else 0
    except sqlite3.OperationalError:
        return 0


def _apply_migrations(conn):
    """Apply pending migrations."""
    current = _get_schema_version(conn)

    migrations = {
        1: "INSERT OR IGNORE INTO schema_version (version) VALUES (1)",
    }

    for version in sorted(migrations.keys()):
        if version > current:
            conn.execute(migrations[version])
            conn.commit()


def init_db():
    """Initialize database with canonical schema."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    _enable_foreign_keys(conn)
    conn.executescript(SCHEMA)
    _apply_migrations(conn)
    conn.commit()
    print(f'Database initialized: {db_path}')
    return conn


def get_db():
    """Get database connection with foreign keys enabled."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    _enable_foreign_keys(conn)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def status():
    """Print database status."""
    conn = get_db()
    _enable_foreign_keys(conn)
    tables = ['raw_blob', 'raw_acquisition', 'source_record', 'observation',
              'source_cursor', 'collector_run', 'market_observation', 'market_listing',
              'market_event', 'listing_seen',
              'manufacturer', 'product_family', 'product_model', 'product_variant',
              'product_identifier', 'product_relation', 'product_relation_assertion',
              'product_spec_observation',
              'lifecycle_event', 'benchmark_observation',
              'robot_description', 'jev_decision', 'source_rights']
    print('=== DATABASE STATUS ===')
    for t in tables:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            print(f'  {t:35s} {c:>10,}')
        except:
            print(f'  {t:35s} {"MISSING":>10}')

    print('\n=== BY SOURCE ===')
    try:
        rows = conn.execute('''
            SELECT source_id, COUNT(*) as total,
                   MIN(retrieved_at) as first, MAX(retrieved_at) as last
            FROM source_record GROUP BY source_id ORDER BY total DESC
        ''').fetchall()
        for r in rows:
            print(f'  {r[0]:25s} {r[1]:>10,}  {r[2][:10] if r[2] else "?"} → {r[3][:10] if r[3] else "?"}')
    except:
        print('  No source_record data yet')

    print('\n=== SOURCE RIGHTS ===')
    try:
        rows = conn.execute('SELECT source_id, status FROM source_rights ORDER BY source_id').fetchall()
        for r in rows:
            print(f'  {r[0]:25s} {r[1]}')
    except:
        print('  No source_rights configured')

    conn.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        status()
    else:
        init_db()
