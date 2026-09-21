# POWPRODUCTS — COMPREHENSIVE DEV INSTRUCTIONS

**Date:** 22 September 2026

> A continuously growing, provenance-preserving historical graph of physical products, components, specifications, compatibility, lifecycle and market state.

## 0. Mission

Create a new repository:

`prx0r/powproducts`

Its purpose is:

> **A continuously growing, provenance-preserving historical graph of physical products, components, specifications, compatibility, lifecycle and market state.**

This is Layer 1.

It is not a valuation engine.

It is not a recommendation engine.

It is not the repair system.

It is not the compute-yield system.

It is not POW Flow.

It is not POW AI.

The permanent distinction is:

```text
powproducts
WHAT PHYSICAL THINGS EXIST?
WHAT ARE THEY MADE OF?
WHAT ARE THEIR EXACT MODELS / VARIANTS / PART NUMBERS?
WHAT WORKS WITH WHAT?
WHAT ARE THEIR DECLARED CAPABILITIES?
WHAT DO THEY COST?
HOW AVAILABLE ARE THEY?
HOW DOES THEIR MARKET STATE CHANGE THROUGH TIME?

repair
WHAT BREAKS?
WHY?
WHAT INTERVENTION WAS ATTEMPTED?
WHICH PART WAS ACTUALLY USED?
DID THE REPAIR WORK?
HOW LONG DID THE REPAIR LAST?

powpowpow
WHAT ECONOMIC WORK CAN COMPUTE HARDWARE PERFORM?
MINING?
AI?
RENTAL?
WHAT IS ITS PRODUCTIVE YIELD?

powuk
WHERE IS IT?
WHAT UK PHYSICAL CAPACITY / LABOUR / GRID / PLANNING CONSTRAINTS EXIST?

powstock
WHAT COMPANIES / SECURITIES / CAPITAL FLOWS ARE EXPOSED?

LATER:
powflow / powai / powrobot
```

The governing POW principle remains:

> `unique transformation × continuous collection × time`

Raw data by itself is not the moat. 

For `powproducts`, the valuable historical tape is:

```text
exact product identity
+
exact product relationships
+
market observations
+
availability
+
stock
+
lead time
+
new/used/broken/parts prices
+
lifecycle transitions
+
compatibility transitions
+
time
```

---

# 1. DO NOT REWRITE THE WORKING REPAIR KERNEL

The current `/repair` repository already has useful infrastructure.

Reuse/extract:

```text
shared/db.py
shared/persist.py
collectors/base.py
layer1/health.py
layer1/health_schema.yaml
source-manifest pattern
raw blob storage
raw acquisition receipts
source_record versioning
source cursors
collector run history
market_observation append semantics
k1 export pattern
tests for collector persistence
```

Current useful collectors to migrate/adapt:

```text
robotshop_collector.py
ebay_3market_collector.py
partsdb_collector.py

possibly:
cex_collector.py       -- disabled until legitimate access works
trade_collector.py     -- only selected product categories
```

Do **not** copy these into `powproducts`:

```text
Open Repair collector
OPSS repair/safety outcome logic
planning data
Land Registry
DVLA/MOT
Companies House
electricity maps
UK workforce
grid
general property data
repair economics
fault models
repair verdicts
```

Those belong elsewhere.

Do not delete anything from `/repair` until `/powproducts` has passed parity tests and has run successfully in parallel.

---

# 2. FIRST ACTION: FREEZE THE CURRENT REPAIR STATE

Before extraction:

```text
1. Record current repair HEAD SHA.
2. Run complete repair tests.
3. Save test output.
4. Save current DB row counts by table/source.
5. Copy current source registry.
6. Copy current ptech_registry research.
7. Back up repair SQLite database.
8. Do not modify historical raw blobs.
```

Create a migration note containing:

```text
repair_source_commit
migration_date
files_copied
files_modified
sources_migrated
sources_remaining
schema_changes
test_counts_before
test_counts_after
```

No destructive migration.

---

# 3. REPOSITORY STRUCTURE

Use something close to:

```text
powproducts/
├── README.md
├── AGENTS.md
├── SOURCES.md
├── BLOCKERS.md
├── DATA_MODEL.md
├── MIGRATION.md
├── ROBOTICS_UNIVERSE.md
├── RIGHTS.md
├── pyproject.toml
│
├── powproducts/
│   ├── __init__.py
│   │
│   ├── shared/
│   │   ├── db.py
│   │   ├── persist.py
│   │   └── rights.py
│   │
│   ├── core/
│   │   ├── ids.py
│   │   ├── enums.py
│   │   ├── models.py
│   │   ├── normalize.py
│   │   └── resolve.py
│   │
│   ├── collectors/
│   │   ├── base.py
│   │   ├── robotshop.py
│   │   ├── ebay_browse.py
│   │   ├── partsdb.py
│   │   ├── mouser.py
│   │   ├── tme.py
│   │   ├── digikey.py
│   │   ├── element14.py
│   │   ├── pci_ids.py
│   │   ├── hwdata.py
│   │   ├── oshwa.py
│   │   ├── robot_descriptions.py
│   │   ├── mujoco_menagerie.py
│   │   ├── robotis.py
│   │   ├── ros_descriptions.py
│   │   ├── blender_open_data.py
│   │   ├── mlperf.py
│   │   ├── bitmain.py
│   │   └── microbt.py
│   │
│   ├── parsers/
│   │   ├── urdf.py
│   │   ├── mjcf.py
│   │   ├── marketplace.py
│   │   └── benchmark.py
│   │
│   ├── semantic/
│   │   └── jev.py
│   │
│   ├── layer1/
│   │   ├── health.py
│   │   ├── health_schema.yaml
│   │   └── manifests/
│   │
│   ├── registry/
│   │   ├── sources.yaml
│   │   ├── ecosystem_sources.yaml
│   │   ├── product_universe.yaml
│   │   ├── taxonomy.yaml
│   │   └── aliases.yaml
│   │
│   ├── export_k1.py
│   ├── daemon.py
│   └── cli.py
│
├── tests/
└── warehouse/
    └── .gitkeep
```

Do not introduce Docker, Neo4j, Postgres, Kafka, Prefect, Grafana or a vector database for Checkpoint 1.

SQLite + raw files + Parquet exports are sufficient.

---

# 4. LAYER-1 BOUNDARY

The source garden may store:

```text
raw bytes
source-native records
canonical product identities
declared specifications
identifiers
relations
market listing identities
market observations
inventory
availability
lead time
lifecycle events
benchmark observations
deterministic diffs
source provenance
probabilistic semantic annotations
```

It must **not** store as canonical Layer-1 truth:

```text
fair value
undervalued
good buy
scarcity score
liquidity score
repair profitability
best workload
mining profitability
AI profitability
predicted failure
investment signal
robotics opportunity
constraint score
Seesaw conclusion
```

Those are later transformations.

A deterministic event such as:

```text
PRICE_CHANGED
STOCK_CHANGED
DISAPPEARED
REAPPEARED
DISCONTINUED
PART_SUPERSEDED
```

is acceptable.

A judgment such as:

```text
SCARCITY_FORMING
BUY_NOW
GOOD_ROBOTICS_OPPORTUNITY
```

is not Layer 1.

---

# 5. CANONICAL PRODUCT MODEL

Stop using `device` as the universal word.

Use `Product`.

A Product can be:

```text
GPU
CPU
ASIC
robot
robot arm
mobile robot
humanoid
actuator
servo
motor
gear reducer
encoder
camera
LiDAR
controller
PLC
SBC
Jetson
PSU
battery
charger
sensor
network interface
3D printer
CNC machine
replacement PCB
connector
IC
MOSFET
bearing
fan
cable
tool
```

Products may contain Products.

This is important.

A motor is not ontologically different from a robot arm merely because it is smaller.

---

# 6. CORE ENTITIES

Implement at minimum:

## Manufacturer

```text
manufacturer_id
canonical_name
aliases[]
country_code
website_domain
external_ids{}
first_seen_at
last_seen_at
```

## ProductFamily

Example:

```text
NVIDIA GeForce RTX 40
Bitmain Antminer S21
ROBOTIS DYNAMIXEL X
Unitree G1
Universal Robots e-Series
```

Fields:

```text
family_id
manufacturer_id
name
product_class
parent_family_id
first_seen_at
last_seen_at
```

## ProductModel

Example:

```text
RTX 4090
Antminer S21 XP
DYNAMIXEL XM430-W350
Universal Robots UR10e
Unitree G1
Jetson AGX Orin
```

Fields:

```text
product_id
manufacturer_id
family_id

canonical_name
model_number
product_class

release_date
discontinued_date

declared_status
country_of_origin

external_ids_json

first_seen_at
last_seen_at
```

## ProductVariant

Examples:

```text
RTX 4090 Founders Edition
MSI RTX 4090 Gaming X Trio
H100 PCIe 80GB
H100 SXM5 80GB
Antminer S21 XP 270T
```

Fields:

```text
variant_id
product_id

manufacturer_sku
mpn
gtin
ean
upc

revision
capacity
memory
packaging
region

external_ids_json

first_seen_at
last_seen_at
```

## ProductIdentifier

Do not cram identity into one text column.

```text
identifier_id
entity_id
namespace
value
source_id
valid_from
valid_to
confidence
```

Namespaces might include:

```text
mpn
sku
gtin
ean
upc
pci_vendor_device
usb_vendor_product
robotshop_sku
ebay_epid
manufacturer_model
ros_package
urdf_name
mujoco_model
```

---

# 7. RELATIONSHIP MODEL

Create a generic temporal `product_relation`.

```text
relation_id
src_entity_id
dst_entity_id
relation_type

quantity
unit

valid_from
valid_to

truth_class
confidence

source_record_id
evidence_json
created_at
```

Initial relation vocabulary:

```text
VARIANT_OF
CONTAINS
COMPATIBLE_WITH
INCOMPATIBLE_WITH
REQUIRES
OPTIONALLY_USES
REPLACES
REPLACED_BY
SUPERSEDES
ALTERNATIVE_TO
MOUNTS_TO
CONNECTS_TO
CONTROLLED_BY
SENSES_WITH
POWERED_BY
USES_PROTOCOL
HAS_INTERFACE
HAS_FIRMWARE
SAME_AS
POSSIBLE_SAME_AS
```

Do not invent compatibility because two products have vaguely similar descriptions.

Compatibility is evidence-bearing.

---

# 8. SPECIFICATIONS MUST BE OBSERVATIONS

Never assume a specification is eternal.

Implement:

```text
product_spec_observation

spec_observation_id
entity_id

spec_key
value
numeric_value
unit

source_id
source_record_id

truth_class
observed_at
effective_at

parser_version
```

Examples:

```text
tdp_watts = 450 W
vram = 24 GB
joint_count = 6
payload = 12.5 kg
reach = 1300 mm
rated_voltage = 24 V
stall_torque = ...
gear_ratio = ...
encoder_resolution = ...
hashrate = ...
power_draw = ...
memory_bandwidth = ...
interface = EtherCAT
```

Manufacturer specification:

```text
truth_class = declared
```

Independent benchmark:

```text
truth_class = observed
```

Do not silently overwrite one with the other.

---

# 9. ROBOT DESCRIPTIONS

This is a major new branch.

Parse URDF/Xacro/MJCF where licensing permits.

Normalize:

```text
robot_description_id
product_id
format
source_id
source_version

links[]
joints[]

joint.name
joint.type
joint.parent
joint.child
joint.axis

joint.limit.lower
joint.limit.upper
joint.limit.velocity
joint.limit.effort

inertial.mass
inertial.origin
geometry

transmissions
interfaces
mimic_relations

raw_ref
```

Do not need to recreate a robotics simulator.

The objective is:

```text
ROBOT MODEL
    ↓
JOINTS
    ↓
ACTUATION REQUIREMENTS
    ↓
INTERFACES
    ↓
REPLACEABLE COMPONENTS
```

This lets later POW systems connect:

```text
robot
→ actuator
→ controller
→ encoder
→ reducer
→ bearing
→ component MPN
→ distributor
→ stock
→ price
→ failure data
```

That is the robotics-ready graph we want.

Useful open seeds include `robot_descriptions.py`, which currently aggregates more than 190 robot descriptions across multiple robot classes, and MuJoCo Menagerie. ROS/ROS-Industrial description packages also expose useful joint, limit and inertial structures. Preserve every upstream licence per model/package rather than assuming one blanket licence.

---

# 10. MARKET DATA MODEL

Do not use one ambiguous `price`.

Every price observation needs semantics.

Implement something like:

```text
market_listing

listing_id
source_id
source_native_id

resolved_product_id
resolved_variant_id

title
description

market
market_country
seller_id
seller_location

listing_type
condition
scope

first_seen_at
last_seen_at

source_url_ref
```

`scope`:

```text
complete_unit
part
accessory
bundle
unknown
```

`condition`:

```text
new
open_box
refurbished
used_like_new
used_good
used_fair
used_poor
broken
for_parts
unknown
```

Then:

```text
market_observation

observation_id
listing_id
observed_at

price_type
price
currency

shipping_price

stock_quantity
availability

seller_rating
seller_sales

raw_ref
```

`price_type` MUST distinguish:

```text
retail_ask
marketplace_ask
auction_current_bid
auction_hammer_confirmed
sold_price_confirmed
dealer_bid
dealer_exchange
manufacturer_list
```

This is critical.

Never put:

```text
£475
```

into the database without saying what kind of £475 it is.

---

# 11. ABSOLUTE RULE: DISAPPEARANCE IS NOT A SALE

The existing eBay logic must retain this rule.

```text
listing seen at t0
listing seen at t1
listing gone at t2
```

means:

```text
DISAPPEARED
```

It does **not** mean:

```text
SOLD
```

Possible causes:

```text
sold
cancelled
expired
removed
delisted
relisted
account suspended
query stopped matching
```

Only create:

```text
SOLD_CONFIRMED
```

when the source explicitly confirms a sale.

The official eBay Browse API is useful for active/purchasable items, structured product/condition/item information and marketplace search, but should not be treated as a sold-history API.

Correct the current stale `/repair/SOURCES.md` wording if it claims the existing collector has authoritative eBay sold prices.

It does not.

---

# 12. JEV

Jev belongs in the pipeline, but **not between HTTP fetch and raw preservation**.

Correct architecture:

```text
SOURCE
  ↓
RAW BYTES
  ↓
RAW HASH + ACQUISITION RECEIPT
  ↓
DETERMINISTIC PARSER
  ↓
SOURCE RECORD
  ↓
OPTIONAL JEV SEMANTIC PASS
  ↓
PROBABILISTIC ANNOTATION
  ↓
RESOLUTION CANDIDATE
```

For marketplace titles Jev may answer bounded questions such as:

```text
Which canonical product is this?

What condition is being described?

Is this:
- complete unit
- replacement part
- accessory
- bundle
- unknown?

Does the text explicitly state a fault?

Which failure symptom is mentioned?
```

Store:

```text
jev_decision_id

source_record_id
input_hash

question_schema_id
question_schema_version

model_id
model_version

options_json
probabilities_json
selected_option

created_at
```

Never reduce:

```text
{
  RTX_4090: 0.72,
  RTX_4080: 0.03,
  UNKNOWN: 0.25
}
```

to an irreversible hard label.

Keep the full distribution.

Most importantly:

**Jev must never overwrite deterministic identifiers.**

If an MPN, GTIN, OEM model number or exact SKU resolves the product, use that.

Jev is for ambiguity.

For now use an extremely conservative automatic-link threshold and require structural agreement with known brand/model information. Anything else becomes:

```text
POSSIBLE_SAME_AS
```

or enters a resolution queue.

No LLM/Jev dependency may prevent a collector from preserving its raw data.

---

# 13. SOURCE RIGHTS BECOME MACHINE-READABLE

Every source manifest needs:

```text
rights:
  access_type:
  licence:
  terms_url_ref:
  raw_retention:
  normalized_retention:
  derivatives:
  redistribution:
  commercial_use:
  automated_access:
  status:
  reviewed_at:
  notes:
```

`status`:

```text
open
approved
terms_review
permission_required
blocked
```

A collector must not run in production when:

```text
status = blocked
```

Do not solve HTTP 403s with proxy gymnastics.

Do not use residential proxies to bypass access restrictions.

Do not make Apify or similar anti-bot tooling the canonical eBay strategy.

Prefer official APIs or clearly permissible public datasets.

Existing blocked collectors may remain as code/tests but disabled.

---

# 14. SOURCE REGISTRY — KEEP ALL RESEARCH

Create two registries.

## `registry/sources.yaml`

Only sources **owned by powproducts**.

## `registry/ecosystem_sources.yaml`

Everything we have discovered, including sources owned by:

```text
repair
powuk
powpowpow
powstock
future systems
```

Each ecosystem record should contain:

```text
source_id
name
owner_system
category
access
status
why_it_matters
historical_depth
ephemeral
rights_status
notes
```

Also preserve the existing:

```text
ptech_registry/source_registry.json
ptech_registry/source_matrix.csv
ptech_registry/physical_repair_sources.json
ptech_registry/execution_plan.json
```

under a legacy research folder or migrate every record before removing them.

Do not lose accumulated source research just because architecture changed.

---

# 15. PRIORITY SOURCE MAP

## A. ELECTRONIC COMPONENTS — HIGH PRIORITY

### Mouser

Build properly.

Useful fields include:

```text
manufacturer
MPN
description
category
lifecycle
stock
availability
MOQ
order_multiple
lead_time
suggested_replacement
price_breaks
datasheet
```

Mouser currently documents API access with up to 30 calls/minute and 1,000 calls/day and exposes stock, lead time, lifecycle, suggested replacement and pricing data.

Action:

```text
P0
START CLOCK
daily promoted basket
weekly long tail
```

### TME

NEW SOURCE.

TME's current API exposes product catalogue/search, detailed data, stock, prices, delivery, parameters and related/similar products.

This is particularly attractive for UK/European robotics/electronics.

Action:

```text
P0/P1
BUILD
obtain normal developer credentials
daily promoted basket
```

### Farnell / element14

NEW SOURCE.

The element14 Product Search API supports part/keyword/MPN search plus pricing and availability via API-key access.

Action:

```text
P1
BUILD
UK-market component reference
```

### DigiKey

Build through official Product Information APIs.

Important fields:

```text
MPN
manufacturer
stock
pricing
substitutions
product status
technical parameters
```

The current Product Information API distinguishes endpoints intended for real-time product detail/availability from broader search results whose data can be less fresh. Preserve the source timestamp and endpoint semantics.

Action:

```text
P1
daily promoted basket
```

### Nexar / Octopart

Keep as enrichment rather than relying on it as our primary free clock.

The current free/evaluation access is intentionally limited, but it is useful for component identity and cross-distributor enrichment.

Action:

```text
P2 enrichment
do not build architecture that requires paid Nexar
```

### PartsDB

Migrate existing collector.

Current repository assumes limited free access.

Before enabling:

```text
VERIFY current quota
VERIFY retention rights
VERIFY commercial terms
```

Do not discard the existing collector.

---

# 16. HARDWARE IDENTITY SOURCES

## PCI ID Repository

Build this immediately.

The PCI ID repository publishes vendor, device, subsystem and class identifiers and makes the canonical `pci.ids` database available for automated retrieval.

Excellent for:

```text
GPU identity
NIC identity
accelerator identity
controller identity
hardware aliases
```

Cadence:

```text
daily or weekly
```

History is backfillable.

## hwdata

Preserve the already identified open-source hardware-ID corpus.

Use as static/reference identity substrate.

## OSHWA certification directory/API

NEW.

The Open Source Hardware Association certification directory has machine-readable search/access and categories covering electronics, robotics and 3D printing.

Useful for:

```text
open robot hardware
open controllers
open actuators
open sensor boards
3D-printable hardware
canonical project identity
source/design links
```

This is especially valuable for future repairability because open hardware exposes designs that proprietary products do not.

---

# 17. ROBOTICS SOURCES — MAKE THESE FIRST CLASS

## robot_descriptions.py

P0 static/backfill source.

Use it to establish broad canonical robot identity and robot-description references.

It currently covers 190+ descriptions spanning arms, humanoids, quadrupeds, bipeds and wheeled robots.

Do not copy every upstream asset blindly.

Store:

```text
robot name
manufacturer
description package
format
upstream repo
upstream version
licence
description hash
```

Then parse only the selected initial universe.

## MuJoCo Menagerie

P0 reference source.

It contains curated robot models including well-known arms, grippers, quadrupeds and humanoid platforms.

Use for:

```text
robot identity
kinematic structure
model geometry
joint information
asset relations
```

Again preserve model-level licences.

## ROS Index

Use as discovery/reference substrate.

ROS Index connects packages, repositories and dependencies across ROS ecosystems.

Do not ingest every ROS package.

Create a curated product-description allowlist.

## ROS-Industrial / manufacturer description repositories

Prioritize:

```text
Universal Robots
KUKA
Franka
UFactory
ROBOTIS
Robotiq
Unitree where suitable descriptions exist
```

Universal Robots' description packages contain URDF/xacro configuration including joint and physical parameters; KUKA description packages similarly expose robot joint structures and limits.

## ROBOTIS DYNAMIXEL e-Manual

P0.

This is particularly valuable.

Make every supported actuator model a canonical product.

Capture:

```text
model
family
status
discontinued
recommended replacement

dimensions
weight

rated voltage
operating voltage

stall torque
speed
current

gear ratio
resolution

control modes
protocol
communication
connector/interface
feedback capability

compatible accessories
```

ROBOTIS documentation explicitly spans current and discontinued DYNAMIXEL families and individual model pages expose model specifications and, where applicable, replacement relationships.

This gives POW a real actuator lifecycle graph.

---

# 18. ROBOT DATASETS — REFERENCE, NOT MARKET TAPE

These do not belong in the marketplace tape but should be registered for future cross-system usage.

## LeRobot datasets

LeRobot's dataset format is designed for multimodal robot trajectories including sensorimotor data and cameras, with large numbers of datasets distributed through Hugging Face.

Use now only for:

```text
robot embodiment identity
sensor configurations
action/state schemas
task vocabulary
future telemetry schema design
```

Do not mirror terabytes of robot video.

## Open X-Embodiment

Register as an important robotics reference.

Open X-Embodiment unified data from many real robot datasets/embodiments into a common representation and contains more than a million trajectories across many institutions.

Use it to inform:

```text
embodiment taxonomy
capability vocabulary
task ontology
observation/action schema
```

Do not turn `powproducts` into a training-dataset mirror.

Every constituent dataset can have its own licensing conditions.

---

# 19. COMPUTE HARDWARE SOURCES

`powproducts` owns hardware identity and market state.

`powpowpow` owns workload economics.

## Blender Open Data

P0.

Blender Open Data exposes public CPU/GPU benchmark results and downloadable machine-processable data.

Capture:

```text
hardware model
device type
benchmark
score/time
Blender version
operating environment where available
submission date
source identity
```

Use primarily to resolve:

```text
product → observed compute performance
```

## MLPerf / MLCommons

P0 historical benchmark source.

The public MLPerf repositories preserve released AI inference benchmark results across hardware platforms.

Capture:

```text
system
accelerator
CPU
accelerator_count
scenario
model/workload
software stack
result
unit
release
```

Do not calculate AI rental yield here.

That remains downstream.

---

# 20. CPU/GPU PRODUCT UNIVERSE

Initial tracked compute hardware:

```text
GPU

NVIDIA RTX 3090
RTX 4090
RTX 5090

A100 80GB
H100 PCIe
H100 SXM
H200
B200

selected AMD high-end GPU equivalents

CPU

Ryzen 7950X
Ryzen 7950X3D
Ryzen 9950X
Ryzen 9950X3D

Threadripper 7970X
selected Threadripper Pro

selected EPYC

EDGE

Jetson Orin Nano
Jetson Orin NX
Jetson AGX Orin
Raspberry Pi 5
```

Do not start with 5,000 chips.

Start with products that bridge:

```text
AI
robotics
homelab
mining
resale
repair
```

---

# 21. ASIC PRODUCTS

ASICs definitely belong in `powproducts`.

Product state:

```text
manufacturer
model
variant
algorithm
declared hashrate
declared power
declared efficiency
dimensions
weight
cooling
input voltage
firmware/support status
release/discontinued status

manufacturer price
retailer price
used price
broken price
parts price
```

Productive mining economics remain in `powpowpow`.

Initial universe:

```text
Bitmain:
S19 family
S21
S21 Pro
S21 XP
relevant Hydro variants
L7

MicroBT:
M50 family
M60 family
current M70-generation products where applicable
```

## MicroBT official store/support

NEW valuable clock.

MicroBT's official store currently exposes active miner models with model-level pricing and hardware characteristics.

Build:

```text
microbt_official
```

Snapshot:

```text
model
listed price
currency
availability/status
declared hashrate
declared efficiency
product URL identity
observed_at
```

This is a genuine manufacturer-market clock.

## Bitmain official support

Use official support/product documentation for:

```text
model identity
firmware
manual availability
declared specifications
repair/support documentation
lifecycle
```

Do not depend on PDF scraping for the architecture.

Store original source references and document hashes where permitted.

---

# 22. SECOND-HAND MARKET SOURCES

This needs to become a major branch.

## eBay

Replace the current scraping-first design with an official API-first collector.

Preserve the existing collector/tests as fallback research, but disable direct scraping in production unless rights/access are explicitly approved.

Track by marketplace:

```text
EBAY_GB
```

Capture:

```text
listing ID
title
condition
item specifics
price
shipping
seller
seller location
availability
buying option
product identity where available
first seen
last seen
```

eBay Browse supports structured product/listing search and detailed item fields useful for this tape.

Poll curated products rather than scraping the entire site.

## Jawa

Register immediately as `terms_review`.

Jawa is unusually interesting because its public market views explicitly show sold PC-component listings and "sold for" values, including GPUs.

It is primarily useful as:

```text
explicit realized GPU/CPU/PC component price reference
```

But public visibility does not imply unrestricted automated archival rights.

Therefore:

```text
source registered
collector fixture built if useful
automation DISABLED until terms/access review
```

Jawa is US-heavy, so use it as cross-market realized-price evidence, not the primary UK price tape.

## CeX

Existing collector stays registered.

Current VPS receives 403.

Do not bypass.

Status:

```text
blocked_access
```

Useful fields when legitimate access exists:

```text
dealer_sell
dealer_cash_buy
dealer_exchange
grade
stock
```

Dealer bid/ask is valuable.

## Cash Converters

Preserve candidate.

UK second-hand goods.

Status:

```text
terms_review
```

## Back Market

Preserve candidate for professional refurb prices.

Status:

```text
terms_review
```

## Radwell

Preserve.

Very relevant to the future robotics/industrial-maintenance graph:

```text
industrial parts
surplus
refurb
repair service
obsolete automation equipment
```

Status:

```text
terms_review
high strategic value
```

## The Saleroom / BidSpotter

Preserve as industrial liquidation / auction candidates.

Potential future data:

```text
robot arms
CNC machines
industrial electronics
motors
drives
PLCs
test equipment
```

Only collect where access/terms allow.

## B-Stock

Preserve as liquidation/returns candidate.

## Alibaba / AliExpress

Preserve as upstream aftermarket/OEM sourcing candidates.

Do not scrape blindly.

Prefer API/affiliate/partner paths.

## Robots.com / industrial robot resellers

Preserve as used/refurb robot-market candidates.

Potentially extremely important later because industrial robots often trade outside consumer marketplaces.

---

# 23. ROBOTSHOP

Migrate the working collector first.

This is one of the few clocks already running.

Keep:

```text
stable SKU/product identity
JSON-LD extraction
price
currency
availability
brand
category
source URL
```

Improve resolution so RobotShop entries map onto:

```text
Product
Variant
Part
```

rather than merely being anonymous listings.

Search/track:

```text
robot arms
servos
actuators
motor controllers
encoders
LiDAR
depth cameras
IMUs
motor drivers
grippers
wheels
gearboxes
SBCs
power electronics
```

Do not broaden into unrelated hobby products.

---

# 24. 3D PRINTING / FABRICATION DATA

Preserve existing research sources:

```text
Bambu profiles
Prusa profiles
Marlin configurations
Cura profiles
Klipper configurations
```

These are useful because they encode:

```text
printer identity
board identity
hotend/extruder relationships
firmware support
configuration compatibility
```

Use Git history when available.

This is mostly reconstructable static/history data, so it is below ephemeral marketplace/component clocks in operational priority.

---

# 25. OPENWRT / HOME ASSISTANT / ZIGBEE2MQTT

Preserve these previously identified sources.

They are not direct robotics-market alpha.

They are excellent compatibility substrates.

Examples:

```text
physical device → chipset
physical device → firmware support
physical device → controllable capabilities
physical device → protocol
physical device → integration
```

This helps build the generic physical ProductGraph that robots will eventually inherit.

Keep them lower priority than:

```text
robotics
components
GPUs/CPUs
ASICs
market prices
```

---

# 26. SECURITY / SUPPORT LIFECYCLE

Register NVD as optional product-lifecycle evidence.

The NVD exposes machine-readable CVE/CPE APIs and feeds suitable for linking vulnerabilities to product/software identities.

Do not ingest the entire NVD at Checkpoint 1.

Eventually useful for:

```text
product
→ firmware/software dependency
→ vulnerability
→ patch
→ unsupported
```

This becomes valuable for deployed robots.

---

# 27. SAFETY / RECALL SOURCES

These remain primarily owned by `repair`, but `powproducts` should be link-compatible.

Preserve:

```text
UK OPSS
EU Safety Gate
NHTSA
DVSA/MOT
```

EU Safety Gate currently provides searchable dangerous-product data with export capabilities and explicit data-reuse conditions.

Do not duplicate full recall ingestion in two gardens.

Instead:

```text
repair
    exports recall/safety event
        ↓
powproducts product_id
```

---

# 28. UK WEEE / INSTALLED-BASE PROXY

NEW UK-specific reference.

The Environment Agency publishes UK EEE placed-on-market and WEEE-collected statistics by reporting period. Current publications include 2026 quarterly data.

This is not exact-model product data.

It can become:

```text
category
period
EEE placed on market
WEEE collected
```

Useful later for:

```text
installed-base proxy
end-of-life flow
repair/reuse opportunity
```

Register it.

Do not make it a Checkpoint-1 blocker.

---

# 29. WHAT STAYS IN POWPOWPOW

Do not move these into powproducts:

```text
Minerstat profitability
Qubic yields
Monero yields
hashprice
MiningRigRentals
Vast
Clore
Akash
Golem
Salad
RunPod
power-adjusted mining revenue
AI rental revenue
best workload
```

`powproducts` says:

```text
RTX 4090 exists
here are exact variants
here are its declared/observed specs
here are marketplace prices
here is availability
here are compatible components
```

`powpowpow` says:

```text
Given that RTX 4090,
what productive workload is worth the most?
```

The join occurs through canonical product IDs.

---

# 30. SOURCES TO PRESERVE BUT NOT BUILD NOW

Keep these in ecosystem registry so previous research is not lost:

```text
Keepa
Luxor
Hashrate Index
Minerstat
MiningRigRentals
Vast
Clore
Akash
Golem
Salad
RunPod

Cash Converters
Back Market
Radwell
The Saleroom
BidSpotter
B-Stock
Alibaba
AliExpress
Robots.com

Nexar
iFixit
Open Repair
OPSS
NHTSA
DVSA

OpenWrt
Zigbee2MQTT
Home Assistant

CEC equipment lists
EPREL

Open X-Embodiment
LeRobot
RobotData
```

Every one gets:

```text
owner_system
status
reason
access
rights
priority
```

Nothing is forgotten merely because it isn't currently enabled.

---

# 31. PRODUCT UNIVERSE — ROBOTICS FIRST

Create `registry/product_universe.yaml`.

Do not ingest the whole planet.

Start with a deliberately selected ~50–100 models.

## Robots / arms

Seed with products where open machine descriptions or strong technical docs exist:

```text
Universal Robots UR5e
Universal Robots UR10e

Franka Panda
Franka FR3 where data permits

KUKA iiwa family

UFactory xArm 6
UFactory xArm 7
UFactory Lite6

Unitree G1
Unitree H1
Unitree Go2
Unitree Z1

Hello Robot Stretch

selected ROBOTIS platforms

Robotiq 2F-85 / common grippers

selected LeRobot low-cost arm ecosystems
```

Do not worry if several are not UK-manufactured.

The UK-first aspect initially comes from:

```text
UK availability
UK second-hand prices
UK distributor stock
UK service/repair supply
UK deployments later
```

not from restricting products to British OEMs.

## Actuation

Prioritize:

```text
DYNAMIXEL current families
DYNAMIXEL discontinued families with replacements

BLDC motors where exact models become available
servo drives
motor controllers
harmonic/cycloidal reducers
encoders
```

The critical thing is exact MPNs.

## Perception

Start with:

```text
Intel RealSense D455
selected OAK-D / Luxonis devices
selected common LiDAR
selected IMUs
industrial/depth cameras
```

Again: exact model identity over breadth.

## Robot compute

```text
Jetson Orin Nano
Jetson Orin NX
Jetson AGX Orin
Raspberry Pi 5

RTX 3090
RTX 4090
RTX 5090

A100
H100
H200
B200

selected AMD equivalents
```

## ASICs

Use the specified Bitmain/MicroBT families.

---

# 32. IDENTITY RESOLUTION IS THE HEART OF THE REPO

The repo fails if:

```text
RTX4090
RTX 4090
NVIDIA GeForce RTX 4090
GeForce 4090
MSI 4090 Gaming Trio
4090 24GB
```

remain unrelated strings.

But it also fails if we overmerge variants.

Implement hierarchy:

```text
manufacturer
    ↓
family
    ↓
model
    ↓
variant
    ↓
individual market listing
```

Example:

```text
NVIDIA
↓
GeForce RTX 40
↓
RTX 4090
↓
MSI Gaming X Trio 24G
↓
eBay listing #123...
```

Resolution evidence priority:

```text
1. Exact MPN / GTIN / SKU
2. Exact manufacturer model identifier
3. Trusted structured source mapping
4. Exact alias table
5. Deterministic normalized string + manufacturer
6. Jev probabilistic candidate
7. unresolved
```

Never silently perform fuzzy merges.

Every merge needs evidence.

---

# 33. CONDITION CLASSIFICATION

Marketplace condition must be normalized separately from product identity.

Do not embed condition into product IDs.

For example:

```text
product:
RTX 4090

listing:
ebay:123

condition:
broken

symptom:
no display
```

The same product can exist in:

```text
new
used
refurb
broken
parts
```

markets simultaneously.

That separation is what later enables:

```text
broken-to-working spread
parts floor
repair economics
depreciation
```

without corrupting identity.

---

# 34. RAW DATA DOCTRINE

Maintain the current good repair behaviour:

```text
FETCH
↓
STORE RAW
↓
STORE ACQUISITION RECEIPT
↓
PARSE
↓
NORMALIZE
↓
VERSION
↓
OBSERVE
```

Raw storage should remain content-addressed.

Do not mutate raw blobs.

Keep:

```text
sha256
source
request URL/reference
final URL/reference
status
content type
content length
ETag
Last-Modified
retrieved_at
```

Where source licences prohibit raw archival, store only what is permitted and record that decision in the manifest.

---

# 35. SOURCE RECORD VERSIONING

Keep the current content-addressed version design.

Product source identity must remain stable when:

```text
price changes
stock changes
availability changes
description changes
```

Never make:

```text
price
timestamp
condition
```

part of an otherwise stable product/listing ID.

Changed payload:

```text
same native entity
new source_record version
```

Time-series observation:

```text
append observation
```

This is correct.

---

# 36. EPHEMERAL CLOCK PRIORITY

Prioritize data by:

```text
Can this exact state be reconstructed six months later?
```

### Highest priority

```text
marketplace listings
manufacturer current prices
component stock
component lead times
component prices
availability
dealer bid/ask
product disappearance
new/discontinued product status
```

### Lower operational urgency

```text
URDF histories
Git histories
PCI IDs
MLPerf historical releases
Blender benchmark history
Open X datasets
static manuals
```

The latter are valuable but recoverable.

Start irreversible clocks first.

---

# 37. INITIAL COLLECTOR SCHEDULE

Suggested initial schedule:

```text
RobotShop                     6h
eBay GB official Browse       6h
MicroBT official products     6-12h

Mouser promoted basket        24h
TME promoted basket           24h
DigiKey promoted basket       24h
Farnell promoted basket       24h

PCI IDs                       weekly
hwdata                        weekly
ROBOTIS docs/lifecycle        weekly
robot description repos       weekly
MuJoCo Menagerie              weekly
ROS curated descriptions      weekly

Blender Open Data             weekly
MLPerf                        release-driven / weekly check

OSHWA                         weekly

UK WEEE                       release-driven
```

Do not waste API quota repeatedly recording static metadata every hour.

---

# 38. COMPONENT PROMOTED BASKET

Create:

`registry/component_basket.yaml`

Do not start with millions of parts.

Pick parts relevant to:

```text
robots
motor control
power electronics
compute
sensing
networking
repair
```

Families:

```text
motor drivers
MOSFETs
IGBTs
GaN power devices
current sensors
encoders
IMUs
temperature sensors
pressure sensors
camera modules
MCUs
SBCs
EtherCAT components
CAN transceivers
RS485 transceivers
power supplies
DC/DC converters
connectors
fans
bearings where distributor-addressable
industrial Ethernet
memory
storage
```

Then expand only when products or repair events create new dependencies.

This makes collection graph-driven rather than arbitrary.

---

# 39. PRODUCT DISCOVERY LOOP

Once basic collectors exist:

```text
known product
↓
extract MPN/components/interfaces
↓
discover unknown component
↓
add candidate
↓
resolve
↓
if relevant, promote to monitored basket
↓
start its historical clock
```

That is how the garden should grow.

Not:

```text
scrape entire DigiKey catalogue
```

---

# 40. BENCHMARK OBSERVATIONS

Create:

```text
benchmark_observation

benchmark_observation_id
product_id
variant_id

benchmark_family
benchmark_name
workload

score
unit

hardware_count
power_mode

software
software_version

source_id
source_record_id
observed_at
benchmark_date
```

Examples:

```text
Blender render time
MLPerf tokens/s
MLPerf latency
other reputable hardware benchmark
```

No attempt yet to combine them into one "performance score."

---

# 41. LIFECYCLE EVENTS

Create deterministic:

```text
lifecycle_event

event_id
entity_id
event_type
event_time
observed_at
source
evidence
```

Types:

```text
ANNOUNCED
RELEASED
NEW_VARIANT
FIRMWARE_RELEASED
DISCONTINUED
SUPPORT_ENDED
SUCCESSOR_DECLARED
PART_SUPERSEDED
RESTOCKED
STOCK_OUT
```

Manufacturer evidence outranks marketplace disappearance for lifecycle status.

---

# 42. MARKET EVENTS

Derive only mechanical transitions:

```text
LISTING_APPEARED
PRICE_CHANGED
AVAILABILITY_CHANGED
DISAPPEARED
REAPPEARED
SOLD_CONFIRMED
STOCK_CHANGED
```

Store:

```text
state_before_ref
state_after_ref
event_time
observation_ids
method_version
```

No economic interpretation.

---

# 43. REPAIR INTEGRATION

Ultimately:

```text
powproducts:
product:robotis:xm430-w350

repair:
failure_event:...
    ↓ AFFECTS
product:robotis:xm430-w350
```

`repair` should eventually stop creating duplicate product identities.

But do not rewrite the existing 305k Open Repair records now.

Instead build a cross-system mapping layer later:

```text
repair legacy entity
POSSIBLE_SAME_AS
powproducts canonical entity
```

Then improve the mapping incrementally.

No destructive rewriting of evidence.

---

# 44. POWPOWPOW INTEGRATION

Likewise:

```text
powproducts:
product:nvidia:rtx4090

powpowpow:
workload_yield observation
    ↓ ABOUT
product:nvidia:rtx4090
```

Do not duplicate specifications manually between systems forever.

`powproducts` becomes the canonical physical identity provider.

---

# 45. K1 EXPORT

Create a clean `export_k1.py`.

Export:

```text
NODE
manufacturer
product
variant
part

EDGE
VARIANT_OF
CONTAINS
COMPATIBLE_WITH
REPLACES
REQUIRES
USES_PROTOCOL
etc.

OBSERVATION
price
stock
availability
lead_time
specification
benchmark

EVENT
price changes
stock changes
lifecycle changes

EVIDENCE
source references / provenance
```

Do not export a marketplace listing as if it is the product itself.

Current `/repair/export_k1.py` conflates source/listing records with canonical nodes in several places.

Fix this in the new repo.

Canonical node:

```text
product:nvidia:rtx4090
```

Observation:

```text
ebay listing 123 asks £1,550 for this product
```

Those are different things.

---

# 46. POWOPS

Only after a collector successfully runs should it be added to `powops`.

Health contract should expose:

```text
source_id
last_attempt
last_success
records_seen
records_new
records_changed
records_invalid
bytes_fetched
source_timestamp
staleness
parser_version
status
status_reason
```

Examples:

```text
powproducts robotshop        ok
powproducts ebay_gb          no_key
powproducts mouser           no_key
powproducts tme              ok
powproducts pci_ids          ok
powproducts robotis          ok
```

A missing credential is not the same state as a broken parser.

Use statuses like:

```text
ok
stale
degraded
no_key
terms_blocked
access_blocked
error
```

---

# 47. TESTS — NON-NEGOTIABLE

Port all relevant existing Repair Garden persistence/collector tests.

Add at least the following.

## Persistence tests

```text
raw content hashes deterministically
raw blobs immutable
repeated raw payload is deduplicated
acquisition receipt still appends
changed source payload versions correctly
unchanged payload doesn't invent version
market observation appends even if price unchanged
```

## Identity tests

```text
same MPN resolves same variant
price changes do not change product ID
condition changes do not change product ID
marketplace listing ID remains stable
manufacturer aliases resolve deterministically
RTX 4090 != MSI RTX 4090 variant
H100 PCIe != H100 SXM
```

## Marketplace tests

```text
listing appears
listing price changes
listing disappears
listing reappears

DISAPPEARED != SOLD_CONFIRMED

sold_confirmed only created from explicit source evidence
```

## Component tests

```text
same MPN across Mouser/TME/DigiKey resolves one part
supplier offers remain separate
stock observations append
price tiers preserved
lead-time units normalized
replacement relations preserve evidence
```

## Robotics tests

Fixture URDF must extract:

```text
links
joints
joint types
parent/child
axis
position limits
velocity limit
effort limit
```

Fixture MJCF similarly.

Test:

```text
robot → component relationships
licence metadata retained
source version retained
```

## ROBOTIS tests

Fixture should verify:

```text
model identity
family
voltage
torque/speed where available
protocol
status
replacement model edge where explicitly stated
```

## Benchmark tests

```text
benchmark hardware resolves canonical product
score and unit preserved
software/version preserved
benchmark doesn't overwrite manufacturer spec
```

## Rights tests

```text
blocked source refuses production collection
terms_review source refuses production collection unless override explicitly approved
open source runs
```

## Jev tests

```text
raw collector succeeds when Jev unavailable
Jev never mutates source record
full probability distribution persisted
uncertain match produces POSSIBLE_SAME_AS, not hard merge
```

## Replay test

Given historical raw bytes:

```text
parser vX
→ same normalized output
```

This is essential.

---

# 48. CHECKPOINT-1 DEFINITION

Checkpoint 1 is not:

```text
nice README
50 collector files
graph visualization
AI demo
dashboard
```

Checkpoint 1 means the garden is actually growing.

At minimum demonstrate:

```text
1. canonical product schema works

2. robotics universe exists

3. RobotShop clock running

4. at least one legitimate UK second-hand market clock running
   preferably official eBay GB

5. at least two component distributor clocks running
   from Mouser / TME / DigiKey / Farnell / PartsDB

6. PCI/hardware identity source loaded

7. robot description source loaded

8. DYNAMIXEL product/lifecycle data loaded

9. CPU/GPU benchmark history imported

10. ASIC manufacturer product data loaded

11. every source preserves raw evidence/provenance

12. health report works

13. k1 export works

14. complete test suite passes

15. daemon can restart safely and resume

16. R2 backup includes raw source data according to source rights

17. no Layer-2 economics contaminates Layer 1
```

---

# 49. BUILD ORDER

## Phase A — extraction

```text
Create repo
Port persistence kernel
Rename REPAIR_DB → POWPRODUCTS_DB
Rename RepairGarden User-Agent → PowProducts
Port health
Port manifests
Port tests
```

Get tests green before adding sources.

## Phase B — canonical model

Implement:

```text
Manufacturer
ProductFamily
ProductModel
ProductVariant
ProductIdentifier
ProductRelation
ProductSpecObservation
MarketListing
MarketObservation
LifecycleEvent
BenchmarkObservation
```

Add deterministic IDs.

## Phase C — preserve existing clocks

Migrate:

```text
RobotShop
PartsDB
eBay logic as fixtures/tests
```

Replace eBay production transport with approved official API path.

## Phase D — new free/open robotics substrate

Implement:

```text
PCI IDs
OSHWA
robot_descriptions.py
MuJoCo Menagerie
curated ROS manufacturer descriptions
ROBOTIS DYNAMIXEL
```

## Phase E — component clocks

Implement in order:

```text
TME
Mouser
Farnell/element14
DigiKey
Nexar enrichment
```

Use whichever legitimate credentials are already available.

A source requiring a human API signup must not block other sources.

## Phase F — compute/ASIC

Implement:

```text
Blender Open Data
MLPerf
MicroBT
Bitmain identity/support
```

## Phase G — market expansion

Evaluate:

```text
Jawa
CeX
Cash Converters
Radwell
industrial auctions
robot resellers
```

Do not activate until rights/access are known.

## Phase H — integration

```text
k1 export
powops
R2 backup
parallel-run validation
```

Only after this should duplicate product collectors be retired from `/repair`.

---

# 50. WHAT NOT TO DO

Do not:

```text
build powflow
build powai
build trading logic
build a dashboard
build recommendations
build product fair value
build depreciation models
build repair profitability
build robot failure prediction
build product embeddings
build graph RAG
install Neo4j
collect every product on earth
mirror giant robotics video datasets
scrape sources merely because technically possible
treat disappeared listings as sold
use price in entity IDs
hard-merge fuzzy product identities
let Jev become source-of-truth
rewrite the working Repair persistence layer unnecessarily
```

The goal is much simpler:

> **Get the physical-product clocks running correctly.**

---

# 51. REQUIRED DOCUMENTATION WHEN FINISHED

`README.md`

Must answer:

```text
What is powproducts?
What does it own?
What does repair own?
What does powpowpow own?
How do I run a collector?
How do I check health?
How do I inspect the DB?
How do I run tests?
```

`SOURCES.md`

For every source:

```text
source
what it contributes
access route
cadence
history available?
ephemeral?
status
rights
collector path
sample count
last successful test
```

`DATA_MODEL.md`

Show hierarchy:

```text
manufacturer
→ family
→ model
→ variant

product
→ component

product
→ marketplace listing

product
→ observation
```

`ROBOTICS_UNIVERSE.md`

List exact tracked models and why they were selected.

`RIGHTS.md`

Record:

```text
licence
terms review
raw retention permission
commercial use
redistribution
automation permission
```

`BLOCKERS.md`

No vague blockers.

Use:

```text
SOURCE
EXACT FAILURE
HTTP STATUS / ERROR
WHAT WAS TRIED
LEGAL ALTERNATIVE
WHETHER HUMAN ACTION IS REQUIRED
```

`MIGRATION.md`

Document exactly what moved from Repair.

---

# 52. REPORT BACK AFTER EACH PHASE

Do not report:

```text
"implemented source collector"
```

Report evidence.

Example:

```text
TME

collector: powproducts/collectors/tme.py
HTTP/API: success
raw blobs: 14
source records: 382
canonical products matched: 241
unresolved products: 17
stock observations: 382
price observations: 1,204
invalid records: 0
first timestamp:
last timestamp:
tests:
health status:
```

For every collector give:

```text
fetched
stored
parsed
normalized
resolved
observed
invalid
blocked
```

---

# 53. FINAL ARCHITECTURE TARGET

When Checkpoint 1 is complete:

```text
                         POWPRODUCTS

Manufacturer
     │
     ▼
Product Family
     │
     ▼
Product Model
     │
     ├──────── Variant
     │
     ├──────── Component
     │            │
     │            ├── substitute
     │            ├── replacement
     │            └── supplier offers
     │
     ├──────── Interfaces / Protocols
     │
     ├──────── Robot description
     │
     ├──────── Specifications
     │
     ├──────── Benchmarks
     │
     ├──────── Lifecycle
     │
     └──────── Market Listings
                      │
                      ▼
             continuous observations
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
           price    stock   availability
             │        │        │
             └────────┴────────┘
                      │
                      ▼
                 HISTORY
```

Then other gardens attach:

```text
repair
    failure / intervention / outcome
          ↓
       PRODUCT

powpowpow
    productive workload economics
          ↓
       PRODUCT

powuk
    place / skills / infrastructure
          ↓
       PRODUCT

powstock
    manufacturer / capital / security
          ↓
       PRODUCT
```

And **only once those Layer-1 tapes are accumulating** do we return to:

```text
powflow
powai
Seesaw
robotics constraint graphs
models
prediction
trading
```

That is the correct order.

The immediate objective for this agent is therefore:

> **Extract the existing product-market substrate from `/repair`, make `/powproducts` the canonical physical-product identity system, start the ephemeral component/secondary-market/manufacturer clocks, and seed it aggressively with robotics, compute and ASIC hardware—without building Layer 2.**

The biggest new sources worth prioritizing beyond what `/repair` already knew are **TME, OSHWA, `robot_descriptions.py`, MuJoCo Menagerie, curated ROS manufacturer descriptions, ROBOTIS/DYNAMIXEL, MicroBT's manufacturer market, Blender Open Data and MLPerf**. Together they give you component supply + exact robot structure + actuator lifecycle + compute/ASIC identity without needing an expensive commercial dataset.
