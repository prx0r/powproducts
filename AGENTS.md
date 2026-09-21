# Agents.md — PowProducts

## What Actually Works

| Component | Status | Evidence |
|-----------|--------|----------|
| Persistence kernel | ✅ | Ported from Repair Garden, all tests green |
| Canonical product schema | ✅ | manufacturer, product_model, product_variant, product_identifier, product_relation, product_spec_observation |
| Market data schema | ✅ | market_listing, market_observation, lifecycle_event, benchmark_observation |
| Robot description schema | ✅ | robot_description, jev_decision |
| Raw blob storage | ✅ | Content-addressed, gzip compressed, idempotent |
| Source record versioning | ✅ | Content-addressed version IDs, payload hash comparison |
| BaseCollector | ✅ | try/finally logging, parse(result) contract |
| CollectorHealth | ✅ | Standardized health state for all collectors |
| Tests | ✅ | 35+ passing tests |

## How to Run

```bash
# Tests
POWPRODUCTS_DB=/tmp/test.db python3 -m pytest tests/ -v

# Initialize DB
python3 -m powproducts.shared.db

# Check DB status
python3 -m powproducts.shared.db status
```

## What Belongs Here

**powproducts** owns:
- Physical product identity (manufacturer → family → model → variant)
- Component identity (MPN, GTIN, cross-references)
- Product specifications (as observations, not eternal truth)
- Market listings and observations (price, stock, availability)
- Lifecycle events (ANNOUNCED, DISCONTINUED, etc.)
- Benchmark observations (Blender, MLPerf)
- Robot descriptions (URDF, MJCF)
- Hardware identity (PCI IDs, OSHWA)

**repair** owns:
- What breaks, why, fault patterns
- Intervention attempts, parts used
- Repair outcomes, survival data

**powpowpow** owns:
- Workload economics (mining, AI rental, yield)
- Best workload selection
- Revenue calculations

## File Layout

```
powproducts/
├── shared/           db.py (schema authority), persist.py
├── core/             models, enums, normalize, resolve
├── collectors/       base.py + per-source collectors
├── parsers/          urdf, mjcf, marketplace, benchmark
├── semantic/         jev.py
├── layer1/           health.py, manifests/
├── registry/         sources.yaml, product_universe.yaml, etc.
├── export_k1.py      k1 kernel export
├── daemon.py         scheduled collection
└── cli.py            command interface

tests/                test suite
warehouse/            SQLite database + raw blobs
```
