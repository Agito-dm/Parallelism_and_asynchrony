import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OutputConfig:
    type: str = "jsonl"
    filename: str = "data/day7_results.jsonl"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    filename: str = "logs/crawler_day7.log"


@dataclass
class CrawlerConfig:
    start_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)

    max_pages: int = 100
    max_depth: int = 2
    max_concurrent: int = 5
    rate_limit: float = 1.0
    respect_robots: bool = True

    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)

    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def default(cls) -> "CrawlerConfig":
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrawlerConfig":
        output_data = data.get("output", {})
        logging_data = data.get("logging", {})

        config = cls(
            start_urls=list(data.get("start_urls", [])),
            sitemap_urls=list(data.get("sitemap_urls", [])),
            max_pages=data.get("max_pages", 100),
            max_depth=data.get("max_depth", 2),
            max_concurrent=data.get("max_concurrent", 5),
            rate_limit=data.get("rate_limit", 1.0),
            respect_robots=data.get("respect_robots", True),
            include_patterns=list(data.get("include_patterns", [])),
            exclude_patterns=list(data.get("exclude_patterns", [])),
            output=OutputConfig(
                type=output_data.get("type", "jsonl"),
                filename=output_data.get("filename", "data/day7_results.jsonl"),
            ),
            logging=LoggingConfig(
                level=logging_data.get("level", "INFO"),
                filename=logging_data.get("filename", "logs/crawler_day7.log"),
            ),
        )

        config.validate()

        return config

    def validate(self) -> None:
        if self.max_pages <= 0:
            raise ValueError("max_pages must be positive")

        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")

        if self.rate_limit <= 0:
            raise ValueError("rate_limit must be positive")

        if self.output.type not in {"jsonl", "csv", "sqlite"}:
            raise ValueError("output.type must be one of: jsonl, csv, sqlite")

    @property
    def output_path(self) -> Path:
        return Path(self.output.filename)


def load_config(filename: str | Path) -> CrawlerConfig:
    path = Path(filename)

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Config file must contain JSON object")

    return CrawlerConfig.from_dict(data)
