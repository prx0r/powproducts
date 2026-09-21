# Migration — Repair → PowProducts

## Source State

```
repair_source_commit: d9a5839d0b202076f2d0c8299a72e8729565081f
migration_date: 2026-09-21
test_counts_before: 27 (all passing)
```

## What Was Copied

### Kernel (modified for PowProducts)
- `shared/db.py` → `powproducts/shared/db.py` — renamed REPAIR_DB → POWPRODUCTS_DB, added product schema tables
- `shared/persist.py` → `powproducts/shared/persist.py` — renamed imports, added product upsert functions
- `collectors/base.py` → `powproducts/collectors/base.py` — changed User-Agent to PowProducts/1.0
- `layer1/health.py` → `powproducts/layer1/health.py` — unchanged
- `tests/test_core.py` → `powproducts/tests/test_core.py` — added product identity tests

### Not Copied (belongs to repair)
- Open Repair collector
- OPSS repair/safety outcome logic
- Repair-specific schemas (FaultRecord, PartListing, RepairEconomics, etc.)
- Planning, Land Registry, DVLA/MOT, Companies House data
- Electricity maps, UK workforce, grid data
- Repair economics, fault models, repair verdicts

## Schema Changes

Added to canonical schema:
- manufacturer
- product_family
- product_model
- product_variant
- product_identifier
- product_relation
- product_spec_observation
- market_listing (resolved to canonical products)
- lifecycle_event
- benchmark_observation
- robot_description
- jev_decision

Added indexes for product identity resolution.

## Test Counts

```
test_counts_after: 35+ (all passing)
```

## No Destructive Changes

Nothing was modified or deleted from `/repair`.
The repair database remains at `warehouse/repair.db` with 305K+ records.
