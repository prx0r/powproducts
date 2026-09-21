"""MicroBT Whatsminer Collector — ASIC manufacturer pricing clock.

Scrapes the official MicroBT shop for miner models and prices.
This is a genuine manufacturer-market clock.

Source: https://shop.whatsminer.com
Licence: Terms review needed for automated access
"""

import json
import re
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import insert_source_record, store_market_observation


class MicrobtCollector(BaseCollector):
    SOURCE_ID = 'microbt_official'
    DATASET = 'miner_products'
    PARSER_ID = 'microbt_shop_v1'

    def fetch(self):
        """Fetch MicroBT shop products page."""
        acq = self._fetch_url('https://shop.whatsminer.com/products', timeout=15,
                               headers={'Accept': 'text/html'})
        if acq and acq.status == 200:
            return acq.content
        return None

    def parse(self, raw_content, raw_hash, result):
        """Parse MicroBT shop HTML for product listings."""
        html = raw_content.decode('utf-8', errors='replace')

        # Extract JSON-LD product data if available
        json_ld_blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            html, re.DOTALL
        )

        for block in json_ld_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    self._parse_product(data, raw_hash, result)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            self._parse_product(item, raw_hash, result)
            except json.JSONDecodeError:
                pass

        # Fallback: parse product cards from HTML
        if result.records_new == 0 and result.records_unchanged == 0:
            self._parse_html_cards(html, raw_hash, result)

    def _parse_product(self, data, raw_hash, result):
        """Parse a single JSON-LD product."""
        name = data.get('name', '')
        if not name:
            result.records_invalid += 1
            return

        offers = data.get('offers', {})
        price = offers.get('price')
        native_id = data.get('sku', '') or name.lower().replace(' ', '-')

        normalized = {
            'source_native_id': native_id,
            'name': name,
            'description': data.get('description', ''),
            'sku': data.get('sku', ''),
            'price': float(price) if price else None,
            'currency': offers.get('priceCurrency', 'USD'),
            'availability': offers.get('availability', ''),
            'url': data.get('url', ''),
            'brand': data.get('brand', {}).get('name', 'MicroBT'),
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

        # Store market observation if price available
        if price is not None:
            store_market_observation(
                source_record_id=ir.record_id,
                observed_at=datetime.now(timezone.utc).isoformat(),
                price=float(price),
                currency=normalized['currency'],
                availability=normalized['availability'],
                market='microbt_official',
            )

    def _parse_html_cards(self, html, raw_hash, result):
        """Fallback: extract product info from HTML structure."""
        # Look for product card patterns
        cards = re.findall(
            r'<div[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</div>',
            html, re.DOTALL
        )
        for card in cards:
            name_match = re.search(r'<h[23][^>]*>(.*?)</h[23]>', card, re.DOTALL)
            price_match = re.search(r'\$[\d,]+\.?\d*', card)
            if name_match:
                name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
                native_id = name.lower().replace(' ', '-')
                price = float(price_match.group().replace('$', '').replace(',', '')) if price_match else None

                normalized = {
                    'source_native_id': native_id,
                    'name': name,
                    'price': price,
                    'currency': 'USD',
                }
                ir = insert_source_record(
                    self.SOURCE_ID, self.DATASET, native_id,
                    normalized, raw_hash, self.PARSER_ID, self.PARSER_VERSION
                )
                if ir.inserted:
                    result.records_new += 1
                else:
                    result.records_unchanged += 1

                if price is not None:
                    store_market_observation(
                        source_record_id=ir.record_id,
                        observed_at=datetime.now(timezone.utc).isoformat(),
                        price=price,
                        currency='USD',
                        market='microbt_official',
                    )


if __name__ == '__main__':
    MicrobtCollector().run()
