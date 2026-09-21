# PowProducts

Canonical physical product identity, component, compatibility and market-state garden.

Part of **pw.systems** — `powproducts.pw.systems`

> physical things exist → what are they → what works with what → what do they cost → how does state change through time

## What This Is

A Data Garden for physical products: GPUs, CPUs, ASICs, robots, actuators, sensors, electronic components, and anything else with a model number.

It answers:
- What physical things exist?
- What are their exact models / variants / part numbers?
- What works with what?
- What are their declared capabilities?
- What do they cost?
- How available are they?
- How does their market state change through time?

It is **not**:
- A valuation engine
- A recommendation engine
- The repair system
- The compute-yield system

## pw.systems

- `powproducts.pw.systems` — this repo (physical product identity + market state)
- `repair.pw.systems` — what breaks, why, intervention, outcome
- `crypto.pw.systems` — PowPowPow (PoW chain economics)
- `powuk.pw.systems` — UK physical capacity / constraints
- `powstock.pw.systems` — companies / securities / capital flows

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
POWPRODUCTS_DB=/tmp/test.db python3 -m pytest tests/ -v

# Initialize DB
python3 -m powproducts.shared.db

# Check DB status
python3 -m powproducts.shared.db status
```

## Architecture

```
Manufacturer → Product Family → Product Model → Variant → Market Listing
                                                        ↓
                                              continuous observations
                                                        ↓
                                               price / stock / availability
                                                        ↓
                                                    HISTORY
```

## Data Model

See `DATA_MODEL.md` for full schema.

Core entities:
- **Manufacturer** — company identity
- **ProductFamily** — product line (e.g. GeForce RTX 40)
- **ProductModel** — specific product (e.g. RTX 4090)
- **ProductVariant** — exact SKU (e.g. MSI Gaming X Trio)
- **ProductIdentifier** — MPN, GTIN, SKU, etc.
- **ProductRelation** — VARIANT_OF, COMPATIBLE_WITH, REPLACES, etc.
- **ProductSpecObservation** — specs as observations (never overwrite)
- **MarketListing** — resolved marketplace listings
- **MarketObservation** — price/stock/availability time series
- **LifecycleEvent** — ANNOUNCED, RELEASED, DISCONTINUED, etc.
- **BenchmarkObservation** — Blender, MLPerf, etc.

## Sources

See `SOURCES.md` for every source with status, rights, and cadence.

## Development

```bash
# Tests
POWPRODUCTS_DB=/tmp/test.db python3 -m pytest tests/ -v

# Ruff
ruff check powproducts/ tests/
```
