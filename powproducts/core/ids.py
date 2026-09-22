"""Identity resolution for PowProducts.

Handles:
- Deterministic ID generation from canonical fields
- Alias resolution
- Evidence-based merge decisions
"""

import hashlib
from typing import Optional


def make_manufacturer_id(canonical_name: str) -> str:
    """Generate deterministic manufacturer ID from canonical name."""
    normalized = canonical_name.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def make_product_id(manufacturer_id: str, model_number: str) -> Optional[str]:
    """Generate deterministic product model ID. Returns None if insufficient info."""
    if not model_number or not model_number.strip():
        return None
    if not manufacturer_id or not manufacturer_id.strip():
        return None
    raw = f'{manufacturer_id.strip().lower()}:{model_number.strip().lower()}'
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def make_variant_id(product_id: str, sku: str = '', mpn: str = '') -> Optional[str]:
    """Generate deterministic variant ID. Returns None if no identifying evidence."""
    identifier = mpn.strip() if mpn and mpn.strip() else sku.strip() if sku and sku.strip() else ''
    if not identifier:
        return None  # Never create variant without identifying evidence
    raw = f'{product_id}:{identifier.lower()}'
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def make_listing_id(source_id: str, native_id: str) -> str:
    """Generate deterministic listing ID from source + native ID."""
    raw = f'{source_id}:{native_id}'
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_mpn(mpn: str) -> str:
    """Normalize an MPN for comparison. Strips whitespace, uppercases."""
    if not mpn:
        return ''
    return mpn.strip().upper()


def normalize_string(s: str) -> str:
    """Normalize a string for comparison. Lowercases, strips, collapses whitespace."""
    if not s:
        return ''
    import re
    s = s.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s


def resolve_manufacturer(name: str, aliases: dict = None) -> Optional[str]:
    """Resolve a manufacturer name to its canonical ID."""
    if not aliases:
        return None
    normalized = normalize_string(name)
    return aliases.get(normalized)
