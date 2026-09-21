"""RobotShop UK Collector — robot parts pricing.

UK/EU source for robot components: actuators, servos, grippers, controllers.
"""

import json
import re
import time
import requests
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import insert_source_record, store_market_observation

# Robot parts to track
ROBOT_CATEGORIES = {
    'actuators': ['servo motor', 'brushless motor', 'stepper motor', 'linear actuator'],
    'controllers': ['arduino', 'raspberry pi', 'esp32', 'jetson', 'stm32'],
    'sensors': ['lidar', 'depth camera', 'imu', 'encoder', 'force sensor'],
    'grippers': ['robot gripper', 'robotic hand', 'end effector'],
    'power': ['lipo battery', 'bms', 'motor driver', 'esc'],
    'mechanical': ['bearing', 'coupling', 'gearbox', 'linear rail'],
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


class RobotShopCollector(BaseCollector):
    SOURCE_ID = 'robotshop_uk'
    DATASET = 'robot_parts'
    PARSER_ID = 'robotshop_web_v1'

    def fetch(self):
        """Scrape RobotShop UK for robot parts."""
        all_items = []
        for category, queries in ROBOT_CATEGORIES.items():
            for query in queries:
                items = self._search_robotshop(query, category)
                all_items.extend(items)
                time.sleep(2)
        return json.dumps(all_items).encode()

    def _search_robotshop(self, query, category):
        """Search RobotShop UK."""
        try:
            url = f'https://uk.robotshop.com/search?q={query}'
            acq = self._fetch_url(url, timeout=15)
            if acq and acq.status == 200:
                html = acq.content.decode('utf-8', errors='replace')
                items = []
                json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
                for block in json_ld:
                    try:
                        data = json.loads(block)
                        if isinstance(data, dict) and data.get('@type') == 'Product':
                            offers = data.get('offers', {})
                            sku = data.get('sku', '')
                            product_id = data.get('productID', '')
                            url_val = data.get('url', '')
                            url_match = re.search(r'/products/.*?-(\d+)$', url_val) if url_val else None
                            items.append({
                                'sku': sku or product_id or (url_match.group(1) if url_match else ''),
                                'name': data.get('name', ''),
                                'price': offers.get('price', None),
                                'currency': offers.get('priceCurrency', 'GBP'),
                                'availability': offers.get('availability', ''),
                                'brand': data.get('brand', {}).get('name', ''),
                                'category': category,
                                'url': url_val,
                            })
                    except:
                        pass
                return items
        except Exception as e:
            print(f'    RobotShop error for {query}: {e}')
        return []

    def parse(self, raw_content, raw_hash, result):
        """Parse RobotShop items. Mutates result — does not return a new one."""
        items = json.loads(raw_content)
        for item in items:
            native_id = item.get('sku', '') or item.get('name', '')
            if not native_id:
                result.records_invalid += 1
                continue

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
                normalized, raw_hash, self.PARSER_ID, self.PARSER_VERSION
            )
            if ir.inserted:
                if ir.duplicate_of:
                    result.records_changed += 1
                else:
                    result.records_new += 1
            else:
                result.records_unchanged += 1

            # Always store market observation
            price = item.get('price')
            if price is not None:
                store_market_observation(
                    source_record_id=ir.record_id,
                    observed_at=datetime.now(timezone.utc).isoformat(),
                    price=float(price),
                    currency=item.get('currency', 'GBP'),
                    availability=item.get('availability', ''),
                    market='robotshop_uk',
                )


if __name__ == '__main__':
    RobotShopCollector().run()
