"""
Content Extraction Module

Extracts clean content from web pages.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
import html2text
import trafilatura

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    url: str
    title: str
    text: str
    markdown: str
    html: str
    author: Optional[str] = None
    publish_date: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    domain: str = ""
    word_count: int = 0
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_time_ms: float = 0


class ContentExtractor:
    """
    Web content extraction.

    Uses trafilatura for main content extraction with fallbacks.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 50000,
        user_agent: str = "Mozilla/5.0 (compatible; JARVISBot/1.0)",
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.user_agent = user_agent
        self._html_converter = html2text.HTML2Text()
        self._html_converter.ignore_links = False
        self._html_converter.ignore_images = False
        self._html_converter.body_width = 0  # No line wrapping

    async def extract(
        self,
        url: str,
        include_html: bool = False,
        include_links: bool = True,
        include_images: bool = True,
    ) -> ExtractedContent:
        """
        Extract content from a URL.

        Args:
            url: URL to extract from
            include_html: Include raw HTML
            include_links: Extract links
            include_images: Extract images

        Returns:
            ExtractedContent
        """
        start_time = datetime.utcnow()

        # Fetch the page
        html = await self._fetch_page(url)

        # Parse domain
        parsed = urlparse(url)
        domain = parsed.netloc

        # Extract using trafilatura (best for article content)
        try:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                output_format="txt",
                with_metadata=True,
            )

            if extracted:
                text = extracted
            else:
                # Fallback to BeautifulSoup
                text = self._extract_with_bs4(html)
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            text = self._extract_with_bs4(html)

        # Get metadata
        metadata = self._extract_metadata(html)
        title = metadata.get("title", "")
        author = metadata.get("author")
        publish_date = metadata.get("date")
        description = metadata.get("description")
        language = metadata.get("language")

        # Convert to markdown
        try:
            markdown = self._html_converter.handle(html)
        except Exception:
            markdown = text

        # Extract links and images
        links = []
        images = []
        soup = BeautifulSoup(html, "lxml")

        if include_links:
            for a in soup.find_all("a", href=True)[:100]:
                href = a["href"]
                if href.startswith("/"):
                    href = f"{parsed.scheme}://{domain}{href}"
                links.append({
                    "text": a.get_text(strip=True)[:100],
                    "url": href,
                })

        if include_images:
            for img in soup.find_all("img", src=True)[:50]:
                src = img["src"]
                if src.startswith("/"):
                    src = f"{parsed.scheme}://{domain}{src}"
                images.append({
                    "alt": img.get("alt", "")[:100],
                    "url": src,
                })

        # Truncate if needed
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + "..."
        if len(markdown) > self.max_content_length:
            markdown = markdown[:self.max_content_length] + "..."

        extraction_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ExtractedContent(
            url=url,
            title=title,
            text=text,
            markdown=markdown,
            html=html if include_html else "",
            author=author,
            publish_date=publish_date,
            description=description,
            language=language,
            domain=domain,
            word_count=len(text.split()),
            links=links,
            images=images,
            metadata=metadata,
            extraction_time_ms=extraction_time,
        )

    async def _fetch_page(self, url: str) -> str:
        """Fetch a web page."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.text

    def _extract_with_bs4(self, html: str) -> str:
        """Fallback extraction using BeautifulSoup."""
        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
            tag.decompose()

        # Try to find main content
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=["content", "post", "article", "entry"]) or
            soup.find(id=["content", "main", "article"]) or
            soup.body
        )

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _extract_metadata(self, html: str) -> Dict[str, Any]:
        """Extract metadata from HTML."""
        soup = BeautifulSoup(html, "lxml")
        metadata = {}

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")

            if not name or not content:
                continue

            name_lower = name.lower()

            if "title" in name_lower:
                metadata["title"] = content
            elif "description" in name_lower:
                metadata["description"] = content
            elif "author" in name_lower:
                metadata["author"] = content
            elif "date" in name_lower or "published" in name_lower:
                metadata["date"] = content
            elif name_lower == "keywords":
                metadata["keywords"] = content
            elif "language" in name_lower or "locale" in name_lower:
                metadata["language"] = content[:5]  # e.g., "en_US"

        # Try to get language from html tag
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata.setdefault("language", html_tag.get("lang"))

        return metadata

    async def extract_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 5,
    ) -> List[ExtractedContent]:
        """Extract content from multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_semaphore(url: str) -> Optional[ExtractedContent]:
            async with semaphore:
                try:
                    return await self.extract(url)
                except Exception as e:
                    logger.error(f"Failed to extract {url}: {e}")
                    return None

        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]


# Singleton instance
_content_extractor: Optional[ContentExtractor] = None


def get_content_extractor() -> ContentExtractor:
    """Get or create the content extractor singleton."""
    global _content_extractor
    if _content_extractor is None:
        from .config import get_settings
        settings = get_settings()
        _content_extractor = ContentExtractor(
            timeout=settings.extraction_timeout,
            max_content_length=settings.max_content_length,
        )
    return _content_extractor
