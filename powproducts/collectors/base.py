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
    get_cursor, set_cursor, log_run, persist_health,
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
        self.acquisitions = []  # list of Acquisition objects from this run


class BaseCollector:
    SOURCE_ID = ''
    DATASET = ''
    PARSER_ID = ''
    PARSER_VERSION = '1.0.0'

    def fetch(self) -> Optional[bytes]:
        """Fetch raw data. Override in subclasses.

        For multi-request collectors, return aggregated bytes.
        Individual acquisitions are tracked via _fetch_url().
        """
        raise NotImplementedError

    def parse(self, raw_content: bytes, raw_hash: str, result: CollectorResult):
        """Parse raw content and mutate `result` with counts.

        Subclasses MUST mutate the passed-in result, NOT return a new one.
        """
        raise NotImplementedError

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
                resp = requests.get(url, timeout=timeout, headers=merged)

                if resp.status_code in (200, 404, 403):
                    # Store the raw response as its own blob
                    content = resp.content
                    raw_result = store_raw(content, self.SOURCE_ID)

                    # Store acquisition receipt
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

                    # Persist the acquisition
                    conn = get_db()
                    cursor = conn.execute(
                        "INSERT INTO raw_acquisition "
                        "(source_id, dataset, retrieved_at, request_url, final_url, "
                        "http_status, etag, last_modified, content_type, content_length, sha256) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (self.SOURCE_ID, self.DATASET,
                         datetime.now(timezone.utc).isoformat(),
                         url, acq.final_url, acq.status, acq.etag, acq.last_modified,
                         acq.content_type, acq.content_length, raw_result.sha256)
                    )
                    acquisition_id = cursor.lastrowid
                    conn.commit()
                    conn.close()

                    acq.sha256 = raw_result.sha256
                    acq.acquisition_id = acquisition_id
                    return acq

                if resp.status_code == 429:
                    time.sleep(min(60, 2 ** (attempt + 2)))
                else:
                    time.sleep(2 ** attempt)
            except Exception:
                time.sleep(2 ** attempt)

        return None

    def run(self) -> CollectorResult:
        result = CollectorResult()
        print(f'{self.SOURCE_ID} — {self.DATASET}')
        print('=' * 50)

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

            # Store the batch acquisition
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
                json.dumps(result.errors) if result.errors else None,
                result.started_at, result.finished_at,
            )
            # Persist health for monitoring
            from powproducts.layer1.health import health_from_run_result
            health = health_from_run_result(self.SOURCE_ID, self.SOURCE_ID, result)
            persist_health(self.SOURCE_ID, health.to_dict())
        return result
