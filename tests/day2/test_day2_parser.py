import pytest
import pytest_asyncio
from aiohttp import web
from bs4 import BeautifulSoup

from crawler_day2.crawler import AsyncCrawler
from crawler_day2.html_parser import HTMLParser


VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="Test description">
    <meta name="keywords" content="python, async, parser">
</head>
<body>
    <h1>Main heading</h1>
    <h2>Sub heading</h2>
    <p>Hello from test page.</p>
    <a href="/about">About</a>
    <img src="/images/logo.png" alt="Logo">
    <table>
        <tr>
            <th>Name</th>
            <th>Role</th>
        </tr>
        <tr>
            <td>Alice</td>
            <td>Engineer</td>
        </tr>
    </table>
    <ul>
        <li>First item</li>
        <li>Second item</li>
    </ul>
    <script>console.log("hidden")</script>
    <style>body { color: red; }</style>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_parse_html_extracts_title_metadata_and_text():
    parser = HTMLParser()

    result = await parser.parse_html(VALID_HTML, "https://example.com")

    assert result["url"] == "https://example.com"
    assert result["title"] == "Test Page"
    assert result["metadata"] == {
        "title": "Test Page",
        "description": "Test description",
        "keywords": "python, async, parser",
    }
    assert result["links"] == ["https://example.com/about"]
    assert result["images"] == [
        {
            "src": "https://example.com/images/logo.png",
            "alt": "Logo",
        }
    ]
    assert result["headings"] == [
        {
            "level": "h1",
            "text": "Main heading",
        },
        {
            "level": "h2",
            "text": "Sub heading",
        },
    ]
    assert result["tables"] == [
        [
            ["Name", "Role"],
            ["Alice", "Engineer"],
        ]
    ]
    assert result["lists"] == [
        {
            "type": "ul",
            "items": ["First item", "Second item"],
        }
    ]
    assert "Hello from test page." in result["text"]
    assert "console.log" not in result["text"]
    assert "color: red" not in result["text"]
    assert result["errors"] == []


def test_extract_text_with_selector():
    parser = HTMLParser()
    soup = BeautifulSoup(VALID_HTML, "lxml")

    result = parser.extract_text(soup, selector="p")

    assert result == "Hello from test page."


@pytest.mark.asyncio
async def test_parse_broken_html_does_not_crash():
    parser = HTMLParser()
    broken_html = "<html><head><title>Broken<title></head><body><h1>Hello"

    result = await parser.parse_html(broken_html, "https://example.com/broken")

    assert result["url"] == "https://example.com/broken"
    assert isinstance(result, dict)
    assert "text" in result
    assert "metadata" in result
    assert "errors" in result


def test_extract_links_converts_relative_urls_and_filters_invalid_links():
    html = """
    <html>
    <body>
        <a href="/about">About</a>
        <a href="contact">Contact</a>
        <a href="../archive">Archive</a>
        <a href="https://external.com/news">External</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="javascript:void(0)">JS</a>
        <a href="">Empty</a>
        <a href="#top">Anchor</a>
        <a>No href</a>
        <a href="/about">Duplicate</a>
    </body>
    </html>
    """

    parser = HTMLParser()
    soup = BeautifulSoup(html, "lxml")

    links = parser.extract_links(
        soup,
        base_url="https://example.com/articles/page",
    )

    assert links == [
        "https://example.com/about",
        "https://example.com/articles/contact",
        "https://example.com/archive",
        "https://external.com/news",
    ]


@pytest.mark.asyncio
async def test_parse_html_includes_extracted_links():
    html = """
    <html>
    <body>
        <a href="/page1">Page 1</a>
        <a href="page2">Page 2</a>
    </body>
    </html>
    """

    parser = HTMLParser()

    result = await parser.parse_html(html, "https://example.com/articles/start")

    assert result["links"] == [
        "https://example.com/page1",
        "https://example.com/articles/page2",
    ]

def test_extract_images_returns_src_and_alt_with_absolute_urls():
    html = """
    <html>
    <body>
        <img src="/images/logo.png" alt="Logo">
        <img src="https://cdn.example.com/banner.jpg" alt="Banner">
        <img src="">
        <img>
        <img src="data:image/png;base64,abc" alt="Inline">
    </body>
    </html>
    """

    parser = HTMLParser()
    soup = BeautifulSoup(html, "lxml")

    images = parser.extract_images(soup, "https://example.com/page")

    assert images == [
        {
            "src": "https://example.com/images/logo.png",
            "alt": "Logo",
        },
        {
            "src": "https://cdn.example.com/banner.jpg",
            "alt": "Banner",
        },
    ]


def test_extract_headings_returns_h1_h2_h3_only():
    html = """
    <html>
    <body>
        <h1>Main</h1>
        <h2>Section</h2>
        <h3>Subsection</h3>
        <h4>Ignored</h4>
        <h2>   </h2>
    </body>
    </html>
    """

    parser = HTMLParser()
    soup = BeautifulSoup(html, "lxml")

    headings = parser.extract_headings(soup)

    assert headings == [
        {
            "level": "h1",
            "text": "Main",
        },
        {
            "level": "h2",
            "text": "Section",
        },
        {
            "level": "h3",
            "text": "Subsection",
        },
    ]

def test_extract_tables_returns_rows_and_cells():
    html = """
    <html>
    <body>
        <table>
            <tr>
                <th>Name</th>
                <th>Age</th>
            </tr>
            <tr>
                <td>Alice</td>
                <td>30</td>
            </tr>
            <tr></tr>
        </table>
    </body>
    </html>
    """

    parser = HTMLParser()
    soup = BeautifulSoup(html, "lxml")

    tables = parser.extract_tables(soup)

    assert tables == [
        [
            ["Name", "Age"],
            ["Alice", "30"],
        ]
    ]


def test_extract_lists_returns_ul_and_ol_items():
    html = """
    <html>
    <body>
        <ul>
            <li>First</li>
            <li>Second</li>
        </ul>
        <ol>
            <li>Step one</li>
            <li>Step two</li>
        </ol>
        <ul></ul>
    </body>
    </html>
    """

    parser = HTMLParser()
    soup = BeautifulSoup(html, "lxml")

    lists = parser.extract_lists(soup)

    assert lists == [
        {
            "type": "ul",
            "items": ["First", "Second"],
        },
        {
            "type": "ol",
            "items": ["Step one", "Step two"],
        },
    ]

@pytest_asyncio.fixture
async def day2_test_server(unused_tcp_port: int):
    async def page_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>Integration Page</title>
                <meta name="description" content="Integration description">
                <meta name="keywords" content="integration, async">
            </head>
            <body>
                <h1>Integration heading</h1>
                <p>Integration page text.</p>
                <a href="/about">About</a>
                <img src="/logo.png" alt="Logo">
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Status</td>
                        <td>OK</td>
                    </tr>
                </table>
                <ol>
                    <li>First step</li>
                    <li>Second step</li>
                </ol>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/", page_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    yield f"http://127.0.0.1:{unused_tcp_port}"

    await runner.cleanup()

@pytest.mark.asyncio
async def test_fetch_and_parse_loads_and_parses_html(day2_test_server):
    url = f"{day2_test_server}/"

    async with AsyncCrawler(max_concurrent=2) as crawler:
        result = await crawler.fetch_and_parse(url)
    
    assert result["url"] == url
    assert result["title"] == "Integration Page"
    assert result["metadata"] == {
        "title": "Integration Page",
        "description": "Integration description",
        "keywords": "integration, async",
    }
    assert "Integration page text." in result["text"]
    assert result["links"] == [f"{day2_test_server}/about"]
    assert result["images"] == [
        {
            "src": f"{day2_test_server}/logo.png",
            "alt": "Logo",
        }
    ]
    assert result["headings"] == [
        {
            "level": "h1",
            "text": "Integration heading",
        }
    ]
    assert result["tables"] == [
        [
            ["Name", "Value"],
            ["Status", "OK"],
        ]
    ]
    assert result["lists"] == [
        {
            "type": "ol",
            "items": ["First step", "Second step"],
        }
    ]
    assert result["errors"] == []

@pytest.mark.asyncio
async def test_fetch_and_parse_returns_error_for_failed_fetch(day2_test_server):
    url = f"{day2_test_server}/missing"

    async with AsyncCrawler(max_concurrent=2) as crawler:
        result = await crawler.fetch_and_parse(url)
    
    assert result["url"] == url
    assert result["title"] == ""
    assert result["text"] == ""
    assert result["links"] == []
    assert result["metadata"] == {}
    assert result["images"] == []
    assert result["headings"] == []
    assert result["tables"] == []
    assert result["lists"] == []
    assert result["errors"] == ["Failed to fetch HTML"]
