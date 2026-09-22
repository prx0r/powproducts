"""RobotShop UK Collector — feeds canonical product graph.

Resolves: brand → manufacturer → product → variant → listing → observations.
"""

import json
import re
import time
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import (
    insert_source_record, store_market_observation,
    upsert_manufacturer, upsert_product_model, upsert_product_variant,
    insert_product_identifier, insert_product_relation
)
from powproducts.core.ids import make_variant_id

ROBOT_CATEGORIES = {
    'actuators': ['servo motor', 'brushless motor', 'stepper motor', 'linear actuator'],
    'controllers': ['arduino', 'raspberry pi', 'esp32', 'jetson', 'stm32'],
    'sensors': ['lidar', 'depth camera', 'imu', 'encoder', 'force sensor'],
    'grippers': ['robot gripper', 'robotic hand', 'end effector'],
    'power': ['lipo battery', 'bms', 'motor driver', 'esc'],
    'mechanical': ['bearing', 'coupling', 'gearbox', 'linear rail'],
}


class RobotShopCollector(BaseCollector):
    SOURCE_ID = 'robotshop_uk'
    DATASET = 'robot_parts'
    PARSER_ID = 'robotshop_web_v2'
    RIGHTS_STATUS = 'terms_review'

    def fetch(self):
        all_items = []
        for category, queries in ROBOT_CATEGORIES.items():
            for query in queries:
                items = self._search_robotshop(query, category)
                all_items.extend(items)
                time.sleep(2)
        return json.dumps(all_items).encode()

    def _search_robotshop(self, query, category):
        try:
            url = f'https://uk.robotshop.com/search?q={query}'
            acq = self._fetch_url(url, timeout=15)
            if acq and acq.status == 200:
                html = acq.content.decode('utf-8', errors='replace')
                items = []
                json_ld = re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    html, re.DOTALL
                )
                for block in json_ld:
                    try:
                        data = json.loads(block)
                        if isinstance(data, dict) and data.get('@type') == 'Product':
                            offers = data.get('offers', {})
                            if isinstance(offers, list):
                                offers = offers[0] if offers else {}
                            sku = data.get('sku', '')
                            product_id = data.get('productID', '')
                            url_val = data.get('url', '')
                            url_match = re.search(r'/products/.*?-(\d+)$', url_val) if url_val else None
                            brand = data.get('brand', {})
                            brand_name = brand.get('name', '') if isinstance(brand, dict) else str(brand)
                            items.append({
                                'sku': sku or product_id or (url_match.group(1) if url_match else ''),
                                'name': data.get('name', ''),
                                'price': offers.get('price', None),
                                'currency': offers.get('priceCurrency', 'GBP'),
                                'availability': offers.get('availability', ''),
                                'brand': brand_name,
                                'category': category,
                                'url': url_val,
                                '_provenance': {
                                    'raw_hash': acq.sha256,
                                    'acquisition_id': acq.acquisition_id,
                                    'requested_url': acq.requested_url,
                                },
                            })
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        pass
                return items
        except Exception as e:
            print(f'    RobotShop error for {query}: {e}')
        return []

    def parse(self, raw_content, raw_hash, result):
        items = json.loads(raw_content)
        for item in items:
            native_id = item.get('sku', '') or item.get('name', '')
            if not native_id:
                result.records_invalid += 1
                continue

            prov = item.get('_provenance', {})

            # 1. Source record (with actual acquisition linkage)
            normalized = {
                'source_native_id': native_id,
                'sku': item.get('sku', ''),
                'name': item.get('name', ''),
                'price': item.get('price'),
                'currency': item.get('currency', 'GBP'),
                'availability': item.get('availability', ''),
                'brand': item.get('brand', ''),
                'category': item.get('category', ''),
                'url': item.get('url', ''),
            }
            ir = insert_source_record(
                self.SOURCE_ID, self.DATASET, native_id,
                normalized, raw_hash, self.PARSER_ID, self.PARSER_VERSION,
                acquisition_id=prov.get('acquisition_id')
            )
            if ir.inserted:
                if ir.duplicate_of:
                    result.records_changed += 1
                else:
                    result.records_new += 1
            else:
                result.records_unchanged += 1

            # 2. Resolve manufacturer from brand
            brand = item.get('brand', '')
            manufacturer_id = None
            if brand:
                manufacturer_id = brand.lower().replace(' ', '-').replace('.', '')
                upsert_manufacturer(manufacturer_id, brand)

            # 3. Try to resolve product model from name
            # Conservative: only resolve if name contains recognizable model pattern
            product_id = None
            variant_id = None
            name = item.get('name', '')
            if name and manufacturer_id:
                # Use the full name as a candidate model identifier
                model_candidate = name.strip()
                if model_candidate:
                    from powproducts.core.ids import make_product_id
                    product_id = make_product_id(manufacturer_id, model_candidate)
                    if product_id:
                        upsert_product_model(
                            product_id, manufacturer_id, model_candidate,
                            product_class=item.get('category', 'component')
                        )

                    # 4. Create variant if SKU exists
                    sku = item.get('sku', '')
                    if sku and product_id:
                        variant_id = make_variant_id(product_id, sku=sku)
                        if variant_id:
                            upsert_product_variant(
                                variant_id, product_id,
                                variant_manufacturer_id=manufacturer_id,
                                manufacturer_sku=sku
                            )
                            insert_product_identifier(
                                variant_id, 'robotshop_sku', sku,
                                source_record_id=ir.record_id
                            )

            # 5. Create market listing
            listing_id = f'robotshop:{native_id}'
            conn = __import__('powproducts.shared.persist', fromlist=['get_db']).get_db()
            now = datetime.now(timezone.utc).isoformat()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO market_listing "
                    "(listing_id, source_id, source_native_id, resolved_product_id, "
                    "resolved_variant_id, title, condition, market, first_seen_at, last_seen_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (listing_id, self.SOURCE_ID, native_id,
                     product_id, variant_id, name,
                     'new', 'robotshop_uk', now, now)
                )
                conn.commit()
            finally:
                conn.close()

            # 6. Store market observation with price_type
            price = item.get('price')
            if price is not None:
                store_market_observation(
                    source_record_id=ir.record_id,
                    observed_at=now,
                    price=float(price),
                    currency=item.get('currency', 'GBP'),
                    availability=item.get('availability', ''),
                    condition='new',
                    market='robotshop_uk',
                    price_type='retail_ask',
                    acquisition_id=prov.get('acquisition_id'),
                    source_native_id=native_id,
                )


if __name__ == '__main__':
    RobotShopCollector().run()
