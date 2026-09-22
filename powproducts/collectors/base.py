"""Collector Base — hardened base class for all collectors.

Uses shared/persist.py for all database operations.
Every HTTP response is stored as a separate raw blob (per-acquisition).
Collectors own their collector_run records.
"""

import json
import time
import requests
from datetime import datetime, timezone
from typing import Optional
from powproducts.shared.persist import (
    get_db, store_raw, store_acquisition, insert_source_record,
    get_cursor, set_cursor, log_run, persist_health, check_source_rights,
    InsertResult, RawStoreResult, Acquisition
)


class CollectorResult:
    def __init__(self):
        self.raw_fetched = 0
        self.raw_new = 0
        self.records_new = 0
        self.records_unchanged = 0
        self.records_changed = 0
        self.records_invalid = 0
        self.errors = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at = None
        self.acquisitions = []
        # HTTP request counters
        self.requests_attempted = 0
        self.requests_200 = 0
        self.requests_403 = 0
        self.requests_404 = 0
        self.requests_429 = 0
        self.requests_failed = 0


class BaseCollector:
    SOURCE_ID = ''
    DATASET = ''
    PARSER_ID = ''
    PARSER_VERSION = '1.0.0'
    RIGHTS_STATUS = 'terms_review'  # Override in subclass

    def fetch(self) -> Optional[bytes]:
        """Fetch raw data. Override in subclasses."""
        raise NotImplementedError

    def parse(self, raw_content: bytes, raw_hash: str, result: CollectorResult):
        """Parse raw content and mutate `result` with counts."""
        raise NotImplementedError

    def _check_rights(self) -> bool:
        """Check if this source is allowed to run in production."""
        rights = check_source_rights(self.SOURCE_ID)
        if not rights['allowed']:
            print(f'  BLOCKED: {rights.get("reason", rights["status"])}')
            return False
        return True

    def _fetch_url(self, url: str, max_retries: int = 3, timeout: int = 30,
                   headers: dict = None) -> Optional[Acquisition]:
        """Fetch a URL. Stores each response as its own raw blob + raw_acquisition.

        Returns Acquisition object with content, URL, status, hash.
        Returns None on failure after retries.
        """
        merged = {'User-Agent': 'PowProducts/1.0'}
        if headers:
            merged.update(headers)

        for attempt in range(max_retries):
            try:
                self.requests_attempted += 1
                resp = requests.get(url, timeout=timeout, headers=merged)

                if resp.status_code == 200:
                    self.requests_200 += 1
                    content = resp.content
                    raw_result = store_raw(content, self.SOURCE_ID)
                    acq = Acquisition(
                        content=content,
                        requested_url=url,
                        final_url=str(resp.url),
                        status=resp.status_code,
                        content_type=resp.headers.get('content-type', ''),
                        etag=resp.headers.get('etag', ''),
                        last_modified=resp.headers.get('last-modified', ''),
                        content_length=len(content),
                    )
                    acquisition_id = store_acquisition(
                        self.SOURCE_ID, self.DATASET, url, resp.status_code,
                        raw_result.sha256, acq.content_type, acq.etag,
                        acq.last_modified, acq.content_length, acq.final_url
                    )
                    acq.sha256 = raw_result.sha256
                    acq.acquisition_id = acquisition_id
                    return acq

                if resp.status_code == 403:
                    self.requests_403 += 1
                    # Store the 403 response as evidence
                    store_acquisition(
                        self.SOURCE_ID, self.DATASET, url, 403,
                        hashlib.sha256(resp.content).hexdigest(),
                        content_type=resp.headers.get('content-type', ''),
                        content_length=len(resp.content)
                    )
                elif resp.status_code == 404:
                    self.requests_404 += 1
                elif resp.status_code == 429:
                    self.requests_429 += 1
                    time.sleep(min(60, 2 ** (attempt + 2)))
                    continue
                else:
                    self.requests_failed += 1

                time.sleep(2 ** attempt)
            except requests.exceptions.RequestException:
                self.requests_failed += 1
                time.sleep(2 ** attempt)

        return None

    def run(self) -> CollectorResult:
        result = CollectorResult()
        print(f'{self.SOURCE_ID} — {self.DATASET}')
        print('=' * 50)

        # Rights gate
        if not self._check_rights():
            result.errors.append('rights_blocked')
            result.finished_at = datetime.now(timezone.utc).isoformat()
            log_run(
                self.SOURCE_ID, 'blocked',
                started_at=result.started_at, finished_at=result.finished_at,
                error='rights_blocked'
            )
            return result

        try:
            print('  Fetching...')
            raw_content = self.fetch()
            if raw_content is None:
                result.errors.append('fetch_failed')
                print('  FETCH FAILED')
                return result

            result.raw_fetched = 1

            raw_result = store_raw(raw_content, self.SOURCE_ID)
            raw_hash = raw_result.sha256
            result.raw_new = 1 if raw_result.inserted else 0

            store_acquisition(
                self.SOURCE_ID, self.DATASET,
                url=f'{self.SOURCE_ID}://batch',
                http_status=200,
                sha256=raw_hash,
                content_length=len(raw_content),
            )
            print(f'  Raw: {raw_hash[:12]}... ({len(raw_content):,} bytes)')

            print('  Parsing...')
            self.parse(raw_content, raw_hash, result)
            print(f'  New: {result.records_new} | Unchanged: {result.records_unchanged} | Changed: {result.records_changed}')
            if result.records_invalid > 0:
                print(f'  Invalid: {result.records_invalid}')

        except Exception as e:
            result.errors.append(str(e))
            print(f'  ERROR: {e}')

        finally:
            result.finished_at = datetime.now(timezone.utc).isoformat()
            log_run(
                self.SOURCE_ID,
                'ok' if not result.errors else 'error',
                result.raw_fetched, result.raw_new,
                result.records_new, result.records_unchanged, result.records_changed,
                result.records_invalid,
                requests_attempted=self.requests_attempted,
                requests_200=self.requests_200,
                requests_403=self.requests_403,
                requests_404=self.requests_404,
                requests_429=self.requests_429,
                requests_failed=self.requests_failed,
                error=json.dumps(result.errors) if result.errors else None,
                started_at=result.started_at, finished_at=result.finished_at,
            )
            from powproducts.layer1.health import health_from_run_result
            health = health_from_run_result(self.SOURCE_ID, self.SOURCE_ID, result)
            persist_health(self.SOURCE_ID, health.to_dict())
        return result
