# Proposal — Next Dev Steps

**Date:** 21 September 2026

## Current State

Phases A-C complete:
- Persistence kernel extracted from repair
- Canonical product model (20 tables) with deterministic IDs
- RobotShop collector working
- 37 tests passing
- All documentation in place

## What Matters Next

The northstar says: **start the ephemeral component/secondary-market/manufacturer clocks**.

The key insight from the dev instructions is that some data is **irreversible** — if you don't capture a marketplace price today, that observation is gone forever. Static data (PCI IDs, robot descriptions) can always be fetched later. So the priority order should be:

1. **Clocks that lose data if we don't run them now** (marketplace, manufacturer pricing)
2. **Identity substrates that enable resolution** (PCI IDs, ROBOTIS specs)
3. **Robot descriptions that inform the graph** (robot_descriptions.py, MuJoCo)

## Proposed Build Order

### Phase D — Identity Substrate (Week 1)

**Why first:** Without hardware identity, we can't resolve what products actually are. PCI IDs give us GPU/NIC/controller identity. ROBOTIS gives us actuator lifecycle. These are foundations everything else builds on.

| Collector | Source | Effort | Value |
|-----------|--------|--------|-------|
| `pci_ids.py` | pci-ids.ucw.cz | Low | High — instant GPU/NIC identity |
| `robotis.py` | emanual.robotis.com | Medium | High — actuator specs + replacement edges |
| `robot_descriptions.py` | GitHub | Medium | High — 190+ robot URDF/MJCF |
| `mujoco_menagerie.py` | GitHub | Medium | Medium — curated robot models |
| `oshwa.py` | certificationapi.oshwa.org | Low | Medium — open hardware registry |

**Test strategy:** Each collector gets a fixture test with canned HTTP responses. Verify: raw blob stored, source records created, product identities resolved, specs populated.

### Phase E — Component Clocks (Week 1-2)

**Why second:** These are the ephemeral clocks. Component prices and stock change daily. If we don't start them now, we lose the historical tape.

| Collector | Source | Effort | Value |
|-----------|--------|--------|-------|
| `tme.py` | TME API | Medium | High — UK/EU robotics components |
| `mouser.py` | Mouser API | Medium | High — stock + lifecycle + replacement |

Both need API keys (free). These should not block Phase D.

**Key design decision:** Component collectors should use the `product_identifier` table for MPN resolution. Same MPN across Mouser/TME resolves to one canonical part. Supplier offers remain separate (different prices, stock, lead times).

### Phase F — Compute/ASIC (Week 2)

| Collector | Source | Effort | Value |
|-----------|--------|--------|-------|
| `blender_open_data.py` | opendata.blender.org | Low | High — GPU benchmark history |
| `mlperf.py` | GitHub mlcommons | Medium | Medium — AI inference benchmarks |
| `microbt.py` | shop.whatsminer.com | Low | High — manufacturer pricing clock |

MicroBT is a genuine manufacturer-market clock — this is one of the few sources where we can observe official pricing.

### Phase G — Market Expansion (Week 3, after API keys)

| Collector | Source | Effort | Value |
|-----------|--------|--------|-------|
| `ebay_browse.py` | eBay Browse API | High | High — UK marketplace tape |
| `partsdb.py` | PartsDB API | Low | Medium — component cross-refs |

eBay needs API key registration. PartsDB needs API key (free, 100/day).

### Phase H — Integration (Week 3-4)

- `export_k1.py` — clean k1 export (fix repair's listing/product conflation)
- `daemon.py` — already built, needs collector registration
- powops health monitoring
- R2 backup configuration

## Architecture Decisions

### 1. MPN-First Resolution

Every component collector normalizes MPNs. When TME and Mouser both list "IRFZ44N", they resolve to the same canonical part. But their stock observations, pricing, and lead times remain separate observations on that part.

### 2. Robot Graph Depth

For each robot in the universe, we want:

```
robot → joints → actuators → controllers → encoders → reducers
```

This means parsing URDF/MJCF to extract joint/actuator requirements, then linking to DYNAMIXEL specs. A UR5e has 6 joints → 6 actuators → what DYNAMIXEL models match those torque/speed requirements?

This is the robotics-ready graph the northstar describes.

### 3. Benchmark as Observation, Not Truth

Blender scores and MLPerf results are stored as `benchmark_observation` with `truth_class=observed`. They never overwrite manufacturer specs (`truth_class=declared`). A GPU's TDP from NVIDIA is `declared`. Its measured power draw in a benchmark is `observed`. Both coexist.

### 4. Disappearance ≠ Sold

Carried forward from repair: marketplace disappearance is `DISAPPEARED`, not `SOLD_CONFIRMED`. Only explicit sale confirmation creates `SOLD_CONFIRMED`. This rule must be in every marketplace collector's parse logic.

## What NOT to Build Yet

- Dashboard
- Graph visualization
- AI/LLM integration
- Deprecation models
- Repair profitability
- Fair value calculations
- Any Layer-2 economics

The garden needs to grow first. Dashboards come after there's something to dashboard.

## Success Criteria for Next Phase

After implementing Phases D-F, demonstrate:

1. PCI IDs loaded (vendor/device table populated)
2. ROBOTIS DYNAMIXEL specs loaded (at least current + discontinued families)
3. At least 10 robot descriptions parsed (URDF/MJCF → joints/links)
4. At least 50 benchmark observations imported (Blender + MLPerf)
5. MicroBT official pricing clock running
6. Every source preserves raw evidence
7. Health report works
8. Test suite passes
9. Daemon can restart safely

## Open Questions

1. **TME API credentials** — do we have them or need to register?
2. **Mouser API credentials** — same question
3. **RobotShop collector reliability** — does it still work from this VPS? The repair version was working.
4. **Product universe seeding** — should we pre-populate manufacturer/product_model entries for the tracked robotics universe, or let collectors create them lazily?

Recommendation: lazy creation. Collectors create manufacturer/product records as they encounter them. This avoids maintaining a giant seed list that drifts from reality.
