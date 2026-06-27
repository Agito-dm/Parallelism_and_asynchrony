from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse


@dataclass
class CrawlerStats:
    total_pages: int = 0
    successful: int = 0
    failed: int = 0

    status_codes: Counter = field(default_factory=Counter)
    domains: Counter = field(default_factory=Counter)

    started_at: datetime | None = None
    finished_at: datetime | None = None

    def start(self) -> None:
        self.started_at = datetime.now(timezone.utc)
        self.finished_at = None

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    def reset(self) -> None:
        self.total_pages = 0
        self.successful = 0
        self.failed = 0
        self.status_codes.clear()
        self.domains.clear()
        self.started_at = None
        self.finished_at = None

    def _ensure_started(self) -> None:
        if self.started_at is None:
            self.start()

    def record_success(self, url: str, status_code: int = 200) -> None:
        self._ensure_started()

        self.total_pages += 1
        self.successful += 1
        self.status_codes[str(status_code)] += 1
        self._record_domain(url)

    def record_failure(self, url: str, status_code: int | None = None) -> None:
        self._ensure_started()

        self.total_pages += 1
        self.failed += 1

        if status_code is not None:
            self.status_codes[str(status_code)] += 1

        self._record_domain(url)

    def _record_domain(self, url: str) -> None:
        domain = urlparse(url).netloc

        if domain:
            self.domains[domain] += 1

    @property
    def duration_seconds(self) -> float:
        if self.started_at is None:
            return 0.0

        end = self.finished_at or datetime.now(timezone.utc)

        return max((end - self.started_at).total_seconds(), 0.0)

    @property
    def pages_per_second(self) -> float:
        duration = self.duration_seconds

        if duration <= 0:
            return 0.0

        return self.total_pages / duration

    def to_dict(self) -> dict:
        return {
            "total_pages": self.total_pages,
            "successful": self.successful,
            "failed": self.failed,
            "status_codes": dict(self.status_codes),
            "top_domains": dict(self.domains.most_common(10)),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "pages_per_second": self.pages_per_second,
        }
