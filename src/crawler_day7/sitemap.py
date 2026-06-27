import logging
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class SitemapParser:
    def __init__(
        self,
        *,
        session: Any | None = None,
        timeout: float = 10.0,
        max_depth: int = 10,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        self.session = session
        self.timeout = timeout
        self.max_depth = max_depth

    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        seen_sitemaps: set[str] = set()
        seen_urls: set[str] = set()

        return await self._fetch_sitemap_recursive(
            sitemap_url,
            seen_sitemaps=seen_sitemaps,
            seen_urls=seen_urls,
            depth=0,
        )

    async def _fetch_sitemap_recursive(
        self,
        sitemap_url: str,
        *,
        seen_sitemaps: set[str],
        seen_urls: set[str],
        depth: int,
    ) -> list[str]:
        if depth > self.max_depth:
            logger.warning("Sitemap max depth exceeded: %s", sitemap_url)
            return []

        if sitemap_url in seen_sitemaps:
            return []

        seen_sitemaps.add(sitemap_url)

        xml_text = await self._fetch_text(sitemap_url)
        root = ET.fromstring(xml_text)

        root_tag = self._strip_namespace(root.tag)

        if root_tag == "urlset":
            return self._extract_urls_from_urlset(root, seen_urls)

        if root_tag == "sitemapindex":
            urls: list[str] = []

            for child_sitemap_url in self._extract_sitemaps_from_index(root):
                child_urls = await self._fetch_sitemap_recursive(
                    child_sitemap_url,
                    seen_sitemaps=seen_sitemaps,
                    seen_urls=seen_urls,
                    depth=depth + 1,
                )
                urls.extend(child_urls)

            return urls

        logger.warning(
            "Unknown sitemap root tag: %s | url=%s",
            root_tag,
            sitemap_url,
        )
        return []

    async def _fetch_text(self, url: str) -> str:
        if self.session is not None:
            return await self._fetch_text_with_session(self.session, url)

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            return await self._fetch_text_with_session(session, url)

    async def _fetch_text_with_session(self, session, url: str) -> str:
        async with session.get(url) as response:
            status = getattr(response, "status", 200)

            if status >= 400:
                raise RuntimeError(f"Failed to fetch sitemap: {url} | status={status}")

            return await response.text()

    def _extract_urls_from_urlset(
        self,
        root: ET.Element,
        seen_urls: set[str],
    ) -> list[str]:
        urls: list[str] = []

        for url_element in self._iter_children_by_name(root, "url"):
            loc = self._find_child_text(url_element, "loc")

            if loc and loc not in seen_urls:
                seen_urls.add(loc)
                urls.append(loc)

        return urls

    def _extract_sitemaps_from_index(self, root: ET.Element) -> list[str]:
        sitemap_urls: list[str] = []

        for sitemap_element in self._iter_children_by_name(root, "sitemap"):
            loc = self._find_child_text(sitemap_element, "loc")

            if loc:
                sitemap_urls.append(loc)

        return sitemap_urls

    def _iter_children_by_name(
        self,
        element: ET.Element,
        name: str,
    ):
        for child in element:
            if self._strip_namespace(child.tag) == name:
                yield child

    def _find_child_text(
        self,
        element: ET.Element,
        child_name: str,
    ) -> str | None:
        for child in element:
            if self._strip_namespace(child.tag) == child_name:
                if child.text:
                    return child.text.strip()

        return None

    def _strip_namespace(self, tag: str) -> str:
        if "}" in tag:
            return tag.rsplit("}", maxsplit=1)[-1]

        return tag
