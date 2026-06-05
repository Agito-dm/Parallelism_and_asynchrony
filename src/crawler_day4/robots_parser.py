import asyncio
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import aiohttp


class RobotsParser:
    def __init__(
        self,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        self._rules_cache: dict[str, dict] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_base_url: str | None = None

    def _get_base_url(self, url: str) -> str:
        parsed = urlparse(url)

        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                "",
                "",
                "",
                "",
            )
        )

    def _get_robots_url(self, base_url: str) -> str:
        normalized_base_url = self._get_base_url(base_url)

        return f"{normalized_base_url}/robots.txt"

    def _get_lock(self, base_url: str) -> asyncio.Lock:
        if base_url not in self._locks:
            self._locks[base_url] = asyncio.Lock()

        return self._locks[base_url]

    async def _download_robots(self, robots_url: str) -> str | None:
        timeout = aiohttp.ClientTimeout(
            sock_connect=self.connect_timeout,
            sock_read=self.read_timeout,
        )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(robots_url) as response:
                    if response.status >= 400:
                        return None

                    return await response.text()

        except aiohttp.ClientError:
            return None

        except TimeoutError:
            return None

        except asyncio.TimeoutError:
            return None

    def _parse_crawl_delays(self, robots_text: str) -> dict[str, float]:
        delays: dict[str, float] = {}

        current_user_agents: list[str] = []
        seen_rule_in_current_group = False

        for raw_line in robots_text.splitlines():
            line = raw_line.split("#", 1)[0].strip()

            if not line:
                current_user_agents = []
                seen_rule_in_current_group = False
                continue

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                if seen_rule_in_current_group:
                    current_user_agents = []
                    seen_rule_in_current_group = False

                if value:
                    current_user_agents.append(value.lower())

                continue

            if key in {"allow", "disallow", "crawl-delay"}:
                seen_rule_in_current_group = True

            if key != "crawl-delay":
                continue

            if not current_user_agents:
                continue

            try:
                delay = float(value)
            except ValueError:
                continue

            if delay < 0:
                continue

            for user_agent in current_user_agents:
                delays[user_agent] = delay

        return delays

    def _build_rules(
        self,
        base_url: str,
        robots_url: str,
        robots_text: str | None,
    ) -> dict:
        parser = RobotFileParser()
        parser.set_url(robots_url)

        if robots_text is None:
            parser.parse([])
            crawl_delays = {}
            available = False
        else:
            lines = robots_text.splitlines()
            parser.parse(lines)
            crawl_delays = self._parse_crawl_delays(robots_text)
            available = True

        return {
            "base_url": base_url,
            "robots_url": robots_url,
            "available": available,
            "parser": parser,
            "crawl_delays": crawl_delays,
        }

    async def fetch_robots(self, base_url: str) -> dict:
        normalized_base_url = self._get_base_url(base_url)
        self._last_base_url = normalized_base_url

        if normalized_base_url in self._rules_cache:
            return self._rules_cache[normalized_base_url]

        lock = self._get_lock(normalized_base_url)

        async with lock:
            if normalized_base_url in self._rules_cache:
                return self._rules_cache[normalized_base_url]

            robots_url = self._get_robots_url(normalized_base_url)
            robots_text = await self._download_robots(robots_url)

            rules = self._build_rules(
                base_url=normalized_base_url,
                robots_url=robots_url,
                robots_text=robots_text,
            )

            self._rules_cache[normalized_base_url] = rules

            return rules

    def can_fetch(
        self,
        url: str,
        user_agent: str = "*",
    ) -> bool:
        base_url = self._get_base_url(url)
        rules = self._rules_cache.get(base_url)

        if rules is None:
            return True

        parser: RobotFileParser = rules["parser"]

        return parser.can_fetch(user_agent, url)

    def _get_matching_delay(
        self,
        crawl_delays: dict[str, float],
        user_agent: str,
    ) -> float:
        normalized_user_agent = user_agent.lower()

        if normalized_user_agent in crawl_delays:
            return crawl_delays[normalized_user_agent]

        for rule_user_agent, delay in crawl_delays.items():
            if rule_user_agent == "*":
                continue

            if rule_user_agent in normalized_user_agent:
                return delay

        return crawl_delays.get("*", 0.0)

    def get_crawl_delay(
        self,
        user_agent: str = "*",
        base_url: str | None = None,
    ) -> float:
        if base_url is None:
            base_url = self._last_base_url

        if base_url is None:
            return 0.0

        normalized_base_url = self._get_base_url(base_url)
        rules = self._rules_cache.get(normalized_base_url)

        if rules is None:
            return 0.0

        crawl_delays: dict[str, float] = rules["crawl_delays"]

        return self._get_matching_delay(
            crawl_delays=crawl_delays,
            user_agent=user_agent,
        )

    def reset(self) -> None:
        self._rules_cache.clear()
        self._locks.clear()
        self._last_base_url = None