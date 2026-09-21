"""Normalization helpers for PowProducts."""

import re
from typing import Optional


def normalize_price(value, currency: str = 'GBP') -> Optional[float]:
    """Normalize a price value to float. Returns None if not parseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    # Remove currency symbols
    s = re.sub(r'[£$€¥]', '', s)
    # Remove commas
    s = s.replace(',', '')
    # Remove spaces
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None


def normalize_condition(raw: str) -> str:
    """Normalize marketplace condition string to our enum values."""
    if not raw:
        return 'unknown'
    s = raw.strip().lower()
    mapping = {
        'new': 'new',
        'brand new': 'new',
        'sealed': 'new',
        'open box': 'open_box',
        'opened': 'open_box',
        'unboxed': 'open_box',
        'refurbished': 'refurbished',
        'certified refurbished': 'refurbished',
        'reconditioned': 'refurbished',
        'used - like new': 'used_like_new',
        'like new': 'used_like_new',
        'excellent': 'used_like_new',
        'used - good': 'used_good',
        'good': 'used_good',
        'used - fair': 'used_fair',
        'fair': 'used_fair',
        'used - poor': 'used_poor',
        'poor': 'used_poor',
        'broken': 'broken',
        'not working': 'broken',
        'faulty': 'broken',
        'for parts': 'for_parts',
        'parts only': 'for_parts',
        'spares': 'for_parts',
    }
    return mapping.get(s, 'unknown')


def normalize_scope(raw: str) -> str:
    """Normalize listing scope."""
    if not raw:
        return 'unknown'
    s = raw.strip().lower()
    if any(w in s for w in ['complete', 'full', 'unit', 'whole']):
        return 'complete_unit'
    if any(w in s for w in ['part', 'component', 'spare', 'replacement']):
        return 'part'
    if any(w in s for w in ['accessory', 'accessories', 'cable', 'charger']):
        return 'accessory'
    if any(w in s for w in ['bundle', 'lot', 'pack', 'set']):
        return 'bundle'
    return 'unknown'


def normalize_stock(raw) -> str:
    """Normalize stock/availability to standard values."""
    if raw is None:
        return 'unknown'
    s = str(raw).strip().lower()
    if any(w in s for w in ['in stock', 'available', 'yes', 'instock']):
        return 'in_stock'
    if any(w in s for w in ['out of stock', 'unavailable', 'no', 'oos', 'sold out']):
        return 'out_of_stock'
    if any(w in s for w in ['limited', 'low stock', 'few']):
        return 'limited'
    if any(w in s for w in ['preorder', 'pre-order', 'backorder']):
        return 'preorder'
    return s or 'unknown'
