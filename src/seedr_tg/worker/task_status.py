from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class DownloadTaskStatus:
    total_bytes: int = 0
    processed_bytes: int = 0
    speed_bps: float = 0.0
    _last_sample_time: float = 0.0
    _last_sample_bytes: int = 0

    def update(self, processed_bytes: int, total_bytes: int) -> tuple[float, float]:
        now = time.monotonic()
        processed = max(0, int(processed_bytes))
        total = max(0, int(total_bytes))

        if self._last_sample_time > 0.0 and processed >= self._last_sample_bytes:
            elapsed = now - self._last_sample_time
            if elapsed > 0:
                self.speed_bps = float(processed - self._last_sample_bytes) / elapsed

        self._last_sample_time = now
        self._last_sample_bytes = processed
        self.processed_bytes = processed
        self.total_bytes = total

        if total <= 0:
            return 0.0, self.speed_bps
        percent = min(100.0, (processed / total) * 100.0)
        return percent, self.speed_bps


@dataclass(slots=True)
class UploadTaskStatus:
    total_files: int = 0
    uploaded_files: int = 0
    speed_bps: float = 0.0
    _last_sample_time: float = 0.0
    _last_sample_bytes: int = 0

    def update(
        self,
        *,
        completed_files: int,
        total_files: int,
        current_bytes: int,
        total_bytes: int,
    ) -> tuple[float, float, int, int]:
        now = time.monotonic()
        completed = max(0, int(completed_files))
        files_total = max(0, int(total_files))
        current = max(0, int(current_bytes))
        current_total = max(0, int(total_bytes))

        if self._last_sample_time > 0.0 and current >= self._last_sample_bytes:
            elapsed = now - self._last_sample_time
            if elapsed > 0:
                self.speed_bps = float(current - self._last_sample_bytes) / elapsed

        self._last_sample_time = now
        self._last_sample_bytes = current
        self.total_files = files_total
        self.uploaded_files = min(completed, files_total)

        file_fraction = 0.0
        if current_total > 0:
            file_fraction = min(1.0, max(0.0, current / current_total))

        units = self.uploaded_files + file_fraction
        percent = 100.0
        if files_total > 0:
            percent = min(100.0, (units / files_total) * 100.0)

        return percent, self.speed_bps, self.uploaded_files, files_total
