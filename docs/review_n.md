# Review N — Kernel Hardening

**Date:** 21 September 2026
**Reviewer:** architecture review
**HEAD:** e3cdaa8

## Assessment

Structurally strong extraction from /repair. Correct domain separation. But not yet a trustworthy running Layer-1 garden. Operational/provenance issues, not missing feature count.

## P0 Fixes (this pass)

| # | Issue | Fix |
|---|-------|-----|
| 1 | Daemon cannot instantiate collectors | Explicit module:class registry |
| 2 | RobotShop doesn't feed ProductGraph | Resolve manufacturer → model → variant → listing |
| 3 | Per-item provenance broken | Carry acquisition hash per item |
| 4 | Silent 403/empty-success | Propagate HTTP failures, enforce manifest health |
| 5 | product_identifier idempotency false | UNIQUE constraint |
| 6 | Product relations discard evidence | Split edge from evidence |
| 7 | Foreign keys not enforced | PRAGMA foreign_keys=ON |
| 8 | Rights policy not enforced | Executable pre-run gate |
| 9 | Product/variant ID edge cases | Reject blank fields |
| 10 | variant_manufacturer_id missing | Add column |
| 11 | price_type not exposed | Add to market_observation |
| 12 | No market_event table | Add with listing_seen |
| 13 | source_record acquisition linkage broken | Fix insert_source_record |
| 14 | RobotShop parsing too silent | Replace except:pass with counters |
| 15 | RobotShop rights inconsistent | → terms_review |
| 16 | derived_fact still in schema | Remove |
| 17 | pow.systems naming wrong | Fix |
| 18 | No CI | Add GitHub Actions |
| 19 | Tests too kernel-focused | Add fixture e2e tests |
| 20 | Schema evolution painful | Add migrations/ |

## Verdict

Do not build PCI, ROBOTIS, TME, Mouser, MLPerf yet.

Do one hardening pass first. Prove one source traverses the entire architecture with perfect temporal provenance.

Once RobotShop produces:

```
RAW PAGE → SOURCE RECORD → CANONICAL PRODUCT → VARIANT → LISTING → PRICE/STOCK → NEXT OBSERVATION → STATE CHANGE
```

with every arrow replayable to raw evidence, then the garden is planted.
