"""OSHWA Certification Collector — open source hardware identity.

Downloads certified open hardware projects from the OSHWA API.
Useful for: open robot hardware, open controllers, open actuators.

Source: https://certificationapi.oshwa.org
Licence: OSHWA data is CC0
"""

import json
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import insert_source_record


class OshwaCollector(BaseCollector):
    SOURCE_ID = 'oshwa'
    DATASET = 'certifications'
    PARSER_ID = 'oshwa_api_v1'

    def fetch(self):
        """Fetch all OSHWA certified projects via paginated API."""
        all_projects = []
        page = 1
        per_page = 100

        while True:
            url = f'https://certificationapi.oshwa.org/api/projects?page={page}&perPage={per_page}'
            acq = self._fetch_url(url, timeout=30)
            if not acq or acq.status != 200:
                break

            try:
                data = json.loads(acq.content)
                projects = data if isinstance(data, list) else data.get('projects', data.get('data', []))
                if not projects:
                    break
                all_projects.extend(projects)
                if len(projects) < per_page:
                    break
                page += 1
            except (json.JSONDecodeError, KeyError):
                break

        if not all_projects:
            return None
        return json.dumps(all_projects).encode()

    def parse(self, raw_content, raw_hash, result):
        """Parse OSHWA project records."""
        projects = json.loads(raw_content)
        for project in projects:
            native_id = str(project.get('id', ''))
            if not native_id:
                result.records_invalid += 1
                continue

            normalized = {
                'source_native_id': native_id,
                'name': project.get('name', ''),
                'description': project.get('description', ''),
                'project_url': project.get('projectUrl', ''),
                'repository_url': project.get('repositoryUrl', ''),
                'country': project.get('country', ''),
                'responsible_party': project.get('responsibleParty', ''),
                'primary_type': project.get('primaryType', ''),
                'additional_type': project.get('additionalType', ''),
                'hardware_license': project.get('hardwareLicense', ''),
                'software_license': project.get('softwareLicense', ''),
                'documentation_license': project.get('documentationLicense', ''),
                'version': project.get('version', ''),
                'revision': project.get('revision', ''),
                'manufacturer': project.get('manufacturer', ''),
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
    OshwaCollector().run()
