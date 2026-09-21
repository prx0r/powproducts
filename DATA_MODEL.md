# DATA MODEL

## Entity Hierarchy

```
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
    ├──────── Specifications (observations)
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

## Tables

### Manufacturer
| Column | Type | Description |
|--------|------|-------------|
| manufacturer_id | TEXT PK | Deterministic hash of canonical name |
| canonical_name | TEXT | Official company name |
| aliases_json | TEXT | JSON array of alternative names |
| country_code | TEXT | ISO 3166-1 alpha-2 |
| website_domain | TEXT | Primary website |
| external_ids_json | TEXT | JSON dict of external IDs |
| first_seen_at | TEXT | ISO timestamp |
| last_seen_at | TEXT | ISO timestamp |

### Product Family
| Column | Type | Description |
|--------|------|-------------|
| family_id | TEXT PK | Deterministic hash |
| manufacturer_id | TEXT FK | → manufacturer |
| name | TEXT | Family name (e.g. "GeForce RTX 40") |
| product_class | TEXT | GPU, CPU, ASIC, etc. |
| parent_family_id | TEXT FK | → product_family (optional) |

### Product Model
| Column | Type | Description |
|--------|------|-------------|
| product_id | TEXT PK | Deterministic hash |
| manufacturer_id | TEXT FK | → manufacturer |
| family_id | TEXT FK | → product_family |
| canonical_name | TEXT | Display name |
| model_number | TEXT | Manufacturer model number |
| product_class | TEXT | Product classification |
| release_date | TEXT | ISO date |
| discontinued_date | TEXT | ISO date |

### Product Variant
| Column | Type | Description |
|--------|------|-------------|
| variant_id | TEXT PK | Deterministic hash |
| product_id | TEXT FK | → product_model |
| manufacturer_sku | TEXT | Manufacturer SKU |
| mpn | TEXT | Manufacturer Part Number |
| gtin | TEXT | Global Trade Item Number |
| ean | TEXT | European Article Number |
| upc | TEXT | Universal Product Code |
| revision | TEXT | Hardware revision |
| capacity | TEXT | Storage/memory capacity |
| memory | TEXT | Memory specification |
| packaging | TEXT | Box/Bulk/OEM |
| region | TEXT | Geographic region |

### Product Identifier
| Column | Type | Description |
|--------|------|-------------|
| identifier_id | INTEGER PK | Autoincrement |
| entity_id | TEXT | References any entity |
| namespace | TEXT | mpn, sku, gtin, pci_vendor_device, etc. |
| value | TEXT | The identifier value |
| source_id | TEXT | Where this ID came from |
| confidence | REAL | 0.0-1.0 |

### Product Relation
| Column | Type | Description |
|--------|------|-------------|
| relation_id | TEXT PK | Content-addressed hash |
| src_entity_id | TEXT | Source entity |
| dst_entity_id | TEXT | Destination entity |
| relation_type | TEXT | VARIANT_OF, COMPATIBLE_WITH, etc. |
| truth_class | TEXT | declared, observed, inferred |
| confidence | REAL | 0.0-1.0 |
| evidence_json | TEXT | Evidence for this relation |

### Product Spec Observation
| Column | Type | Description |
|--------|------|-------------|
| spec_observation_id | TEXT PK | Content-addressed hash |
| entity_id | TEXT | Product/variant |
| spec_key | TEXT | vram, tdp_watts, stall_torque, etc. |
| value | TEXT | String value |
| numeric_value | REAL | Numeric value |
| unit | TEXT | GB, W, Nm, etc. |
| truth_class | TEXT | declared (manufacturer) or observed (benchmark) |

### Market Listing
| Column | Type | Description |
|--------|------|-------------|
| listing_id | TEXT PK | Content-addressed hash |
| source_id | TEXT | robotshop_uk, ebay_gb, etc. |
| source_native_id | TEXT | Original listing ID |
| resolved_product_id | TEXT FK | → product_model |
| resolved_variant_id | TEXT FK | → product_variant |
| title | TEXT | Listing title |
| condition | TEXT | new, used_good, broken, etc. |
| scope | TEXT | complete_unit, part, accessory, bundle |
| market | TEXT | Marketplace name |

### Market Observation
| Column | Type | Description |
|--------|------|-------------|
| observation_id | INTEGER PK | Autoincrement |
| source_record_id | TEXT FK | → source_record |
| source_native_id | TEXT | Listing ID |
| observation_type | TEXT | price, stock, availability |
| observed_at | TEXT | ISO timestamp |
| price | REAL | Price value |
| currency | TEXT | GBP, USD, EUR |
| stock | TEXT | Stock status |
| availability | TEXT | Availability status |
| condition | TEXT | Item condition |
| market | TEXT | Marketplace |

### Lifecycle Event
| Column | Type | Description |
|--------|------|-------------|
| event_id | TEXT PK | Content-addressed hash |
| entity_id | TEXT | Product/variant |
| event_type | TEXT | ANNOUNCED, RELEASED, DISCONTINUED, etc. |
| event_time | TEXT | When it happened |
| source_id | TEXT | Evidence source |

### Benchmark Observation
| Column | Type | Description |
|--------|------|-------------|
| benchmark_observation_id | TEXT PK | Content-addressed hash |
| product_id | TEXT FK | → product_model |
| benchmark_family | TEXT | blender, mlperf, etc. |
| benchmark_name | TEXT | Specific benchmark |
| score | REAL | Score value |
| unit | TEXT | Score unit |
| software | TEXT | Software used |
| software_version | TEXT | Version |

### Robot Description
| Column | Type | Description |
|--------|------|-------------|
| robot_description_id | TEXT PK | Content-addressed hash |
| product_id | TEXT FK | → product_model |
| format | TEXT | urdf, mjcf, xacro |
| source_id | TEXT | robot_descriptions, mujoco_menagerie |
| links_json | TEXT | Robot links |
| joints_json | TEXT | Robot joints |
| licence | TEXT | Model licence |
