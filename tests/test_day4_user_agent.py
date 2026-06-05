from crawler_day4.crawler import AsyncCrawler


class FakeResponse:
    status = 200

    def raise_for_status(self) -> None:
        return None

    async def text(self) -> str:
        return "<html><body>Hello</body></html>"


class FakeRequestContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.requested_url: str | None = None
        self.requested_headers: dict | None = None

    def get(self, url: str, headers: dict | None = None) -> FakeRequestContext:
        self.requested_url = url
        self.requested_headers = headers

        return FakeRequestContext(FakeResponse())


async def test_day4_fetch_url_sends_user_agent_header(monkeypatch):
    crawler = AsyncCrawler(
        max_concurrent=1,
        user_agent="MyBot/1.0",
    )
    fake_session = FakeSession()

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/page")

    assert html == "<html><body>Hello</body></html>"
    assert fake_session.requested_url == "https://example.com/page"
    assert fake_session.requested_headers == {
        "User-Agent": "MyBot/1.0",
    }


async def test_day4_fetch_and_parse_uses_user_agent_fetch_url(monkeypatch):
    crawler = AsyncCrawler(
        max_concurrent=1,
        user_agent="ParserBot/2.0",
    )
    fake_session = FakeSession()

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    await crawler.fetch_and_parse("https://example.com/page")

    assert fake_session.requested_headers == {
        "User-Agent": "ParserBot/2.0",
    }
