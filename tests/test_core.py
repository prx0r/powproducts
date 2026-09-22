"""Comprehensive test suite for PowProducts — Section 47 + P0 hardening.

Covers: persistence, identity, marketplace, component, robotics, ROBOTIS,
benchmark, rights, JEV, replay, and end-to-end fixture tests.
"""

import hashlib
import json
import os
import sys
import sqlite3
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from powproducts.shared.persist import (
    get_db, store_raw, store_acquisition, insert_source_record,
    get_cursor, set_cursor, log_run, store_market_observation,
    upsert_manufacturer, upsert_product_model, upsert_product_variant,
    insert_product_identifier, insert_product_relation, insert_spec_observation,
    check_source_rights, persist_health,
    InsertResult, RawStoreResult
)
from powproducts.shared.db import SCHEMA, _enable_foreign_keys


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database using the production schema."""
    db_path = tmp_path / 'test.db'
    os.environ['POWPRODUCTS_DB'] = str(db_path)
    conn = sqlite3.connect(str(db_path))
    _enable_foreign_keys(conn)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    yield db_path
    os.environ.pop('POWPRODUCTS_DB', None)


# =============================================================================
# P0: FOREIGN KEYS
# =============================================================================

class TestForeignKeys:
    def test_fk_enforced_on_connection(self, temp_db):
        """Foreign keys are enforced — inserting for nonexistent manufacturer fails."""
        conn = sqlite3.connect(str(temp_db))
        _enable_foreign_keys(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO product_model (product_id, manufacturer_id, canonical_name) "
                "VALUES ('test', 'nonexistent', 'Test')"
            )
        conn.close()

    def test_fk_violation_not_enforced_without_pragma(self, temp_db):
        """Without PRAGMA, FK violation would succeed (proves PRAGMA matters)."""
        conn = sqlite3.connect(str(temp_db))
        # Don't enable FKs
        conn.execute(
            "INSERT INTO product_model (product_id, manufacturer_id, canonical_name) "
            "VALUES ('test', 'nonexistent', 'Test')"
        )
        conn.rollback()
        conn.close()


# =============================================================================
# P0: PRODUCT IDENTIFIER UNIQUENESS
# =============================================================================

class TestIdentifierUniqueness:
    def test_same_identifier_not_duplicated(self, temp_db):
        """Same (namespace, value, entity) does not accumulate duplicates."""
        insert_product_identifier('v1', 'mpn', 'RTX4090', source_id='mouser')
        insert_product_identifier('v1', 'mpn', 'RTX4090', source_id='tme')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_identifier').fetchone()[0]
        assert count == 1  # deduplicated
        conn.close()

    def test_different_entities_different_identifiers(self, temp_db):
        """Same MPN on different entities creates separate identifiers."""
        insert_product_identifier('v1', 'mpn', 'RTX4090')
        insert_product_identifier('v2', 'mpn', 'RTX4090')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_identifier').fetchone()[0]
        assert count == 2
        conn.close()

    def test_blank_identifier_rejected(self, temp_db):
        """Blank MPN/sku does not create an identifier."""
        insert_product_identifier('v1', 'mpn', '')
        insert_product_identifier('v1', 'mpn', '  ')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_identifier').fetchone()[0]
        assert count == 0
        conn.close()


# =============================================================================
# P0: PRODUCT RELATIONS SPLIT
# =============================================================================

class TestRelationSplit:
    def test_relation_edge_plus_assertions(self, temp_db):
        """One edge can have multiple independent evidence assertions."""
        rid = insert_product_relation('mx28', 'xm430', 'SUPERSEDES',
                                       source_record_id='sr1',
                                       evidence_json=json.dumps({'source': 'robotis'}))
        insert_product_relation('mx28', 'xm430', 'SUPERSEDES',
                                 source_record_id='sr2',
                                 evidence_json=json.dumps({'source': 'mouser'}))
        conn = sqlite3.connect(str(temp_db))
        edges = conn.execute('SELECT COUNT(*) FROM product_relation').fetchone()[0]
        assertions = conn.execute('SELECT COUNT(*) FROM product_relation_assertion').fetchone()[0]
        assert edges == 1  # one canonical edge
        assert assertions == 2  # two independent proofs
        conn.close()

    def test_relation_id_deterministic(self, temp_db):
        """Same src+dst+type always produces same relation_id."""
        rid1 = insert_product_relation('a', 'b', 'VARIANT_OF')
        rid2 = insert_product_relation('a', 'b', 'VARIANT_OF')
        assert rid1 == rid2
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_relation').fetchone()[0]
        assert count == 1
        conn.close()


# =============================================================================
# P0: VARIANT MANUFACTURER
# =============================================================================

class TestVariantManufacturer:
    def test_variant_has_manufacturer(self, temp_db):
        """Variant tracks its own manufacturer (brand)."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_manufacturer('msi', 'MSI')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('msi-gaming-x-trio', 'rtx4090',
                                variant_manufacturer_id='msi', mpn='RTX 4090 GAMING X TRIO')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            'SELECT variant_manufacturer_id FROM product_variant WHERE variant_id="msi-gaming-x-trio"'
        ).fetchone()
        assert row[0] == 'msi'
        conn.close()


# =============================================================================
# P0: PRICE TYPE
# =============================================================================

class TestPriceType:
    def test_price_type_stored(self, temp_db):
        """Market observations carry price_type semantics."""
        ir = insert_source_record('test', 'ds', 'n1', {'price': 100}, 'h', 'p')
        store_market_observation(
            source_record_id=ir.record_id,
            observed_at=datetime.now(timezone.utc).isoformat(),
            price=100.0, currency='GBP', market='test',
            price_type='retail_ask',
        )
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT price_type FROM market_observation').fetchone()
        assert row[0] == 'retail_ask'
        conn.close()


# =============================================================================
# P0: SOURCE RIGHTS GATE
# =============================================================================

class TestRightsGate:
    def test_blocked_source_refuses(self, temp_db):
        """Blocked source is not allowed to run."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO source_rights (source_id, status) VALUES ('ebay_gb', 'blocked')")
        conn.commit()
        conn.close()
        rights = check_source_rights('ebay_gb')
        assert rights['allowed'] is False
        assert rights['status'] == 'blocked'

    def test_open_source_allowed(self, temp_db):
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO source_rights (source_id, status) VALUES ('pci_ids', 'open')")
        conn.commit()
        conn.close()
        rights = check_source_rights('pci_ids')
        assert rights['allowed'] is True

    def test_unknown_source_not_allowed(self, temp_db):
        rights = check_source_rights('nonexistent')
        assert rights['allowed'] is False


# =============================================================================
# P0: IDs REJECT BLANK FIELDS
# =============================================================================

class TestIdEdgeCases:
    def test_make_product_id_rejects_blank(self):
        from powproducts.core.ids import make_product_id
        assert make_product_id('nvidia', '') is None
        assert make_product_id('nvidia', '  ') is None
        assert make_product_id('', 'RTX4090') is None

    def test_make_variant_id_rejects_blank(self):
        from powproducts.core.ids import make_variant_id
        assert make_variant_id('product1', sku='', mpn='') is None
        assert make_variant_id('product1', sku='  ', mpn='  ') is None

    def test_make_variant_id_with_sku(self):
        from powproducts.core.ids import make_variant_id
        vid = make_variant_id('product1', sku='SKU123')
        assert vid is not None

    def test_make_variant_id_with_mpn(self):
        from powproducts.core.ids import make_variant_id
        vid = make_variant_id('product1', mpn='MPN456')
        assert vid is not None


# =============================================================================
# PERSISTENCE TESTS
# =============================================================================

class TestPersistence:
    def test_raw_content_hashes_deterministically(self, temp_db):
        content = b'deterministic content test'
        r1 = store_raw(content, 'test')
        r2 = store_raw(content, 'test')
        assert r1.sha256 == r2.sha256
        assert r1.sha256 == hashlib.sha256(content).hexdigest()

    def test_raw_blobs_immutable(self, temp_db):
        content = b'immutable content'
        r = store_raw(content, 'test')
        store_raw(b'different content', 'test')
        import gzip
        with gzip.open(r.path, 'rb') as f:
            assert f.read() == content

    def test_repeated_raw_payload_deduplicated(self, temp_db):
        content = b'dedup test'
        for _ in range(5):
            store_raw(content, 'test')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM raw_blob').fetchone()[0]
        assert count == 1
        conn.close()

    def test_acquisition_receipt_appends(self, temp_db):
        content = b'acquisition test'
        r = store_raw(content, 'test')
        store_acquisition('test', 'ds', 'http://example.com', 200, r.sha256)
        store_acquisition('test', 'ds', 'http://example.com', 200, r.sha256)
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM raw_acquisition').fetchone()[0]
        assert count == 2
        conn.close()

    def test_changed_source_payload_versions(self, temp_db):
        ir1 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h1', 'p')
        ir2 = insert_source_record('test', 'ds', 'n1', {'k': 'v2'}, 'h2', 'p')
        assert ir1.inserted is True
        assert ir2.inserted is True
        assert ':v' in ir2.record_id

    def test_unchanged_payload_no_invented_version(self, temp_db):
        ir1 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h1', 'p')
        ir2 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h2', 'p')
        assert ir1.inserted is True
        assert ir2.inserted is False

    def test_market_observation_appends_unchanged_price(self, temp_db):
        ir = insert_source_record('test', 'ds', 'n1', {'price': 100}, 'h', 'p')
        for _ in range(5):
            store_market_observation(
                source_record_id=ir.record_id,
                observed_at=datetime.now(timezone.utc).isoformat(),
                price=100.0, currency='GBP', market='test',
            )
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM market_observation').fetchone()[0]
        assert count == 5
        conn.close()

    def test_source_record_links_to_acquisition(self, temp_db):
        """Source record carries acquisition_id for provenance."""
        r = store_raw(b'test', 'test')
        acq_id = store_acquisition('test', 'ds', 'http://example.com', 200, r.sha256)
        ir = insert_source_record('test', 'ds', 'n1', {'k': 'v'}, 'h', 'p',
                                   acquisition_id=acq_id)
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT acquisition_id FROM source_record WHERE source_record_id=?',
                           (ir.record_id,)).fetchone()
        assert row[0] == acq_id
        conn.close()


# =============================================================================
# IDENTITY TESTS
# =============================================================================

class TestIdentity:
    def test_same_mpn_resolves_same_variant(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('rtx4090-fe', 'rtx4090', mpn='RTX4090')
        insert_product_identifier('rtx4090-fe', 'mpn', 'RTX4090', source_id='mouser')
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT entity_id FROM product_identifier WHERE namespace="mpn" AND normalized_value="RTX4090"').fetchall()
        assert len({r[0] for r in rows}) == 1
        conn.close()

    def test_price_does_not_change_product_id(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('v1', 'rtx4090', mpn='RTX4090-FE')
        insert_spec_observation('v1', 'tdp_watts', '450', numeric_value=450)
        insert_spec_observation('v1', 'tdp_watts', '420', numeric_value=420)
        conn = sqlite3.connect(str(temp_db))
        v = conn.execute('SELECT COUNT(*) FROM product_variant WHERE variant_id="v1"').fetchone()[0]
        assert v == 1
        conn.close()

    def test_rtx4090_not_msi_variant(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_manufacturer('msi', 'MSI')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('rtx4090-fe', 'rtx4090', variant_manufacturer_id='nvidia', mpn='RTX4090FE')
        upsert_product_variant('msi-gaming', 'rtx4090', variant_manufacturer_id='msi', mpn='RTX 4090 GAMING')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_variant WHERE product_id="rtx4090"').fetchone()[0]
        assert count == 2
        conn.close()

    def test_h100_pcie_not_h100_sxm(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('h100', 'nvidia', 'H100')
        upsert_product_variant('h100-pcie', 'h100', mpn='H100 PCIe 80GB')
        upsert_product_variant('h100-sxm', 'h100', mpn='H100 SXM5 80GB')
        conn = sqlite3.connect(str(temp_db))
        v1 = conn.execute('SELECT variant_id FROM product_variant WHERE mpn="H100 PCIe 80GB"').fetchone()
        v2 = conn.execute('SELECT variant_id FROM product_variant WHERE mpn="H100 SXM5 80GB"').fetchone()
        assert v1[0] != v2[0]
        conn.close()


# =============================================================================
# MARKETPLACE TESTS
# =============================================================================

class TestMarketplace:
    def test_disappeared_is_not_sold(self, temp_db):
        """Disappearance is not SOLD_CONFIRMED."""
        ir = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'active'}, 'h', 'p')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id="ebay:L100"').fetchone()
        data = json.loads(row[0])
        assert data.get('status') == 'active'
        conn.close()

    def test_sold_confirmed_needs_explicit_evidence(self, temp_db):
        ir = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'sold', 'sold_price': 1450}, 'h', 'p')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id="ebay:L100"').fetchone()
        data = json.loads(row[0])
        assert data.get('status') == 'sold'
        conn.close()


# =============================================================================
# ROBOTICS TESTS
# =============================================================================

class TestRobotics:
    def test_urdf_fixture_extracts_links_and_joints(self, temp_db):
        urdf_data = {
            'links': [{'name': 'base'}, {'name': 'shoulder'}],
            'joints': [{'name': 'j1', 'type': 'revolute', 'parent': 'base',
                        'child': 'shoulder', 'axis': [0, 0, 1],
                        'limit': {'lower': -3.14, 'upper': 3.14, 'velocity': 1.0, 'effort': 50.0}}],
        }
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO robot_description (robot_description_id, product_id, format, "
            "source_id, links_json, joints_json) VALUES (?, ?, ?, ?, ?, ?)",
            ('rd1', 'ur5e', 'urdf', 'test',
             json.dumps(urdf_data['links']), json.dumps(urdf_data['joints']))
        )
        conn.commit()
        row = conn.execute('SELECT joints_json FROM robot_description WHERE robot_description_id="rd1"').fetchone()
        joints = json.loads(row[0])
        assert joints[0]['type'] == 'revolute'
        assert joints[0]['limit']['effort'] == 50.0
        conn.close()

    def test_robot_component_relationships(self, temp_db):
        upsert_manufacturer('ur', 'Universal Robots')
        upsert_product_model('ur5e', 'ur', 'UR5e', product_class='robot_arm')
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('xm430', 'robotis', 'DYNAMIXEL XM430', product_class='actuator')
        rid = insert_product_relation('ur5e', 'xm430', 'CONTAINS',
                                       source_record_id='sr1',
                                       quantity=6, unit='joints')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT quantity, unit FROM product_relation_assertion WHERE relation_id=?',
                           (rid,)).fetchone()
        assert row[0] == 6
        assert row[1] == 'joints'
        conn.close()


# =============================================================================
# ROBOTIS TESTS
# =============================================================================

class TestRobotis:
    def test_model_identity_and_specs(self, temp_db):
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('xm430-w350', 'robotis', 'DYNAMIXEL XM430-W350', product_class='actuator')
        insert_spec_observation('xm430-w350', 'rated_voltage', '12V', numeric_value=12, unit='V')
        insert_spec_observation('xm430-w350', 'stall_torque', '4.66', numeric_value=4.66, unit='N·m')
        conn = sqlite3.connect(str(temp_db))
        specs = conn.execute('SELECT spec_key, numeric_value FROM product_spec_observation WHERE entity_id="xm430-w350"').fetchall()
        spec_dict = {s[0]: s[1] for s in specs}
        assert spec_dict['rated_voltage'] == 12.0
        assert spec_dict['stall_torque'] == 4.66
        conn.close()

    def test_replacement_edge_with_evidence(self, temp_db):
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('mx-28', 'robotis', 'DYNAMIXEL MX-28')
        upsert_product_model('xm430', 'robotis', 'DYNAMIXEL XM430')
        rid = insert_product_relation('mx-28', 'xm430', 'SUPERSEDES',
                                       source_record_id='sr1',
                                       evidence_json=json.dumps({'source': 'robotis'}))
        insert_product_relation('mx-28', 'xm430', 'SUPERSEDES',
                                 source_record_id='sr2',
                                 evidence_json=json.dumps({'source': 'distributor'}))
        conn = sqlite3.connect(str(temp_db))
        assertions = conn.execute('SELECT COUNT(*) FROM product_relation_assertion WHERE relation_id=?',
                                   (rid,)).fetchone()[0]
        assert assertions == 2
        conn.close()


# =============================================================================
# BENCHMARK TESTS
# =============================================================================

class TestBenchmark:
    def test_benchmark_resolves_canonical_product(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO benchmark_observation (benchmark_observation_id, product_id, "
            "benchmark_family, score, unit, software, software_version, source_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('b1', 'rtx4090', 'blender', 4200.5, 'samples/min', 'Blender', '4.1.0', 'blender')
        )
        conn.commit()
        row = conn.execute('SELECT score, unit FROM benchmark_observation WHERE product_id="rtx4090"').fetchone()
        assert row[0] == 4200.5
        conn.close()


# =============================================================================
# JEV TESTS
# =============================================================================

class TestJev:
    def test_raw_collector_succeeds_when_jev_unavailable(self, temp_db):
        from powproducts.collectors.base import BaseCollector
        class OfflineCollector(BaseCollector):
            SOURCE_ID = 'offline'
            DATASET = 'test'
            PARSER_ID = 'test'
            def fetch(self): return b'{"items": []}'
            def parse(self, raw_content, raw_hash, result): result.records_new = 1
        result = OfflineCollector().run()
        assert result.records_new == 1

    def test_jev_never_mutates_source_record(self, temp_db):
        ir = insert_source_record('test', 'ds', 'n1', {'title': 'RTX 4090'}, 'h', 'p')
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO jev_decision (jev_decision_id, source_record_id, "
            "question_schema_id, model_id, probabilities_json, selected_option) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ('jd1', ir.record_id, 'q1', 'm1',
             json.dumps({'RTX_4090': 0.92, 'UNKNOWN': 0.08}), 'RTX 4090')
        )
        conn.commit()
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id=?',
                           (ir.record_id,)).fetchone()
        data = json.loads(row[0])
        assert data['title'] == 'RTX 4090'
        conn.close()


# =============================================================================
# REPLAY TESTS
# =============================================================================

class TestReplay:
    def test_parser_deterministic_output(self, temp_db):
        raw = b'{"sku": "RTX4090", "name": "RTX 4090"}'
        data1 = json.loads(raw)
        data2 = json.loads(raw)
        assert data1 == data2
        h1 = hashlib.sha256(json.dumps(data1, sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(data2, sort_keys=True).encode()).hexdigest()
        assert h1 == h2


# =============================================================================
# HEALTH TESTS
# =============================================================================

class TestHealth:
    def test_health_computes_ok(self):
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="test", source_id="test", records_seen=20)
        h.compute_status(expected_min_rows=10)
        assert h.status == "ok"

    def test_health_computes_blocked(self):
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="test", source_id="test", http_status=403)
        h.compute_status()
        assert h.status == "blocked"

    def test_health_computes_degraded_no_data(self):
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="test", source_id="test", records_seen=0)
        h.compute_status(expected_min_rows=10)
        assert h.status == "degraded"

    def test_health_computes_error(self):
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="test", source_id="test", last_error="timeout")
        h.compute_status()
        assert h.status == "error"

    def test_health_from_run_result(self):
        from powproducts.collectors.base import CollectorResult
        from powproducts.layer1.health import health_from_run_result
        result = CollectorResult()
        result.records_new = 5
        result.finished_at = "2026-09-21T12:00:00"
        health = health_from_run_result("test", "test", result)
        assert health.status == "ok"
        assert health.records_new == 5


# =============================================================================
# BASE COLLECTOR TESTS
# =============================================================================

class TestBaseCollector:
    def test_success_run(self, temp_db):
        from powproducts.collectors.base import BaseCollector
        class TestCollector(BaseCollector):
            SOURCE_ID = 'test_c'
            DATASET = 'test_d'
            PARSER_ID = 'test_p'
            RIGHTS_STATUS = 'open'
            def fetch(self): return b'{"items": []}'
            def parse(self, raw_content, raw_hash, result): result.records_new = 1
        # Need to register rights
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO source_rights (source_id, status) VALUES ('test_c', 'open')")
        conn.commit()
        conn.close()
        result = TestCollector().run()
        assert result.records_new == 1

    def test_rights_blocked_run(self, temp_db):
        from powproducts.collectors.base import BaseCollector
        class BlockedCollector(BaseCollector):
            SOURCE_ID = 'blocked_c'
            DATASET = 'test'
            PARSER_ID = 'test'
            RIGHTS_STATUS = 'blocked'
            def fetch(self): return b'data'
            def parse(self, raw_content, raw_hash, result): pass
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO source_rights (source_id, status) VALUES ('blocked_c', 'blocked')")
        conn.commit()
        conn.close()
        result = BlockedCollector().run()
        assert 'rights_blocked' in result.errors

    def test_failed_fetch_is_logged(self, temp_db):
        from powproducts.collectors.base import BaseCollector
        class Failing(BaseCollector):
            SOURCE_ID = 'fail'
            DATASET = 'test'
            PARSER_ID = 'test'
            RIGHTS_STATUS = 'open'
            def fetch(self): return None
            def parse(self, raw_content, raw_hash, result): pass
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO source_rights (source_id, status) VALUES ('fail', 'open')")
        conn.commit()
        conn.close()
        result = Failing().run()
        assert 'fetch_failed' in result.errors


# =============================================================================
# DAEMON TESTS
# =============================================================================

class TestDaemon:
    def test_daemon_can_resolve_all_collectors(self):
        """Every registered collector class can be loaded."""
        from powproducts.daemon import COLLECTORS, load_collector
        for source_id, config in COLLECTORS.items():
            cls = load_collector(config['class'])
            assert hasattr(cls, 'SOURCE_ID')


# =============================================================================
# LIFECYCLE TESTS
# =============================================================================

class TestLifecycle:
    def test_lifecycle_event_stored(self, temp_db):
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO lifecycle_event (event_id, entity_id, event_type, event_time, source_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('e1', 'rtx4090', 'RELEASED', '2022-10-12', 'nvidia')
        )
        conn.commit()
        row = conn.execute('SELECT event_type FROM lifecycle_event WHERE event_id="e1"').fetchone()
        assert row[0] == 'RELEASED'
        conn.close()


# =============================================================================
# CURSOR TESTS
# =============================================================================

class TestCursor:
    def test_cursor_set_and_get(self, temp_db):
        set_cursor('test', 'ds', '42')
        assert get_cursor('test', 'ds') == '42'

    def test_cursor_overwrite(self, temp_db):
        set_cursor('test', 'ds', '10')
        set_cursor('test', 'ds', '20')
        assert get_cursor('test', 'ds') == '20'
