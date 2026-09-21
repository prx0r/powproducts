"""Blender Open Data Collector — CPU/GPU benchmark history.

Downloads benchmark results from Blender Open Data.
Useful for: product → observed compute performance.

Source: https://opendata.blender.org
Licence: Open data
"""

import json
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import insert_source_record


class BlenderOpenDataCollector(BaseCollector):
    SOURCE_ID = 'blender_open_data'
    DATASET = 'benchmarks'
    PARSER_ID = 'blender_opendata_v1'

    def fetch(self):
        """Fetch Blender benchmark snapshot."""
        # Try the latest snapshot ZIP first
        acq = self._fetch_url('https://opendata.blender.org/raw-data/', timeout=30)
        if acq and acq.status == 200:
            return acq.content
        return None

    def parse(self, raw_content, raw_hash, result):
        """Parse Blender benchmark data."""
        # The raw-data endpoint returns a page listing files
        # For now, we store the raw index and parse what we can
        try:
            text = raw_content.decode('utf-8', errors='replace')
            # Look for JSON data in the response
            # The actual benchmark data is in CSV/JSON files listed on this page
            # For checkpoint 1, we store the index as a source record
            normalized = {
                'source_native_id': 'blender_opendata_index',
                'content_type': 'html_index',
                'content_length': len(raw_content),
                'note': 'Blender Open Data index page stored. Full benchmark import requires CSV download.',
            }
            ir = insert_source_record(
                self.SOURCE_ID, self.DATASET, 'index_page',
                normalized, raw_hash, self.PARSER_ID, self.PARSER_VERSION
            )
            if ir.inserted:
                result.records_new += 1
            else:
                result.records_unchanged += 1
        except Exception as e:
            result.records_invalid += 1


if __name__ == '__main__':
    BlenderOpenDataCollector().run()
