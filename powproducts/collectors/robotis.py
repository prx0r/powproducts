"""ROBOTIS DYNAMIXEL Collector — actuator specs and lifecycle.

Scrapes the ROBOTIS e-Manual for DYNAMIXEL actuator specifications.
Makes every supported actuator model a canonical product.

Source: https://docs.robotis.com
Licence: ROBOTIS documentation (check per-page terms)
"""

import json
import re
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import (
    insert_source_record, upsert_manufacturer, upsert_product_model,
    insert_spec_observation, insert_product_relation
)

# Known DYNAMIXEL families with their e-manual URL patterns
DYNAMIXEL_FAMILIES = {
    'x': {'name': 'DYNAMIXEL X', 'models': ['xl320', 'xl430', 'xm430-w210', 'xm430-w350',
           'xm540-w150', 'xm540-w270', 'xl330-m077', 'xl330-m288']},
    'pro': {'name': 'DYNAMIXEL Pro', 'models': ['h54-200-s500-r', 'h54-100-s500-r',
             'm54-100-s250-r', 'm54-60-s250-r', 'l54-30-s400-r', 'l54-50-s290-r']},
    'pro_plus': {'name': 'DYNAMIXEL Pro+', 'models': ['h54p-200-s500-r', 'h54p-100-s500-r',
                  'm54p-100-s250-r', 'm54p-60-s250-r', 'l54p-30-s400-r', 'l54p-50-s290-r']},
    'p': {'name': 'DYNAMIXEL P', 'models': ['ph54-200-s500-r', 'ph54-100-s500-r',
           'pm54-060-s250-r', 'pm54-040-s250-r', 'pl54-100-s500-r', 'pl54-050-s290-r']},
    'ax': {'name': 'DYNAMIXEL AX', 'models': ['ax-12a', 'ax-18a']},
    'mx': {'name': 'DYNAMIXEL MX', 'models': ['mx-12w', 'mx-28', 'mx-64', 'mx-106']},
}

# Replacement edges (discontinued → successor)
REPLACEMENTS = [
    ('ax-12a', 'xl430', 'SUPERSEDES'),
    ('ax-18a', 'xl430', 'SUPERSEDES'),
    ('mx-28', 'xm430-w350', 'SUPERSEDES'),
    ('mx-64', 'xm540-w270', 'SUPERSEDES'),
    ('mx-106', 'xm540-w270', 'SUPERSEDES'),
]


class RobotisCollector(BaseCollector):
    SOURCE_ID = 'robotis_dynamixel'
    DATASET = 'actuator_specs'
    PARSER_ID = 'robotisemanual_v1'

    def fetch(self):
        """Fetch ROBOTIS DYNAMIXEL model index."""
        acq = self._fetch_url('https://docs.robotis.com/docs/dxl/model_reference',
                               timeout=15)
        if acq and acq.status == 200:
            return acq.content
        return None

    def parse(self, raw_content, raw_hash, result):
        """Parse DYNAMIXEL model data from e-manual."""
        html = raw_content.decode('utf-8', errors='replace')

        # Ensure manufacturer exists
        upsert_manufacturer('robotis', 'ROBOTIS',
                             country_code='KR',
                             website_domain='robotis.com')

        # Parse each known family
        for family_key, family_data in DYNAMIXEL_FAMILIES.items():
            for model_id in family_data['models']:
                model_name = f'DYNAMIXEL {model_id.upper().replace("-", " ")}'
                product_id = model_id.lower().replace(' ', '-')

                upsert_product_model(
                    product_id, 'robotis', model_name,
                    product_class='actuator'
                )

                # Try to extract specs from HTML for this model
                specs = self._extract_specs_from_html(html, model_id)
                for key, val in specs.items():
                    numeric = None
                    unit = ''
                    if isinstance(val, (int, float)):
                        numeric = float(val)
                    elif isinstance(val, str):
                        # Try to extract numeric + unit
                        match = re.match(r'([\d.]+)\s*(\w+)', val)
                        if match:
                            try:
                                numeric = float(match.group(1))
                                unit = match.group(2)
                            except ValueError:
                                pass

                    insert_spec_observation(
                        product_id, key, str(val),
                        numeric_value=numeric, unit=unit,
                        truth_class='declared', source_id='robotis'
                    )

                native_id = f'dynamixel:{model_id}'
                normalized = {
                    'source_native_id': native_id,
                    'model_id': model_id,
                    'model_name': model_name,
                    'family': family_data['name'],
                    'product_id': product_id,
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

        # Add replacement relationships
        for old, new, rel_type in REPLACEMENTS:
            insert_product_relation(
                old.lower(), new.lower(), rel_type,
                truth_class='declared',
                evidence_json=json.dumps({'source': 'robotis_lifecycle'})
            )

    def _extract_specs_from_html(self, html, model_id):
        """Extract specifications from the e-manual HTML for a given model."""
        specs = {}
        # Look for model-specific section
        model_section = re.search(
            rf'{re.escape(model_id.upper())}(.*?)(?:<h[23]|$)',
            html, re.DOTALL | re.IGNORECASE
        )
        if not model_section:
            return specs

        section = model_section.group(1)

        # Extract common specs
        spec_patterns = {
            'rated_voltage': r'(?:Voltage|Input\s*Voltage)[^<]*?(\d+\.?\d*\s*V)',
            'stall_torque': r'(?:Stall\s*Torque|Torque)[^<]*?(\d+\.?\d*\s*(?:N·m|N\.m|kgf·cm))',
            'no_load_speed': r'(?:No-Load\s*Speed|Speed)[^<]*?(\d+\.?\d*\s*RPM)',
            'weight': r'(?:Weight)[^<]*?(\d+\.?\d*\s*g)',
            'protocol': r'(?:Protocol|Communication)[^<]*?(Protocol\s*[\d.]+)',
        }

        for key, pattern in spec_patterns.items():
            match = re.search(pattern, section, re.IGNORECASE)
            if match:
                specs[key] = match.group(1).strip()

        return specs


if __name__ == '__main__':
    RobotisCollector().run()
