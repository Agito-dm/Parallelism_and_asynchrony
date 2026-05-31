import logging
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

class HTMLParser:
    async def parse_html(self, html: str, url: str) -> dict:
        result = {
            "url": url,
            "title": "",
            "text": "",
            "links": [],
            "metadata": {},
            "images": [],
            "headings": [],
            "tables": [],
            "lists": [],
            "errors": [],
        }

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as error:
            logger.warning(
                "Failed to parse HTML for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to parse HTML: {type(error).__name__}")
            return result

        try:
            metadata = self.extract_metadata(soup)
            result["metadata"] = metadata
            result["title"] = metadata.get("title", "")
        except Exception as error:
            logger.warning(
                "Failed to extract metadata for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract metadata: {type(error).__name__}")

        try:
            result["text"] = self.extract_text(soup)
        except Exception as error:
            logger.warning(
                "Failed to extract text for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract text: {type(error).__name__}")
        
        try:
            result["links"] = self.extract_links(soup, url)
        except Exception as error:
            logger.warning(
                "Failed to extract links for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract links: {type(error).__name__}")

        try:
            result["images"] = self.extract_images(soup, url)
        except Exception as error:
            logger.warning(
                "Failed to extract images for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract images: {type(error).__name__}")

        try:
            result["headings"] = self.extract_headings(soup)
        except Exception as error:
            logger.warning(
                "Failed to extract headings for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract headings: {type(error).__name__}")
        
        try:
            result["tables"] = self.extract_tables(soup)
        except Exception as error:
            logger.warning(
                "Failed to extract tables for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract tables: {type(error).__name__}")

        try:
            result["lists"] = self.extract_lists(soup)
        except Exception as error:
            logger.warning(
                "Failed to extract lists for URL: %s | error=%s",
                url,
                type(error).__name__,
            )
            result["errors"].append(f"Failed to extract lists: {type(error).__name__}")

        return result

    def extract_text(self, soup: BeautifulSoup, selector: str | None = None) -> str:
        if selector is not None:
            elements = soup.select(selector)
            return " ".join(
                element.get_text(separator=" ", strip=True)
                for element in elements
            )

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        title_tag = soup.find("title")

        description_tag = soup.find("meta", attrs={"name": "description"})
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})

        title = title_tag.get_text(strip=True) if title_tag else ""
        description = description_tag.get("content", "").strip() if description_tag else ""
        keywords = keywords_tag.get("content", "").strip() if keywords_tag else ""

        return {
            "title": title,
            "description": description,
            "keywords": keywords,
        }

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()

        for tag in soup.find_all("a", href=True):
            href = tag.get("href", "").strip()

            if not href or href.startswith("#"):
                continue

            absolute_url = urljoin(base_url, href)
            absolute_url, _fragment = urldefrag(absolute_url)

            if not self._is_valid_url(absolute_url):
                continue

            if absolute_url in seen:
                continue

            seen.add(absolute_url)
            links.append(absolute_url)

        return links

    def _is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)

        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images: list[dict] = []

        for tag in soup.find_all("img", src=True):
            src = tag.get("src", "").strip()

            if not src:
                continue

            absolute_src = urljoin(base_url, src)

            if not self._is_valid_url(absolute_src):
                continue

            images.append(
                {
                    "src": absolute_src,
                    "alt": tag.get("alt", "").strip(),
                }
            )

        return images

    def extract_headings(self, soup: BeautifulSoup) -> list[dict]:
        headings: list[dict] = []

        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(separator=" ", strip=True)

            if not text:
                continue

            headings.append(
                {
                    "level": tag.name,
                    "text": text,
                }
            )

        return headings

    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables: list[list[list[str]]] = []

        for table_tag in soup.find_all("table"):
            table_rows: list[list[str]] = []

            for row_tag in table_tag.find_all("tr"):
                cells = row_tag.find_all(["th", "td"])

                row = [
                    cell.get_text(separator=" ", strip=True)
                    for cell in cells
                ]

                if row:
                    table_rows.append(row)

            if table_rows:
                tables.append(table_rows)

        return tables

    def extract_lists(self, soup: BeautifulSoup) -> list[dict]:
        lists: list[dict] = []

        for list_tag in soup.find_all(["ul", "ol"]):
            items = [
                item.get_text(separator=" ", strip=True)
                for item in list_tag.find_all("li", recursive=False)
            ]

            items = [item for item in items if item]

            if not items:
                continue

            lists.append(
                {
                    "type": list_tag.name,
                    "items": items,
                }
            )

        return lists
