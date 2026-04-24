from __future__ import annotations

import asyncio
import contextlib
import logging

import httpx

LOGGER = logging.getLogger(__name__)


class KeepalivePinger:
    def __init__(
        self,
        *,
        base_url: str | None,
        path: str = "/api/health",
        interval_seconds: float = 240.0,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = (base_url or "").strip()
        self._path = path.strip() or "/api/health"
        self._interval_seconds = max(30.0, float(interval_seconds))
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._base_url)

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._client = httpx.AsyncClient(timeout=self._timeout_seconds, follow_redirects=True)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        LOGGER.info(
            "Keepalive ping enabled: url=%s interval=%.0fs",
            self._ping_url,
            self._interval_seconds,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def _ping_url(self) -> str:
        base = self._base_url.rstrip("/")
        path = self._path if self._path.startswith("/") else f"/{self._path}"
        return f"{base}{path}"

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self._ping_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except TimeoutError:
                continue

    async def _ping_once(self) -> None:
        if self._client is None:
            return
        try:
            response = await self._client.get(self._ping_url)
            if response.status_code >= 400:
                LOGGER.warning(
                    "Keepalive ping failed: status=%s url=%s",
                    response.status_code,
                    self._ping_url,
                )
        except (httpx.HTTPError, OSError, RuntimeError, TimeoutError) as exc:
            LOGGER.warning("Keepalive ping error for %s: %s", self._ping_url, exc)
