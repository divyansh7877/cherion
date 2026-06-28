"""Async ClinicalTrials.gov v2 client: pagination, retry, bounded concurrency."""

from __future__ import annotations

import asyncio

import httpx

BASE_URL = "https://clinicaltrials.gov/api/v2"
# The API tolerates concurrent bursts well (tested ~20 concurrent, no 429s);
# we cap concurrency to stay polite while keeping faceted grouped bars fast.
_MAX_CONCURRENCY = 12


class CTGovError(RuntimeError):
    pass


class CTGovClient:
    """Thin async wrapper around the /studies and /stats endpoints.

    Returns raw JSON dicts; all interpretation happens in the aggregation layer.
    """

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict) -> dict:
        last_exc: Exception | None = None
        for attempt in range(4):
            async with self._sem:
                try:
                    resp = await client.get(f"{self.base_url}{path}", params=params)
                    if resp.status_code == 429:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.HTTPError, ValueError) as exc:
                    last_exc = exc
            await asyncio.sleep(0.5 * (attempt + 1))
        raise CTGovError(f"GET {path} failed after retries: {last_exc}")

    async def search_studies(
        self, params: dict, max_records: int = 1000, max_pages: int = 10
    ) -> tuple[list[dict], int]:
        """Page through /studies. Returns (studies, total_count).

        Stops at ``max_records`` or ``max_pages``. The caller compares the returned
        length against total_count to flag sampling in meta.
        """
        studies: list[dict] = []
        total = 0
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for _ in range(max_pages):
                page_params = dict(params)
                if page_token:
                    page_params["pageToken"] = page_token
                data = await self._get(client, "/studies", page_params)
                total = data.get("totalCount", total)
                studies.extend(data.get("studies", []))
                page_token = data.get("nextPageToken")
                if not page_token or len(studies) >= max_records:
                    break
        return studies[:max_records], total

    async def count(self, params: dict, sample: int = 3) -> tuple[int, list[dict]]:
        """Single exact-count query: returns (totalCount, up-to-`sample` example studies)."""
        q = dict(params)
        q["countTotal"] = "true"
        q["pageSize"] = str(sample)
        q.setdefault("fields", "protocolSection.identificationModule")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            data = await self._get(client, "/studies", q)
        return data.get("totalCount", 0), data.get("studies", [])

    async def count_many(self, param_sets: list[dict], sample: int = 3) -> list[tuple[int, list[dict]]]:
        """Run many count queries concurrently (one shared client). Order preserved."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:

            async def one(params: dict) -> tuple[int, list[dict]]:
                q = dict(params)
                q["countTotal"] = "true"
                q["pageSize"] = str(sample)
                q.setdefault("fields", "protocolSection.identificationModule")
                data = await self._get(client, "/studies", q)
                return data.get("totalCount", 0), data.get("studies", [])

            return await asyncio.gather(*(one(p) for p in param_sets))

    async def field_values(self, fields: list[str]) -> dict:
        """Call /stats/field/values for authoritative GLOBAL value distributions."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._get(client, "/stats/field/values", {"fields": ",".join(fields)})
