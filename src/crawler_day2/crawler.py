from crawler_day1.crawler import AsyncCrawler as BaseAsyncCrawler
from crawler_day2.html_parser import HTMLParser


class AsyncCrawler(BaseAsyncCrawler):
    def __init__(
        self,
        max_concurrent: int = 10,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        super().__init__(
            max_concurrent=max_concurrent,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        self._parser = HTMLParser()

    async def fetch_and_parse(self, url: str) -> dict:
        html = await self.fetch_url(url)

        if not html:
            return {
                "url": url,
                "title": "",
                "text": "",
                "links": [],
                "metadata": {},
                "images": [],
                "headings": [],
                "tables": [],
                "lists": [],
                "errors": ["Failed to fetch HTML"],
            }

        return await self._parser.parse_html(html, url)