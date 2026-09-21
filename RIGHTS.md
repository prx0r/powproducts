# RIGHTS

Source rights machine-readable.

## Open Sources

| Source | Licence | Raw Retention | Commercial | Redistribution | Automation |
|--------|---------|---------------|------------|----------------|------------|
| PCI IDs | Open | Yes | Yes | Yes | Yes |
| OSHWA | Open | Yes | Yes | Yes | Yes |
| ROBOTIS docs | Public | Yes | Unknown | Restricted | Yes |
| robot_descriptions.py | Mixed | Yes | Per-model | Per-model | Yes |
| MuJoCo Menagerie | Mixed | Yes | Per-model | Per-model | Yes |
| Blender Open Data | Open | Yes | Yes | Yes | Yes |
| MLPerf | Open | Yes | Yes | Yes | Yes |

## Blocked Sources

| Source | Status | Reason |
|--------|--------|--------|
| eBay GB | blocked | VPS IP blocked (403) |
| CeX | blocked | VPS IP blocked (403) |

## Terms Review Required

| Source | Status | What to check |
|--------|--------|---------------|
| Jawa | terms_review | Public sold listings, automated archival rights unclear |
| Cash Converters | terms_review | UK second-hand, no API |
| Back Market | terms_review | Professional refurb, no API |
| Radwell | terms_review | Industrial parts, strategic value |
| MicroBT store | terms_review | Manufacturer pricing, automated access unclear |

## Permission Required

| Source | Status | What's needed |
|--------|--------|---------------|
| Mouser | permission_required | API key registration |
| TME | permission_required | API key registration |
| DigiKey | permission_required | API key registration |
| Farnell | permission_required | API key registration |
| PartsDB | permission_required | API key registration |

## Policy

- No proxy gymnastics to bypass 403s
- No residential proxies to bypass access restrictions
- No Apify or anti-bot tooling as canonical strategy
- Prefer official APIs or clearly permissible public datasets
- Blocked collectors remain as code/tests but disabled in production
