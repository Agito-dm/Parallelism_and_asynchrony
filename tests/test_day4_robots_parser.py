from crawler_day4.robots_parser import RobotsParser


async def test_robots_parser_fetches_and_blocks_disallowed_url(monkeypatch):
    parser = RobotsParser()

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow: /private
Allow: /public
Crawl-delay: 0.5
"""

    monkeypatch.setattr(parser, "_download_robots", fake_download_robots)

    rules = await parser.fetch_robots("https://example.com/index.html")

    assert rules["available"] is True
    assert rules["robots_url"] == "https://example.com/robots.txt"

    assert parser.can_fetch("https://example.com/public/page") is True
    assert parser.can_fetch("https://example.com/private/page") is False
    assert parser.get_crawl_delay("*", "https://example.com") == 0.5


async def test_robots_parser_caches_rules_per_domain(monkeypatch):
    parser = RobotsParser()
    calls = 0

    async def fake_download_robots(robots_url: str) -> str:
        nonlocal calls
        calls += 1

        return """
User-agent: *
Disallow: /private
"""

    monkeypatch.setattr(parser, "_download_robots", fake_download_robots)

    first_rules = await parser.fetch_robots("https://example.com/page-1")
    second_rules = await parser.fetch_robots("https://example.com/page-2")

    assert calls == 1
    assert first_rules is second_rules


async def test_robots_parser_uses_separate_cache_for_different_domains(monkeypatch):
    parser = RobotsParser()
    requested_robots_urls: list[str] = []

    async def fake_download_robots(robots_url: str) -> str:
        requested_robots_urls.append(robots_url)

        return """
User-agent: *
Disallow:
"""

    monkeypatch.setattr(parser, "_download_robots", fake_download_robots)

    await parser.fetch_robots("https://example.com/page")
    await parser.fetch_robots("https://python.org/page")

    assert requested_robots_urls == [
        "https://example.com/robots.txt",
        "https://python.org/robots.txt",
    ]


async def test_robots_parser_allows_urls_when_robots_txt_is_missing(monkeypatch):
    parser = RobotsParser()

    async def fake_download_robots(robots_url: str) -> None:
        return None

    monkeypatch.setattr(parser, "_download_robots", fake_download_robots)

    rules = await parser.fetch_robots("https://example.com/page")

    assert rules["available"] is False
    assert parser.can_fetch("https://example.com/private/page") is True
    assert parser.get_crawl_delay("*", "https://example.com") == 0.0


async def test_robots_parser_uses_specific_user_agent_crawl_delay(monkeypatch):
    parser = RobotsParser()

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Crawl-delay: 1

User-agent: MyBot
Crawl-delay: 0.25
Disallow: /blocked-for-mybot
"""

    monkeypatch.setattr(parser, "_download_robots", fake_download_robots)

    await parser.fetch_robots("https://example.com/page")

    assert parser.get_crawl_delay("*", "https://example.com") == 1.0
    assert parser.get_crawl_delay("MyBot/1.0", "https://example.com") == 0.25

    assert parser.can_fetch(
        "https://example.com/blocked-for-mybot/page",
        user_agent="MyBot/1.0",
    ) is False
