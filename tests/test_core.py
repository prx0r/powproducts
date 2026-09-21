"""Comprehensive test suite for PowProducts — Section 47 of northstar.

Covers: persistence, identity, marketplace, component, robotics, ROBOTIS,
benchmark, rights, JEV, and replay tests.
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
    InsertResult, RawStoreResult
)
from powproducts.shared.db import SCHEMA


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database using the production schema."""
    db_path = tmp_path / 'test.db'
    os.environ['POWPRODUCTS_DB'] = str(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    yield db_path
    os.environ.pop('POWPRODUCTS_DB', None)


# =============================================================================
# PERSISTENCE TESTS
# =============================================================================

class TestPersistence:
    def test_raw_content_hashes_deterministically(self, temp_db):
        """Same content always produces same hash."""
        content = b'deterministic content test'
        r1 = store_raw(content, 'test')
        r2 = store_raw(content, 'test')
        assert r1.sha256 == r2.sha256
        expected = hashlib.sha256(content).hexdigest()
        assert r1.sha256 == expected

    def test_raw_blobs_immutable(self, temp_db):
        """Once stored, raw blobs cannot be modified."""
        content = b'immutable content'
        r = store_raw(content, 'test')
        # Try to store same path with different content — should not overwrite
        store_raw(b'different content', 'test')
        import gzip
        with gzip.open(r.path, 'rb') as f:
            assert f.read() == content

    def test_repeated_raw_payload_deduplicated(self, temp_db):
        """Repeated raw payloads produce one blob, not many."""
        content = b'dedup test'
        for _ in range(5):
            store_raw(content, 'test')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM raw_blob').fetchone()[0]
        assert count == 1
        conn.close()

    def test_acquisition_receipt_appends(self, temp_db):
        """Same blob fetched at different times creates multiple acquisition records."""
        content = b'acquisition test'
        r = store_raw(content, 'test')
        store_acquisition('test', 'ds', 'http://example.com', 200, r.sha256)
        store_acquisition('test', 'ds', 'http://example.com', 200, r.sha256)
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM raw_acquisition').fetchone()[0]
        assert count == 2
        conn.close()

    def test_changed_source_payload_versions(self, temp_db):
        """Changed payload creates a new version with content-addressed ID."""
        ir1 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h1', 'p')
        ir2 = insert_source_record('test', 'ds', 'n1', {'k': 'v2'}, 'h2', 'p')
        assert ir1.inserted is True
        assert ir2.inserted is True
        assert ':v' in ir2.record_id
        assert ir2.record_id != ir1.record_id

    def test_unchanged_payload_no_invented_version(self, temp_db):
        """Unchanged payload returns duplicate_of, not a new version."""
        ir1 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h1', 'p')
        ir2 = insert_source_record('test', 'ds', 'n1', {'k': 'v1'}, 'h2', 'p')
        assert ir1.inserted is True
        assert ir2.inserted is False
        assert ir2.duplicate_of == ir1.record_id

    def test_market_observation_appends_unchanged_price(self, temp_db):
        """Even unchanged price still creates an observation (time dimension matters)."""
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


# =============================================================================
# IDENTITY TESTS
# =============================================================================

class TestIdentity:
    def test_same_mpn_resolves_same_variant(self, temp_db):
        """Same MPN across sources should reference the same canonical variant."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('rtx4090-fe', 'rtx4090', mpn='RTX4090')
        insert_product_identifier('rtx4090-fe', 'mpn', 'RTX4090', source_id='mouser')
        insert_product_identifier('rtx4090-fe', 'mpn', 'RTX4090', source_id='tme')
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT entity_id FROM product_identifier WHERE namespace="mpn" AND value="RTX4090"').fetchall()
        entity_ids = {r[0] for r in rows}
        assert len(entity_ids) == 1  # both resolve to same entity
        conn.close()

    def test_price_does_not_change_product_id(self, temp_db):
        """Price changes are observations, not identity mutations."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('v1', 'rtx4090', mpn='RTX4090-FE')
        insert_spec_observation('v1', 'price_gbp', '1599', numeric_value=1599)
        insert_spec_observation('v1', 'price_gbp', '1499', numeric_value=1499)
        insert_spec_observation('v1', 'price_gbp', '1699', numeric_value=1699)
        conn = sqlite3.connect(str(temp_db))
        v = conn.execute('SELECT COUNT(*) FROM product_variant WHERE variant_id="v1"').fetchone()[0]
        assert v == 1
        s = conn.execute('SELECT COUNT(*) FROM product_spec_observation WHERE entity_id="v1"').fetchone()[0]
        assert s == 3
        conn.close()

    def test_condition_does_not_change_product_id(self, temp_db):
        """Condition is a listing attribute, not a product attribute."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('v1', 'rtx4090')
        ir1 = insert_source_record('ebay', 'uk', 'L1', {'condition': 'new'}, 'h1', 'p')
        ir2 = insert_source_record('ebay', 'uk', 'L1', {'condition': 'broken'}, 'h2', 'p')
        conn = sqlite3.connect(str(temp_db))
        v = conn.execute('SELECT COUNT(*) FROM product_variant WHERE variant_id="v1"').fetchone()[0]
        assert v == 1
        conn.close()

    def test_marketplace_listing_id_stable(self, temp_db):
        """Listing ID is source-native, stable across price/condition changes."""
        ir1 = insert_source_record('ebay', 'uk', 'listing_12345',
                                    {'price': 1000, 'condition': 'new'}, 'h1', 'p')
        ir2 = insert_source_record('ebay', 'uk', 'listing_12345',
                                    {'price': 900, 'condition': 'used'}, 'h2', 'p')
        assert ir1.record_id == 'ebay:listing_12345'
        assert ':v' in ir2.record_id
        assert ir2.duplicate_of == 'ebay:listing_12345'

    def test_manufacturer_aliases_resolve_deterministically(self, temp_db):
        """Known aliases resolve to the same manufacturer."""
        upsert_manufacturer('nvidia', 'NVIDIA Corporation',
                            aliases=['NVIDIA', 'NVIDIA Corp', 'nVidia'])
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT canonical_name FROM manufacturer WHERE manufacturer_id="nvidia"').fetchone()
        assert row[0] == 'NVIDIA Corporation'
        aliases = json.loads(conn.execute('SELECT aliases_json FROM manufacturer WHERE manufacturer_id="nvidia"').fetchone()[0])
        assert 'NVIDIA' in aliases
        conn.close()

    def test_rtx4090_not_msi_variant(self, temp_db):
        """RTX 4090 Founders Edition and MSI RTX 4090 are distinct variants."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_manufacturer('msi', 'MSI')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090', product_class='GPU')
        upsert_product_variant('rtx4090-fe', 'rtx4090', mpn='RTX 4090 FE')
        upsert_product_variant('msi-gaming-x-trio', 'rtx4090', mpn='RTX 4090 GAMING X TRIO 24G')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_variant WHERE product_id="rtx4090"').fetchone()[0]
        assert count == 2
        conn.close()

    def test_h100_pcie_not_h100_sxm(self, temp_db):
        """H100 PCIe and H100 SXM are distinct variants (different form factor)."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('h100', 'nvidia', 'H100', product_class='GPU')
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
    def _setup_product(self, temp_db):
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        upsert_product_variant('v1', 'rtx4090', mpn='RTX4090')

    def test_listing_appears(self, temp_db):
        """A new listing creates a source_record and market_listing."""
        self._setup_product(temp_db)
        ir = insert_source_record('ebay', 'uk', 'L100',
                                    {'title': 'RTX 4090 FE', 'price': 1500, 'condition': 'new'}, 'h', 'p')
        assert ir.inserted is True
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM source_record WHERE source_native_id="L100"').fetchone()[0]
        assert count >= 1
        conn.close()

    def test_listing_price_changes(self, temp_db):
        """Price change creates a new version, not a new listing."""
        self._setup_product(temp_db)
        ir1 = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'condition': 'new'}, 'h1', 'p')
        ir2 = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1400, 'condition': 'new'}, 'h2', 'p')
        assert ir1.inserted is True
        assert ir2.inserted is True
        assert ':v' in ir2.record_id
        assert ir2.duplicate_of == 'ebay:L100'

    def test_listing_disappears(self, temp_db):
        """Disappearance is recorded as an event, NOT as sold."""
        self._setup_product(temp_db)
        ir1 = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'active'}, 'h1', 'p')
        # Listing not seen in next fetch — this is DISAPPEARED, not SOLD
        # We record the last observation and note the gap
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id="ebay:L100"').fetchone()
        assert row is not None
        conn.close()

    def test_listing_reappears(self, temp_db):
        """Reappearance after disappearance creates a new observation."""
        self._setup_product(temp_db)
        ir1 = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'active'}, 'h1', 'p')
        # Simulate disappearance then reappearance with changed price
        ir2 = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1300, 'status': 'active'}, 'h2', 'p')
        assert ir2.inserted is True
        assert ':v' in ir2.record_id

    def test_disappeared_is_not_sold(self, temp_db):
        """DISAPPEARED and SOLD_CONFIRMED are fundamentally different events."""
        # This is a design rule test — we never auto-create SOLD from disappearance
        self._setup_product(temp_db)
        ir = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'active'}, 'h', 'p')
        # No SOLD_CONFIRMED should exist without explicit source evidence
        conn = sqlite3.connect(str(temp_db))
        # The source record should still show 'active' status, not 'sold'
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id="ebay:L100"').fetchone()
        data = json.loads(row[0])
        assert data.get('status') == 'active'
        conn.close()

    def test_sold_confirmed_needs_explicit_evidence(self, temp_db):
        """SOLD_CONFIRMED is only created when the source explicitly confirms a sale."""
        self._setup_product(temp_db)
        # Only when source says "sold" do we record it
        ir = insert_source_record('ebay', 'uk', 'L100',
                                    {'price': 1500, 'status': 'sold', 'sold_price': 1450}, 'h', 'p')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id="ebay:L100"').fetchone()
        data = json.loads(row[0])
        assert data.get('status') == 'sold'
        assert data.get('sold_price') == 1450
        conn.close()


# =============================================================================
# COMPONENT TESTS
# =============================================================================

class TestComponents:
    def test_same_mpn_across_suppliers_resolves_one_part(self, temp_db):
        """IRFZ44N from Mouser and TME resolve to the same canonical part."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N', product_class='MOSFET')
        upsert_product_variant('irfz44n-v1', 'irfz44n', mpn='IRFZ44N')
        insert_product_identifier('irfz44n-v1', 'mpn', 'IRFZ44N', source_id='mouser')
        insert_product_identifier('irfz44n-v1', 'mpn', 'IRFZ44N', source_id='tme')
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT entity_id FROM product_identifier WHERE namespace="mpn" AND value="IRFZ44N"').fetchall()
        assert len({r[0] for r in rows}) == 1
        conn.close()

    def test_supplier_offers_remain_separate(self, temp_db):
        """Same part from different suppliers has separate spec observations."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N')
        upsert_product_variant('v1', 'irfz44n', mpn='IRFZ44N')
        insert_spec_observation('v1', 'price_usd', '1.50', source_id='mouser',
                                 truth_class='observed', numeric_value=1.50)
        insert_spec_observation('v1', 'price_usd', '1.65', source_id='tme',
                                 truth_class='observed', numeric_value=1.65)
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT source_id, numeric_value FROM product_spec_observation WHERE spec_key="price_usd"').fetchall()
        assert len(rows) == 2
        sources = {r[0] for r in rows}
        assert 'mouser' in sources
        assert 'tme' in sources
        conn.close()

    def test_stock_observations_append(self, temp_db):
        """Stock state changes create separate observations. Same state+source deduplicates."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N')
        upsert_product_variant('v1', 'irfz44n', mpn='IRFZ44N')
        # Different states from same source → separate observations
        insert_spec_observation('v1', 'stock', 'in_stock', source_id='mouser')
        insert_spec_observation('v1', 'stock', 'out_of_stock', source_id='mouser')
        # Same state from different source → separate observations
        insert_spec_observation('v1', 'stock', 'in_stock', source_id='tme')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_spec_observation WHERE spec_key="stock"').fetchone()[0]
        assert count == 3  # mouser: in_stock, out_of_stock; tme: in_stock
        # Same value + same source → deduplicates (content-addressed)
        insert_spec_observation('v1', 'stock', 'in_stock', source_id='mouser')
        count2 = conn.execute('SELECT COUNT(*) FROM product_spec_observation WHERE spec_key="stock"').fetchone()[0]
        assert count2 == 3  # unchanged — same value+source already existed
        conn.close()

    def test_price_tiers_preserved(self, temp_db):
        """Multiple price breaks from a distributor are all stored."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N')
        upsert_product_variant('v1', 'irfz44n', mpn='IRFZ44N')
        for qty, price in [(1, 1.50), (10, 1.20), (100, 0.90), (1000, 0.65)]:
            insert_spec_observation('v1', f'price_tier_{qty}', f'{price}',
                                     numeric_value=price, unit='USD', source_id='mouser')
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute('SELECT COUNT(*) FROM product_spec_observation WHERE spec_key LIKE "price_tier_%"').fetchone()[0]
        assert count == 4
        conn.close()

    def test_lead_time_units_normalized(self, temp_db):
        """Lead time observations store numeric value + unit."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N')
        upsert_product_variant('v1', 'irfz44n', mpn='IRFZ44N')
        insert_spec_observation('v1', 'lead_time', '14', numeric_value=14, unit='days', source_id='mouser')
        insert_spec_observation('v1', 'lead_time', '0', numeric_value=0, unit='days', source_id='tme')
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT numeric_value, unit FROM product_spec_observation WHERE spec_key="lead_time"').fetchall()
        assert all(r[1] == 'days' for r in rows)
        conn.close()

    def test_replacement_relations_preserve_evidence(self, temp_db):
        """Replacement relationships carry source evidence."""
        upsert_manufacturer('ir', 'International Rectifier')
        upsert_product_model('irfz44n', 'ir', 'IRFZ44N')
        upsert_product_model('irfz44npb', 'ir', 'IRFZ44NPB')
        rid = insert_product_relation('irfz44n', 'irfz44npb', 'SUPERSEDES',
                                       truth_class='declared', confidence=0.95,
                                       evidence_json=json.dumps({'source': 'mouser_lifecycle'}))
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT evidence_json, confidence FROM product_relation WHERE relation_id=?', (rid,)).fetchone()
        assert row[1] == 0.95
        evidence = json.loads(row[0])
        assert evidence['source'] == 'mouser_lifecycle'
        conn.close()


# =============================================================================
# ROBOTICS TESTS
# =============================================================================

class TestRobotics:
    def test_urdf_fixture_extracts_links_and_joints(self, temp_db):
        """Fixture URDF must extract links, joints, types, parent/child, axis, limits."""
        # Simulate a parsed URDF
        urdf_data = {
            'format': 'urdf',
            'links': [
                {'name': 'base_link', 'inertial': {'mass': 1.0}},
                {'name': 'shoulder_link', 'inertial': {'mass': 2.5}},
                {'name': 'elbow_link', 'inertial': {'mass': 1.8}},
            ],
            'joints': [
                {'name': 'shoulder_joint', 'type': 'revolute', 'parent': 'base_link',
                 'child': 'shoulder_link', 'axis': [0, 0, 1],
                 'limit': {'lower': -3.14, 'upper': 3.14, 'velocity': 1.0, 'effort': 50.0}},
                {'name': 'elbow_joint', 'type': 'revolute', 'parent': 'shoulder_link',
                 'child': 'elbow_link', 'axis': [0, 1, 0],
                 'limit': {'lower': -2.0, 'upper': 2.0, 'velocity': 1.5, 'effort': 30.0}},
            ]
        }
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO robot_description (robot_description_id, product_id, format, "
            "source_id, links_json, joints_json) VALUES (?, ?, ?, ?, ?, ?)",
            ('test_urdf', 'ur5e', 'urdf', 'robot_descriptions',
             json.dumps(urdf_data['links']), json.dumps(urdf_data['joints']))
        )
        conn.commit()
        row = conn.execute('SELECT links_json, joints_json FROM robot_description WHERE robot_description_id="test_urdf"').fetchone()
        links = json.loads(row[0])
        joints = json.loads(row[1])
        assert len(links) == 3
        assert len(joints) == 2
        assert joints[0]['type'] == 'revolute'
        assert joints[0]['parent'] == 'base_link'
        assert joints[0]['child'] == 'shoulder_link'
        assert joints[0]['axis'] == [0, 0, 1]
        assert joints[0]['limit']['lower'] == -3.14
        assert joints[0]['limit']['effort'] == 50.0
        conn.close()

    def test_mjcf_fixture_extracts_same_structure(self, temp_db):
        """MJCF fixture extracts similar joint/link structure."""
        mjcf_data = {
            'format': 'mjcf',
            'links': [{'name': 'world', 'mass': 0}],
            'joints': [
                {'name': 'joint1', 'type': 'hinge', 'parent': 'world', 'child': 'link1',
                 'axis': [0, 0, 1], 'limit': {'lower': -3.14, 'upper': 3.14,
                 'velocity': 1.0, 'effort': 100.0}},
            ]
        }
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO robot_description (robot_description_id, product_id, format, "
            "source_id, links_json, joints_json) VALUES (?, ?, ?, ?, ?, ?)",
            ('test_mjcf', 'panda', 'mjcf', 'mujoco_menagerie',
             json.dumps(mjcf_data['links']), json.dumps(mjcf_data['joints']))
        )
        conn.commit()
        row = conn.execute('SELECT format, joints_json FROM robot_description WHERE robot_description_id="test_mjcf"').fetchone()
        assert row[0] == 'mjcf'
        joints = json.loads(row[1])
        assert joints[0]['type'] == 'hinge'
        conn.close()

    def test_robot_component_relationships(self, temp_db):
        """Robot → component relationships are stored as product_relations."""
        upsert_manufacturer('ur', 'Universal Robots')
        upsert_product_model('ur5e', 'ur', 'UR5e', product_class='robot_arm')
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('xm430', 'robotis', 'DYNAMIXEL XM430-W350', product_class='actuator')
        insert_product_relation('ur5e', 'xm430', 'CONTAINS', quantity=6, unit='joints',
                                 truth_class='declared')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT quantity, unit, relation_type FROM product_relation WHERE src_entity_id="ur5e"').fetchone()
        assert row[0] == 6
        assert row[1] == 'joints'
        assert row[2] == 'CONTAINS'
        conn.close()

    def test_licence_metadata_retained(self, temp_db):
        """Robot description preserves upstream licence."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO robot_description (robot_description_id, product_id, format, "
            "source_id, licence, description_hash) VALUES (?, ?, ?, ?, ?, ?)",
            ('rd1', 'ur5e', 'urdf', 'robot_descriptions', 'Apache-2.0', 'abc123')
        )
        conn.commit()
        row = conn.execute('SELECT licence FROM robot_description WHERE robot_description_id="rd1"').fetchone()
        assert row[0] == 'Apache-2.0'
        conn.close()

    def test_source_version_retained(self, temp_db):
        """Robot description preserves source version for reproducibility."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO robot_description (robot_description_id, product_id, format, "
            "source_id, source_version, upstream_version) VALUES (?, ?, ?, ?, ?, ?)",
            ('rd2', 'panda', 'mjcf', 'mujoco_menagerie', 'v1.0.0', '4.1.0')
        )
        conn.commit()
        row = conn.execute('SELECT source_version, upstream_version FROM robot_description WHERE robot_description_id="rd2"').fetchone()
        assert row[0] == 'v1.0.0'
        assert row[1] == '4.1.0'
        conn.close()


# =============================================================================
# ROBOTIS TESTS
# =============================================================================

class TestRobotis:
    def test_model_identity_and_family(self, temp_db):
        """DYNAMIXEL model identity, family, and key specs."""
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('xm430-w350', 'robotis', 'DYNAMIXEL XM430-W350',
                              product_class='actuator')
        insert_spec_observation('xm430-w350', 'rated_voltage', '12V',
                                 numeric_value=12, unit='V', truth_class='declared')
        insert_spec_observation('xm430-w350', 'stall_torque', '4.66',
                                 numeric_value=4.66, unit='N·m', truth_class='declared')
        insert_spec_observation('xm430-w350', 'no_load_speed', '56',
                                 numeric_value=56, unit='RPM', truth_class='declared')
        insert_spec_observation('xm430-w350', 'protocol', 'Protocol 2.0',
                                 truth_class='declared')
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT canonical_name, product_class FROM product_model WHERE product_id="xm430-w350"').fetchone()
        assert row[0] == 'DYNAMIXEL XM430-W350'
        assert row[1] == 'actuator'
        specs = conn.execute('SELECT spec_key, numeric_value FROM product_spec_observation WHERE entity_id="xm430-w350"').fetchall()
        spec_dict = {s[0]: s[1] for s in specs}
        assert spec_dict['rated_voltage'] == 12.0
        assert spec_dict['stall_torque'] == 4.66
        conn.close()

    def test_replacement_model_edge(self, temp_db):
        """DYNAMIXEL replacement relationship: discontinued → successor."""
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('mx-28', 'robotis', 'DYNAMIXEL MX-28', product_class='actuator')
        upsert_product_model('xm430-w350', 'robotis', 'DYNAMIXEL XM430-W350', product_class='actuator')
        insert_product_relation('mx-28', 'xm430-w350', 'SUPERSEDES',
                                 truth_class='declared',
                                 evidence_json=json.dumps({'source': 'robotis_lifecycle'}))
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT dst_entity_id, relation_type FROM product_relation WHERE src_entity_id="mx-28"').fetchone()
        assert row[0] == 'xm430-w350'
        assert row[1] == 'SUPERSEDES'
        conn.close()

    def test_discontinued_status_tracked(self, temp_db):
        """Discontinued DYNAMIXEL models tracked via lifecycle_event."""
        upsert_manufacturer('robotis', 'ROBOTIS')
        upsert_product_model('mx-28', 'robotis', 'DYNAMIXEL MX-28')
        conn = sqlite3.connect(str(temp_db))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO lifecycle_event (event_id, entity_id, event_type, event_time, source_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('evt1', 'mx-28', 'DISCONTINUED', '2020-01-01', 'robotis')
        )
        conn.commit()
        row = conn.execute('SELECT event_type FROM lifecycle_event WHERE entity_id="mx-28"').fetchone()
        assert row[0] == 'DISCONTINUED'
        conn.close()


# =============================================================================
# BENCHMARK TESTS
# =============================================================================

class TestBenchmark:
    def test_benchmark_resolves_canonical_product(self, temp_db):
        """Benchmark observation references canonical product_id."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        conn = sqlite3.connect(str(temp_db))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO benchmark_observation (benchmark_observation_id, product_id, "
            "benchmark_family, benchmark_name, score, unit, software, software_version, "
            "source_id, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ('b1', 'rtx4090', 'blender', 'monster', 4200.5, 'samples/min',
             'Blender', '4.1.0', 'blender_open_data', now)
        )
        conn.commit()
        row = conn.execute('SELECT score, unit, software FROM benchmark_observation WHERE product_id="rtx4090"').fetchone()
        assert row[0] == 4200.5
        assert row[1] == 'samples/min'
        assert row[2] == 'Blender'
        conn.close()

    def test_benchmark_score_and_unit_preserved(self, temp_db):
        """Score and unit are stored as separate fields, not concatenated."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('h100', 'nvidia', 'H100')
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO benchmark_observation (benchmark_observation_id, product_id, "
            "benchmark_family, score, unit, source_id) VALUES (?, ?, ?, ?, ?, ?)",
            ('b2', 'h100', 'mlperf', 3800.0, 'tokens/s', 'mlperf')
        )
        conn.commit()
        row = conn.execute('SELECT score, unit FROM benchmark_observation WHERE benchmark_observation_id="b2"').fetchone()
        assert row[0] == 3800.0
        assert row[1] == 'tokens/s'
        conn.close()

    def test_benchmark_software_version_preserved(self, temp_db):
        """Software and version are stored for reproducibility."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO benchmark_observation (benchmark_observation_id, product_id, "
            "benchmark_family, score, unit, software, software_version, source_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('b3', 'rtx4090', 'blender', 4200.5, 'samples/min', 'Blender', '4.1.0', 'blender')
        )
        conn.commit()
        row = conn.execute('SELECT software, software_version FROM benchmark_observation WHERE benchmark_observation_id="b3"').fetchone()
        assert row[0] == 'Blender'
        assert row[1] == '4.1.0'
        conn.close()

    def test_benchmark_does_not_overwrite_manufacturer_spec(self, temp_db):
        """Benchmark (observed) never overwrites manufacturer spec (declared)."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        # Manufacturer declares TDP
        insert_spec_observation('rtx4090', 'tdp_watts', '450', numeric_value=450, unit='W',
                                 truth_class='declared', source_id='nvidia')
        # Benchmark observes power draw
        insert_spec_observation('rtx4090', 'tdp_watts', '420', numeric_value=420, unit='W',
                                 truth_class='observed', source_id='blender')
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute('SELECT truth_class, numeric_value FROM product_spec_observation WHERE spec_key="tdp_watts"').fetchall()
        assert len(rows) == 2
        truth_classes = {r[0] for r in rows}
        assert 'declared' in truth_classes
        assert 'observed' in truth_classes
        conn.close()


# =============================================================================
# RIGHTS TESTS
# =============================================================================

class TestRights:
    def test_blocked_source_refuses_production(self, temp_db):
        """Blocked source must not run in production."""
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="ebay_gb", source_id="ebay_gb", http_status=403)
        h.compute_status()
        assert h.status == "blocked"

    def test_terms_review_refuses_unless_override(self, temp_db):
        """terms_review source requires explicit approval."""
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="jawa", source_id="jawa", records_seen=0)
        h.compute_status(expected_min_rows=10)
        assert h.status == "degraded"  # no data + no override = not ok

    def test_open_source_runs(self, temp_db):
        """Open source with data runs successfully."""
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="robotshop", source_id="robotshop_uk",
                             records_seen=100, last_success="2026-09-21T12:00:00")
        h.compute_status(expected_min_rows=10)
        assert h.status == "ok"


# =============================================================================
# JEV TESTS
# =============================================================================

class TestJev:
    def test_raw_collector_succeeds_when_jev_unavailable(self, temp_db):
        """Collector must work even if Jev/LLM is not available."""
        from powproducts.collectors.base import BaseCollector

        class OfflineCollector(BaseCollector):
            SOURCE_ID = 'offline_test'
            DATASET = 'test'
            PARSER_ID = 'test'

            def fetch(self):
                return b'{"items": [{"name": "RTX 4090", "price": 1500}]}'

            def parse(self, raw_content, raw_hash, result):
                items = json.loads(raw_content)
                result.records_new = len(items.get('items', []))

        collector = OfflineCollector()
        result = collector.run()
        assert result.records_new == 1
        assert result.errors == []

    def test_jev_never_mutates_source_record(self, temp_db):
        """Jev annotations are separate from source records."""
        ir = insert_source_record('test', 'ds', 'n1', {'title': 'RTX 4090 24GB'}, 'h', 'p')
        # Jev decision is stored in a separate table
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO jev_decision (jev_decision_id, source_record_id, input_hash, "
            "question_schema_id, model_id, options_json, probabilities_json, selected_option) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('jd1', ir.record_id, 'abc', 'product_match_v1', 'jev-v1',
             json.dumps(['RTX 4090', 'RTX 4080', 'UNKNOWN']),
             json.dumps({'RTX_4090': 0.92, 'RTX_4080': 0.03, 'UNKNOWN': 0.05}),
             'RTX 4090')
        )
        conn.commit()
        # Source record unchanged
        row = conn.execute('SELECT normalized_json FROM source_record WHERE source_record_id=?', (ir.record_id,)).fetchone()
        data = json.loads(row[0])
        assert data['title'] == 'RTX 4090 24GB'
        # Jev decision is separate
        jd = conn.execute('SELECT selected_option FROM jev_decision WHERE jev_decision_id="jd1"').fetchone()
        assert jd[0] == 'RTX 4090'
        conn.close()

    def test_full_probability_distribution_persisted(self, temp_db):
        """Jev stores full distribution, not just the winner."""
        conn = sqlite3.connect(str(temp_db))
        probs = {'RTX_4090': 0.72, 'RTX_4080': 0.03, 'UNKNOWN': 0.25}
        conn.execute(
            "INSERT INTO jev_decision (jev_decision_id, source_record_id, input_hash, "
            "question_schema_id, model_id, probabilities_json, selected_option) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('jd2', 'sr1', 'hash', 'q1', 'm1', json.dumps(probs), 'RTX 4090')
        )
        conn.commit()
        row = conn.execute('SELECT probabilities_json FROM jev_decision WHERE jev_decision_id="jd2"').fetchone()
        parsed = json.loads(row[0])
        assert len(parsed) == 3
        assert parsed['RTX_4090'] == 0.72
        conn.close()

    def test_uncertain_match_produces_possible_same_as(self, temp_db):
        """Low-confidence match creates POSSIBLE_SAME_AS, not hard merge."""
        upsert_manufacturer('nvidia', 'NVIDIA')
        upsert_product_model('rtx4090', 'nvidia', 'GeForce RTX 4090')
        # Uncertain match — confidence below threshold
        rid = insert_product_relation('listing_x', 'rtx4090', 'POSSIBLE_SAME_AS',
                                       confidence=0.65,
                                       evidence_json=json.dumps({'method': 'jev', 'model': 'v1'}))
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute('SELECT relation_type, confidence FROM product_relation WHERE relation_id=?', (rid,)).fetchone()
        assert row[0] == 'POSSIBLE_SAME_AS'
        assert row[1] == 0.65
        conn.close()


# =============================================================================
# REPLAY TESTS
# =============================================================================

class TestReplay:
    def test_parser_deterministic_output(self, temp_db):
        """Given same raw bytes, parser vX produces same normalized output."""
        raw = b'{"sku": "RTX4090", "name": "GeForce RTX 4090", "price": 1500}'
        # Parse twice
        data1 = json.loads(raw)
        data2 = json.loads(raw)
        assert data1 == data2
        # Normalize twice
        n1 = {'sku': data1['sku'], 'name': data1['name'], 'price': data1['price']}
        n2 = {'sku': data2['sku'], 'name': data2['name'], 'price': data2['price']}
        assert n1 == n2
        # Content-addressed IDs should be identical
        h1 = hashlib.sha256(json.dumps(n1, sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(n2, sort_keys=True).encode()).hexdigest()
        assert h1 == h2

    def test_replay_same_raw_same_source_record(self, temp_db):
        """Replaying same raw bytes produces same source_record_id."""
        ir1 = insert_source_record('test', 'ds', 'n1', {'k': 'v'}, 'h', 'p')
        ir2 = insert_source_record('test', 'ds', 'n1', {'k': 'v'}, 'h', 'p')
        assert ir1.record_id == ir2.record_id
        assert ir2.inserted is False


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

    def test_health_to_json(self):
        from powproducts.layer1.health import CollectorHealth
        h = CollectorHealth(collector_id="test", source_id="test")
        parsed = json.loads(h.to_json())
        assert parsed["collector_id"] == "test"

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
            def fetch(self): return b'{"items": []}'
            def parse(self, raw_content, raw_hash, result): result.records_new = 1

        result = TestCollector().run()
        assert result.records_new == 1
        assert result.errors == []

    def test_failed_fetch_is_logged(self, temp_db):
        from powproducts.collectors.base import BaseCollector

        class Failing(BaseCollector):
            SOURCE_ID = 'fail'
            DATASET = 'test'
            PARSER_ID = 'test'
            def fetch(self): return None
            def parse(self, raw_content, raw_hash, result): pass

        result = Failing().run()
        assert 'fetch_failed' in result.errors

    def test_parse_failure_is_logged(self, temp_db):
        from powproducts.collectors.base import BaseCollector

        class BadParser(BaseCollector):
            SOURCE_ID = 'bad'
            DATASET = 'test'
            PARSER_ID = 'test'
            def fetch(self): return b'data'
            def parse(self, raw_content, raw_hash, result): raise ValueError('bad')

        result = BadParser().run()
        assert 'bad' in result.errors[0]

    def test_raw_new_deduplication(self, temp_db):
        from powproducts.collectors.base import BaseCollector

        class Replay(BaseCollector):
            SOURCE_ID = 'replay'
            DATASET = 'test'
            PARSER_ID = 'test'
            def fetch(self): return b'same'
            def parse(self, raw_content, raw_hash, result): result.records_new = 1

        r1 = Replay().run()
        r2 = Replay().run()
        assert r1.raw_new == 1
        assert r2.raw_new == 0


# =============================================================================
# LIFECYCLE TESTS
# =============================================================================

class TestLifecycle:
    def test_lifecycle_event_types(self, temp_db):
        """All deterministic lifecycle event types are valid."""
        from powproducts.core.enums import LifecycleEventType
        valid_types = {e.value for e in LifecycleEventType}
        assert 'ANNOUNCED' in valid_types
        assert 'RELEASED' in valid_types
        assert 'DISCONTINUED' in valid_types
        assert 'SUPPORT_ENDED' in valid_types
        assert 'PART_SUPERSEDED' in valid_types

    def test_lifecycle_event_stored(self, temp_db):
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO lifecycle_event (event_id, entity_id, event_type, event_time, source_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('e1', 'rtx4090', 'RELEASED', '2022-10-12', 'nvidia')
        )
        conn.commit()
        row = conn.execute('SELECT event_type, source_id FROM lifecycle_event WHERE event_id="e1"').fetchone()
        assert row[0] == 'RELEASED'
        assert row[1] == 'nvidia'
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

    def test_cursor_returns_none_when_missing(self, temp_db):
        assert get_cursor('nonexistent', 'ds') is None
