"""PCI ID Repository Collector — hardware identity substrate.

Downloads the canonical pci.ids file and parses vendor/device/class IDs.
Excellent for GPU, NIC, accelerator, and controller identity.

Source: https://pci-ids.ucw.cz/v2.2/pci.ids
Licence: GPL v2+ / BSD-3
"""

import json
import re
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import insert_source_record


class PciIdsCollector(BaseCollector):
    SOURCE_ID = 'pci_ids'
    DATASET = 'pci_ids'
    PARSER_ID = 'pci_ids_parser_v1'

    def fetch(self):
        """Fetch pci.ids from the canonical mirror."""
        acq = self._fetch_url('https://pci-ids.ucw.cz/v2.2/pci.ids', timeout=30)
        if acq and acq.status == 200:
            return acq.content
        # Fallback to GitHub mirror
        acq = self._fetch_url(
            'https://raw.githubusercontent.com/pciutils/pciids/master/pci.ids',
            timeout=30
        )
        if acq and acq.status == 200:
            return acq.content
        return None

    def parse(self, raw_content, raw_hash, result):
        """Parse pci.ids format: indentation-based hierarchy."""
        text = raw_content.decode('utf-8', errors='replace')
        lines = text.split('\n')

        current_vendor = None
        current_class = None
        in_classes = False

        for line in lines:
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                if line and 'Class' in line:
                    in_classes = True
                continue

            # Vendor line: starts at column 0 (no tab)
            if not line.startswith('\t') and not line.startswith('  '):
                if in_classes:
                    # Class line: "C02 Display controller"
                    match = re.match(r'^C\s*([0-9A-Fa-f]{2})\s+(.+)', line)
                    if match:
                        current_class = {
                            'class_id': f'C{match.group(1)}',
                            'class_name': match.group(2).strip(),
                        }
                else:
                    # Vendor line: "10de NVIDIA Corporation"
                    match = re.match(r'^([0-9A-Fa-f]{4})\s+(.+)', line)
                    if match:
                        current_vendor = {
                            'vendor_id': match.group(1),
                            'vendor_name': match.group(2).strip(),
                        }
                continue

            # Device line: one tab indent
            if line.startswith('\t') and not line.startswith('\t\t'):
                device_line = line.strip()
                match = re.match(r'^([0-9A-Fa-f]{4})\s+(.+)', device_line)
                if match and current_vendor:
                    device = {
                        'vendor_id': current_vendor['vendor_id'],
                        'vendor_name': current_vendor['vendor_name'],
                        'device_id': match.group(1),
                        'device_name': match.group(2).strip(),
                    }
                    native_id = f"{device['vendor_id']}:{device['device_id']}"
                    normalized = {
                        'source_native_id': native_id,
                        'vendor_id': device['vendor_id'],
                        'vendor_name': device['vendor_name'],
                        'device_id': device['device_id'],
                        'device_name': device['device_name'],
                        'type': 'device',
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

            # Subsystem line: two tab indents — skip for now (too granular)
            # Subclass line in classes section: one tab indent
            elif in_classes and line.startswith('\t') and not line.startswith('\t\t'):
                subclass_line = line.strip()
                match = re.match(r'^([0-9A-Fa-f]{2})\s+(.+)', subclass_line)
                if match and current_class:
                    native_id = f"{current_class['class_id']}:{match.group(1)}"
                    normalized = {
                        'source_native_id': native_id,
                        'class_id': current_class['class_id'],
                        'class_name': current_class['class_name'],
                        'subclass_id': match.group(1),
                        'subclass_name': match.group(2).strip(),
                        'type': 'class',
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


if __name__ == '__main__':
    PciIdsCollector().run()
