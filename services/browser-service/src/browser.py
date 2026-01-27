"""
Browser Automation Module

Provides Playwright-based browser automation for web scraping,
form filling, screenshots, and general web interaction.
"""

import asyncio
import base64
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
import html2text
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    ElementHandle,
    Error as PlaywrightError,
)

logger = logging.getLogger(__name__)


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class WaitUntil(str, Enum):
    """Page load states."""
    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"


@dataclass
class BrowserSession:
    """A browser session."""
    id: str
    user_id: str
    browser_type: BrowserType
    context: BrowserContext
    pages: Dict[str, Page] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PageInfo:
    """Information about a page."""
    page_id: str
    url: str
    title: str
    content_type: Optional[str] = None


@dataclass
class ScreenshotResult:
    """Result of a screenshot operation."""
    page_id: str
    url: str
    path: Optional[str] = None
    base64_data: Optional[str] = None
    width: int = 0
    height: int = 0


@dataclass
class ContentResult:
    """Result of content extraction."""
    page_id: str
    url: str
    title: str
    html: str
    text: str
    markdown: str
    links: List[Dict[str, str]]
    images: List[Dict[str, str]]
    metadata: Dict[str, Any]


@dataclass
class ActionResult:
    """Result of a browser action."""
    success: bool
    action: str
    element: Optional[str] = None
    value: Optional[str] = None
    error: Optional[str] = None
    screenshot: Optional[str] = None


class BrowserManager:
    """
    Manages browser instances and sessions.

    Features:
    - Multi-browser support (Chromium, Firefox, WebKit)
    - Session management with isolation
    - Screenshot and PDF generation
    - Content extraction and parsing
    - Form automation
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        default_timeout: int = 30000,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        screenshot_dir: str = "./data/screenshots",
        pdf_dir: str = "./data/pdfs",
    ):
        self.browser_type = BrowserType(browser_type)
        self.headless = headless
        self.default_timeout = default_timeout
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.screenshot_dir = Path(screenshot_dir)
        self.pdf_dir = Path(pdf_dir)

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._sessions: Dict[str, BrowserSession] = {}
        self._html_converter = html2text.HTML2Text()
        self._html_converter.ignore_links = False
        self._html_converter.ignore_images = False

        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the browser manager."""
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()

            if self._browser is None:
                browser_launcher = getattr(self._playwright, self.browser_type.value)
                self._browser = await browser_launcher.launch(
                    headless=self.headless,
                )
                logger.info(f"Browser started: {self.browser_type.value}")

    async def stop(self) -> None:
        """Stop the browser manager."""
        async with self._lock:
            # Close all sessions
            for session in list(self._sessions.values()):
                await self._close_session(session)

            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Browser stopped")

    async def create_session(
        self,
        user_id: str,
        storage_state: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        locale: str = "en-US",
        timezone: Optional[str] = None,
        geolocation: Optional[Dict[str, float]] = None,
        permissions: Optional[List[str]] = None,
    ) -> str:
        """
        Create a new browser session.

        Args:
            user_id: User identifier
            storage_state: Cookies and local storage to restore
            user_agent: Custom user agent
            locale: Browser locale
            timezone: Timezone ID
            geolocation: Geolocation coordinates
            permissions: Granted permissions

        Returns:
            Session ID
        """
        await self.start()

        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "locale": locale,
        }

        if storage_state:
            context_options["storage_state"] = storage_state
        if user_agent:
            context_options["user_agent"] = user_agent
        if timezone:
            context_options["timezone_id"] = timezone
        if geolocation:
            context_options["geolocation"] = geolocation
            if permissions is None:
                permissions = ["geolocation"]
        if permissions:
            context_options["permissions"] = permissions

        context = await self._browser.new_context(**context_options)
        context.set_default_timeout(self.default_timeout)

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = BrowserSession(
            id=session_id,
            user_id=user_id,
            browser_type=self.browser_type,
            context=context,
        )

        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    async def close_session(self, session_id: str) -> bool:
        """Close a browser session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        await self._close_session(session)
        del self._sessions[session_id]
        logger.info(f"Closed session {session_id}")
        return True

    async def _close_session(self, session: BrowserSession) -> None:
        """Internal method to close a session."""
        try:
            await session.context.close()
        except Exception as e:
            logger.warning(f"Error closing session: {e}")

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = datetime.utcnow().isoformat()
        return session

    async def new_page(
        self,
        session_id: str,
        url: Optional[str] = None,
        wait_until: str = "domcontentloaded",
    ) -> Optional[str]:
        """
        Create a new page in a session.

        Args:
            session_id: Session ID
            url: Initial URL to navigate to
            wait_until: When to consider navigation complete

        Returns:
            Page ID
        """
        session = self.get_session(session_id)
        if not session:
            return None

        page = await session.context.new_page()
        page_id = str(uuid.uuid4())
        session.pages[page_id] = page

        if url:
            await page.goto(url, wait_until=wait_until)

        logger.info(f"Created page {page_id} in session {session_id}")
        return page_id

    async def close_page(self, session_id: str, page_id: str) -> bool:
        """Close a page."""
        session = self.get_session(session_id)
        if not session or page_id not in session.pages:
            return False

        await session.pages[page_id].close()
        del session.pages[page_id]
        return True

    def get_page(self, session_id: str, page_id: str) -> Optional[Page]:
        """Get a page by ID."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.pages.get(page_id)

    async def navigate(
        self,
        session_id: str,
        page_id: str,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None,
    ) -> Optional[PageInfo]:
        """
        Navigate to a URL.

        Args:
            session_id: Session ID
            page_id: Page ID
            url: URL to navigate to
            wait_until: When to consider navigation complete
            timeout: Navigation timeout in milliseconds

        Returns:
            Page information
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        try:
            response = await page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout or self.default_timeout,
            )
            return PageInfo(
                page_id=page_id,
                url=page.url,
                title=await page.title(),
                content_type=response.headers.get("content-type") if response else None,
            )
        except PlaywrightError as e:
            logger.error(f"Navigation error: {e}")
            return None

    async def go_back(self, session_id: str, page_id: str) -> Optional[PageInfo]:
        """Go back in history."""
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        await page.go_back()
        return PageInfo(
            page_id=page_id,
            url=page.url,
            title=await page.title(),
        )

    async def go_forward(self, session_id: str, page_id: str) -> Optional[PageInfo]:
        """Go forward in history."""
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        await page.go_forward()
        return PageInfo(
            page_id=page_id,
            url=page.url,
            title=await page.title(),
        )

    async def reload(
        self,
        session_id: str,
        page_id: str,
        wait_until: str = "domcontentloaded",
    ) -> Optional[PageInfo]:
        """Reload the page."""
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        await page.reload(wait_until=wait_until)
        return PageInfo(
            page_id=page_id,
            url=page.url,
            title=await page.title(),
        )

    async def screenshot(
        self,
        session_id: str,
        page_id: str,
        full_page: bool = False,
        selector: Optional[str] = None,
        format: str = "png",
        quality: int = 90,
        save_to_file: bool = True,
        return_base64: bool = False,
    ) -> Optional[ScreenshotResult]:
        """
        Take a screenshot.

        Args:
            session_id: Session ID
            page_id: Page ID
            full_page: Capture full scrollable page
            selector: CSS selector for element screenshot
            format: Image format (png, jpeg)
            quality: JPEG quality (0-100)
            save_to_file: Save to file
            return_base64: Return base64-encoded data

        Returns:
            Screenshot result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        screenshot_options = {
            "full_page": full_page and not selector,
            "type": format,
        }

        if format == "jpeg":
            screenshot_options["quality"] = quality

        if selector:
            element = await page.query_selector(selector)
            if not element:
                return None
            screenshot_data = await element.screenshot(**screenshot_options)
        else:
            screenshot_data = await page.screenshot(**screenshot_options)

        result = ScreenshotResult(
            page_id=page_id,
            url=page.url,
        )

        if save_to_file:
            filename = f"{page_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
            filepath = self.screenshot_dir / filename
            with open(filepath, "wb") as f:
                f.write(screenshot_data)
            result.path = str(filepath)

        if return_base64:
            result.base64_data = base64.b64encode(screenshot_data).decode()

        # Get dimensions from viewport
        viewport = page.viewport_size
        if viewport:
            result.width = viewport["width"]
            result.height = viewport["height"]

        return result

    async def pdf(
        self,
        session_id: str,
        page_id: str,
        format: str = "A4",
        landscape: bool = False,
        print_background: bool = True,
        margin: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Generate PDF of the page.

        Args:
            session_id: Session ID
            page_id: Page ID
            format: Page format (A4, Letter, etc.)
            landscape: Landscape orientation
            print_background: Print background graphics
            margin: Page margins

        Returns:
            Path to PDF file
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        pdf_options = {
            "format": format,
            "landscape": landscape,
            "print_background": print_background,
        }

        if margin:
            pdf_options["margin"] = margin

        filename = f"{page_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.pdf_dir / filename

        await page.pdf(path=str(filepath), **pdf_options)
        return str(filepath)

    async def get_content(
        self,
        session_id: str,
        page_id: str,
        include_html: bool = True,
        max_length: int = 100000,
    ) -> Optional[ContentResult]:
        """
        Extract content from the page.

        Args:
            session_id: Session ID
            page_id: Page ID
            include_html: Include raw HTML
            max_length: Maximum content length

        Returns:
            Extracted content
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Convert to markdown
        markdown = self._html_converter.handle(html)

        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            links.append({
                "text": a.get_text(strip=True),
                "href": a["href"],
            })

        # Extract images
        images = []
        for img in soup.find_all("img", src=True):
            images.append({
                "alt": img.get("alt", ""),
                "src": img["src"],
            })

        # Extract metadata
        metadata = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                metadata[name] = content

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."
        if len(markdown) > max_length:
            markdown = markdown[:max_length] + "..."
        if include_html and len(html) > max_length:
            html = html[:max_length] + "..."

        return ContentResult(
            page_id=page_id,
            url=page.url,
            title=await page.title(),
            html=html if include_html else "",
            text=text,
            markdown=markdown,
            links=links[:100],  # Limit links
            images=images[:50],  # Limit images
            metadata=metadata,
        )

    async def click(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Click an element.

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            button: Mouse button (left, right, middle)
            click_count: Number of clicks
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="click", error="Page not found")

        try:
            await page.click(
                selector,
                button=button,
                click_count=click_count,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(
                success=True,
                action="click",
                element=selector,
            )
        except PlaywrightError as e:
            return ActionResult(
                success=False,
                action="click",
                element=selector,
                error=str(e),
            )

    async def fill(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Fill a text input.

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            value: Text to fill
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="fill", error="Page not found")

        try:
            await page.fill(
                selector,
                value,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(
                success=True,
                action="fill",
                element=selector,
                value=value,
            )
        except PlaywrightError as e:
            return ActionResult(
                success=False,
                action="fill",
                element=selector,
                value=value,
                error=str(e),
            )

    async def type_text(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        text: str,
        delay: int = 50,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Type text character by character (simulates real typing).

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes (ms)
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="type", error="Page not found")

        try:
            await page.type(
                selector,
                text,
                delay=delay,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(
                success=True,
                action="type",
                element=selector,
                value=text,
            )
        except PlaywrightError as e:
            return ActionResult(
                success=False,
                action="type",
                element=selector,
                value=text,
                error=str(e),
            )

    async def press(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        key: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Press a key.

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            key: Key to press (e.g., "Enter", "Tab", "Escape")
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="press", error="Page not found")

        try:
            await page.press(
                selector,
                key,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(
                success=True,
                action="press",
                element=selector,
                value=key,
            )
        except PlaywrightError as e:
            return ActionResult(
                success=False,
                action="press",
                element=selector,
                value=key,
                error=str(e),
            )

    async def select_option(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        label: Optional[str] = None,
        index: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Select an option from a dropdown.

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            value: Option value
            label: Option label
            index: Option index
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="select", error="Page not found")

        try:
            options = {}
            if value is not None:
                options["value"] = value
            elif label is not None:
                options["label"] = label
            elif index is not None:
                options["index"] = index

            await page.select_option(
                selector,
                **options,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(
                success=True,
                action="select",
                element=selector,
                value=str(value or label or index),
            )
        except PlaywrightError as e:
            return ActionResult(
                success=False,
                action="select",
                element=selector,
                error=str(e),
            )

    async def check(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """Check a checkbox."""
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="check", error="Page not found")

        try:
            await page.check(selector, timeout=timeout or self.default_timeout)
            return ActionResult(success=True, action="check", element=selector)
        except PlaywrightError as e:
            return ActionResult(success=False, action="check", element=selector, error=str(e))

    async def uncheck(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """Uncheck a checkbox."""
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="uncheck", error="Page not found")

        try:
            await page.uncheck(selector, timeout=timeout or self.default_timeout)
            return ActionResult(success=True, action="uncheck", element=selector)
        except PlaywrightError as e:
            return ActionResult(success=False, action="uncheck", element=selector, error=str(e))

    async def hover(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """Hover over an element."""
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="hover", error="Page not found")

        try:
            await page.hover(selector, timeout=timeout or self.default_timeout)
            return ActionResult(success=True, action="hover", element=selector)
        except PlaywrightError as e:
            return ActionResult(success=False, action="hover", element=selector, error=str(e))

    async def wait_for_selector(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        state: str = "visible",
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """
        Wait for an element.

        Args:
            session_id: Session ID
            page_id: Page ID
            selector: CSS selector
            state: Element state (attached, detached, visible, hidden)
            timeout: Timeout in milliseconds

        Returns:
            Action result
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="wait", error="Page not found")

        try:
            await page.wait_for_selector(
                selector,
                state=state,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(success=True, action="wait", element=selector)
        except PlaywrightError as e:
            return ActionResult(success=False, action="wait", element=selector, error=str(e))

    async def wait_for_navigation(
        self,
        session_id: str,
        page_id: str,
        url: Optional[str] = None,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """Wait for navigation."""
        page = self.get_page(session_id, page_id)
        if not page:
            return ActionResult(success=False, action="wait_navigation", error="Page not found")

        try:
            await page.wait_for_url(
                url or "**",
                wait_until=wait_until,
                timeout=timeout or self.default_timeout,
            )
            return ActionResult(success=True, action="wait_navigation", value=page.url)
        except PlaywrightError as e:
            return ActionResult(success=False, action="wait_navigation", error=str(e))

    async def evaluate(
        self,
        session_id: str,
        page_id: str,
        expression: str,
        arg: Optional[Any] = None,
    ) -> Tuple[bool, Any]:
        """
        Execute JavaScript in the page.

        Args:
            session_id: Session ID
            page_id: Page ID
            expression: JavaScript expression
            arg: Optional argument to pass

        Returns:
            Tuple of (success, result)
        """
        page = self.get_page(session_id, page_id)
        if not page:
            return False, "Page not found"

        try:
            result = await page.evaluate(expression, arg)
            return True, result
        except PlaywrightError as e:
            return False, str(e)

    async def get_attribute(
        self,
        session_id: str,
        page_id: str,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        """Get an element attribute."""
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        try:
            return await page.get_attribute(selector, attribute)
        except PlaywrightError:
            return None

    async def get_text(
        self,
        session_id: str,
        page_id: str,
        selector: str,
    ) -> Optional[str]:
        """Get element text content."""
        page = self.get_page(session_id, page_id)
        if not page:
            return None

        try:
            element = await page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except PlaywrightError:
            return None

    async def query_selector_all(
        self,
        session_id: str,
        page_id: str,
        selector: str,
    ) -> List[Dict[str, Any]]:
        """Query all matching elements."""
        page = self.get_page(session_id, page_id)
        if not page:
            return []

        try:
            elements = await page.query_selector_all(selector)
            results = []
            for i, element in enumerate(elements):
                results.append({
                    "index": i,
                    "text": await element.text_content(),
                    "tag": await element.evaluate("el => el.tagName.toLowerCase()"),
                })
            return results
        except PlaywrightError:
            return []

    async def get_storage_state(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get session storage state (cookies, local storage)."""
        session = self.get_session(session_id)
        if not session:
            return None

        try:
            return await session.context.storage_state()
        except PlaywrightError:
            return None

    async def set_cookies(
        self,
        session_id: str,
        cookies: List[Dict[str, Any]],
    ) -> bool:
        """Set cookies for the session."""
        session = self.get_session(session_id)
        if not session:
            return False

        try:
            await session.context.add_cookies(cookies)
            return True
        except PlaywrightError:
            return False

    async def clear_cookies(self, session_id: str) -> bool:
        """Clear all cookies."""
        session = self.get_session(session_id)
        if not session:
            return False

        try:
            await session.context.clear_cookies()
            return True
        except PlaywrightError:
            return False

    def get_sessions_for_user(self, user_id: str) -> List[str]:
        """Get all session IDs for a user."""
        return [
            session.id
            for session in self._sessions.values()
            if session.user_id == user_id
        ]


# Singleton instance
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the browser manager singleton."""
    global _browser_manager
    if _browser_manager is None:
        from .config import get_settings
        settings = get_settings()
        _browser_manager = BrowserManager(
            browser_type=settings.browser_type,
            headless=settings.headless,
            default_timeout=settings.default_timeout,
            viewport_width=settings.default_viewport_width,
            viewport_height=settings.default_viewport_height,
            screenshot_dir=settings.screenshot_dir,
            pdf_dir=settings.pdf_dir,
        )
    return _browser_manager
