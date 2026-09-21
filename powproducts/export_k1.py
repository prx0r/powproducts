"""K1 Export — export PowProducts as JSONL for the k1 kernel.

Exports:
- NODE: manufacturer, product, variant, part
- EDGE: VARIANT_OF, CONTAINS, COMPATIBLE_WITH, REPLACES, etc.
- OBSERVATION: price, stock, availability, spec, benchmark
- EVENT: price changes, stock changes, lifecycle changes
- EVIDENCE: source references / provenance
"""

import json
import os
import sqlite3
from pathlib import Path
from powproducts.shared.db import get_db_path


def export_nodes(conn, output_dir):
    """Export canonical product nodes."""
    path = output_dir / 'nodes.jsonl'
    count = 0
    with open(path, 'w') as f:
        # Manufacturers
        for row in conn.execute('SELECT * FROM manufacturer'):
            node = {
                'type': 'manufacturer',
                'id': row[0],
                'name': row[1],
                'country': row[3],
                'website': row[4],
            }
            f.write(json.dumps(node, default=str) + '\n')
            count += 1

        # Product models
        for row in conn.execute('SELECT * FROM product_model'):
            node = {
                'type': 'product',
                'id': row[0],
                'manufacturer_id': row[1],
                'family_id': row[2],
                'name': row[3],
                'model_number': row[4],
                'product_class': row[5],
            }
            f.write(json.dumps(node, default=str) + '\n')
            count += 1

        # Variants
        for row in conn.execute('SELECT * FROM product_variant'):
            node = {
                'type': 'variant',
                'id': row[0],
                'product_id': row[1],
                'sku': row[2],
                'mpn': row[3],
                'gtin': row[4],
            }
            f.write(json.dumps(node, default=str) + '\n')
            count += 1

    return count


def export_edges(conn, output_dir):
    """Export product relations as edges."""
    path = output_dir / 'edges.jsonl'
    count = 0
    with open(path, 'w') as f:
        for row in conn.execute('SELECT * FROM product_relation'):
            edge = {
                'type': 'relation',
                'id': row[0],
                'src': row[1],
                'dst': row[2],
                'relation': row[3],
                'truth_class': row[8],
                'confidence': row[9],
                'source': row[10],
            }
            f.write(json.dumps(edge, default=str) + '\n')
            count += 1

    return count


def export_observations(conn, output_dir):
    """Export spec observations and market observations."""
    path = output_dir / 'observations.jsonl'
    count = 0
    with open(path, 'w') as f:
        # Spec observations
        for row in conn.execute('SELECT * FROM product_spec_observation'):
            obs = {
                'type': 'spec_observation',
                'id': row[0],
                'entity_id': row[1],
                'spec_key': row[2],
                'value': row[3],
                'numeric_value': row[4],
                'unit': row[5],
                'source': row[6],
                'truth_class': row[8],
            }
            f.write(json.dumps(obs, default=str) + '\n')
            count += 1

        # Market observations
        for row in conn.execute('SELECT * FROM market_observation'):
            obs = {
                'type': 'market_observation',
                'id': row[0],
                'source_record_id': row[1],
                'source_native_id': row[4],
                'observation_type': row[5],
                'observed_at': row[6],
                'price': row[7],
                'currency': row[10],
                'stock': row[11],
                'availability': row[12],
                'condition': row[13],
                'market': row[14],
            }
            f.write(json.dumps(obs, default=str) + '\n')
            count += 1

        # Benchmark observations
        for row in conn.execute('SELECT * FROM benchmark_observation'):
            obs = {
                'type': 'benchmark_observation',
                'id': row[0],
                'product_id': row[1],
                'benchmark_family': row[3],
                'benchmark_name': row[4],
                'score': row[6],
                'unit': row[7],
                'software': row[10],
                'software_version': row[11],
                'source': row[12],
            }
            f.write(json.dumps(obs, default=str) + '\n')
            count += 1

    return count


def export_events(conn, output_dir):
    """Export lifecycle events."""
    path = output_dir / 'events.jsonl'
    count = 0
    with open(path, 'w') as f:
        for row in conn.execute('SELECT * FROM lifecycle_event'):
            event = {
                'type': 'lifecycle_event',
                'id': row[0],
                'entity_id': row[1],
                'event_type': row[2],
                'event_time': row[3],
                'source': row[5],
            }
            f.write(json.dumps(event, default=str) + '\n')
            count += 1

    return count


def export_evidence(conn, output_dir):
    """Export source records as evidence."""
    path = output_dir / 'evidence.jsonl'
    count = 0
    with open(path, 'w') as f:
        for row in conn.execute(
            'SELECT source_record_id, source_id, dataset, source_native_id, '
            'retrieved_at, payload_hash, parser_id, parser_version '
            'FROM source_record LIMIT 10000'
        ):
            ev = {
                'type': 'evidence',
                'source_record_id': row[0],
                'source_id': row[1],
                'dataset': row[2],
                'native_id': row[3],
                'retrieved_at': row[4],
                'payload_hash': row[5],
                'parser': row[6],
                'parser_version': row[7],
            }
            f.write(json.dumps(ev, default=str) + '\n')
            count += 1

    return count


def export_all(output_dir=None):
    """Export all data as JSONL files."""
    if output_dir is None:
        output_dir = Path(__file__).parent / 'warehouse' / 'k1_export'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = get_db_path()
    if not db_path.exists():
        print(f'Database not found: {db_path}')
        return {}

    conn = sqlite3.connect(str(db_path))

    stats = {
        'nodes': export_nodes(conn, output_dir),
        'edges': export_edges(conn, output_dir),
        'observations': export_observations(conn, output_dir),
        'events': export_events(conn, output_dir),
        'evidence': export_evidence(conn, output_dir),
    }

    conn.close()

    # Write manifest
    manifest = {
        'exported_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'stats': stats,
        'db_path': str(db_path),
    }
    with open(output_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)

    total = sum(stats.values())
    print(f'K1 export complete: {total} records → {output_dir}')
    for k, v in stats.items():
        print(f'  {k}: {v:,}')

    return stats


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else None
    export_all(out)
