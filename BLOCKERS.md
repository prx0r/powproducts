# BLOCKERS

No vague blockers. Every entry has: source, exact failure, what was tried, legal alternative, human action required.

## Currently Blocked

| Source | Failure | HTTP Status | Tried | Alternative | Human Action |
|--------|---------|-------------|-------|-------------|--------------|
| eBay GB | VPS IP blocked | 403 | Direct HTTP | Official eBay Browse API | Register for API key ($0 free tier) |
| CeX | VPS IP blocked | 403 | Direct HTTP | None (no official API) | Run from non-VPS machine or wait |
| Mouser | No API key | — | — | Official Mouser Search API (free, 30/min, 1000/day) | Register at mouser.com/api |
| TME | No API key | — | — | Official TME API v2.0 | Register at api.tme.eu |
| DigiKey | No API key | — | — | Official DigiKey Product Info API | Register at developer.digikey.com |
| Farnell | No API key | — | — | Official element14 API | Register at partner.element14.com |
| PartsDB | No API key | — | — | Official PartsDB API (free, 100/day) | Register at partsdb.io |

## Not Blocked

| Source | Status |
|--------|--------|
| RobotShop | ✅ Works |
| PCI IDs | ✅ Public download |
| OSHWA | ✅ Public API |
| ROBOTIS | ✅ Public docs |
| robot_descriptions.py | ✅ Public GitHub |
| MuJoCo Menagerie | ✅ Public GitHub |
| Blender Open Data | ✅ Public download |
| MLPerf | ✅ Public GitHub |
