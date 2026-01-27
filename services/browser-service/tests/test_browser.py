"""
Browser Service Tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.browser import (
    BrowserManager,
    BrowserType,
    BrowserSession,
    PageInfo,
    ScreenshotResult,
    ContentResult,
    ActionResult,
)


@pytest.fixture
def browser_manager():
    """Create a browser manager for testing."""
    return BrowserManager(
        browser_type="chromium",
        headless=True,
        default_timeout=5000,
        viewport_width=1280,
        viewport_height=720,
        screenshot_dir="./test_screenshots",
        pdf_dir="./test_pdfs",
    )


class TestBrowserManager:
    """Test browser manager operations."""

    def test_initialization(self, browser_manager):
        """Test browser manager initialization."""
        assert browser_manager.browser_type == BrowserType.CHROMIUM
        assert browser_manager.headless is True
        assert browser_manager.default_timeout == 5000
        assert browser_manager.viewport_width == 1280
        assert browser_manager.viewport_height == 720

    @pytest.mark.asyncio
    async def test_create_session(self, browser_manager):
        """Test session creation."""
        with patch.object(browser_manager, 'start', new_callable=AsyncMock):
            browser_manager._browser = MagicMock()
            mock_context = MagicMock()
            mock_context.set_default_timeout = MagicMock()
            browser_manager._browser.new_context = AsyncMock(return_value=mock_context)

            session_id = await browser_manager.create_session(
                user_id="test-user",
                locale="en-US",
            )

            assert session_id is not None
            assert session_id in browser_manager._sessions
            assert browser_manager._sessions[session_id].user_id == "test-user"

    @pytest.mark.asyncio
    async def test_close_session(self, browser_manager):
        """Test session closing."""
        # Create a mock session
        mock_context = MagicMock()
        mock_context.close = AsyncMock()

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        browser_manager._sessions["test-session"] = session

        result = await browser_manager.close_session("test-session")

        assert result is True
        assert "test-session" not in browser_manager._sessions
        mock_context.close.assert_called_once()

    def test_get_session(self, browser_manager):
        """Test getting a session."""
        mock_context = MagicMock()
        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        browser_manager._sessions["test-session"] = session

        retrieved = browser_manager.get_session("test-session")

        assert retrieved is not None
        assert retrieved.id == "test-session"
        assert retrieved.user_id == "test-user"

    def test_get_nonexistent_session(self, browser_manager):
        """Test getting a non-existent session."""
        result = browser_manager.get_session("nonexistent")
        assert result is None


class TestPageOperations:
    """Test page operations."""

    @pytest.fixture
    def browser_with_session(self, browser_manager):
        """Create browser manager with a mock session."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")
        mock_page.goto = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_new_page(self, browser_with_session):
        """Test creating a new page."""
        page_id = await browser_with_session.new_page(
            session_id="test-session",
            url="https://example.com",
        )

        assert page_id is not None
        session = browser_with_session.get_session("test-session")
        assert page_id in session.pages

    @pytest.mark.asyncio
    async def test_close_page(self, browser_with_session):
        """Test closing a page."""
        # First create a page
        page_id = await browser_with_session.new_page(
            session_id="test-session",
        )

        session = browser_with_session.get_session("test-session")
        session.pages[page_id].close = AsyncMock()

        # Then close it
        result = await browser_with_session.close_page("test-session", page_id)

        assert result is True
        assert page_id not in session.pages


class TestNavigation:
    """Test navigation operations."""

    @pytest.fixture
    def browser_with_page(self, browser_manager):
        """Create browser manager with a session and page."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")
        mock_page.viewport_size = {"width": 1280, "height": 720}

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session.pages["test-page"] = mock_page
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_navigate(self, browser_with_page):
        """Test navigation."""
        page = browser_with_page.get_page("test-session", "test-page")
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        page.goto = AsyncMock(return_value=mock_response)

        result = await browser_with_page.navigate(
            session_id="test-session",
            page_id="test-page",
            url="https://example.com/page",
        )

        assert result is not None
        assert result.page_id == "test-page"
        page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_go_back(self, browser_with_page):
        """Test going back in history."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.go_back = AsyncMock()

        result = await browser_with_page.go_back("test-session", "test-page")

        assert result is not None
        page.go_back.assert_called_once()

    @pytest.mark.asyncio
    async def test_go_forward(self, browser_with_page):
        """Test going forward in history."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.go_forward = AsyncMock()

        result = await browser_with_page.go_forward("test-session", "test-page")

        assert result is not None
        page.go_forward.assert_called_once()


class TestActions:
    """Test browser actions."""

    @pytest.fixture
    def browser_with_page(self, browser_manager):
        """Create browser manager with a session and page."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session.pages["test-page"] = mock_page
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_click(self, browser_with_page):
        """Test clicking an element."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.click = AsyncMock()

        result = await browser_with_page.click(
            session_id="test-session",
            page_id="test-page",
            selector="button.submit",
        )

        assert result.success is True
        assert result.action == "click"
        page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill(self, browser_with_page):
        """Test filling a text input."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.fill = AsyncMock()

        result = await browser_with_page.fill(
            session_id="test-session",
            page_id="test-page",
            selector="input[name='email']",
            value="test@example.com",
        )

        assert result.success is True
        assert result.action == "fill"
        assert result.value == "test@example.com"
        page.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_type_text(self, browser_with_page):
        """Test typing text."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.type = AsyncMock()

        result = await browser_with_page.type_text(
            session_id="test-session",
            page_id="test-page",
            selector="input[name='search']",
            text="hello world",
            delay=50,
        )

        assert result.success is True
        assert result.action == "type"
        page.type.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_option(self, browser_with_page):
        """Test selecting an option."""
        page = browser_with_page.get_page("test-session", "test-page")
        page.select_option = AsyncMock()

        result = await browser_with_page.select_option(
            session_id="test-session",
            page_id="test-page",
            selector="select[name='country']",
            value="US",
        )

        assert result.success is True
        assert result.action == "select"
        page.select_option.assert_called_once()


class TestScreenshots:
    """Test screenshot functionality."""

    @pytest.fixture
    def browser_with_page(self, browser_manager, tmp_path):
        """Create browser manager with a session and page."""
        browser_manager.screenshot_dir = tmp_path / "screenshots"
        browser_manager.screenshot_dir.mkdir()

        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.viewport_size = {"width": 1280, "height": 720}
        mock_page.screenshot = AsyncMock(return_value=b"fake_image_data")

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session.pages["test-page"] = mock_page
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_screenshot(self, browser_with_page):
        """Test taking a screenshot."""
        result = await browser_with_page.screenshot(
            session_id="test-session",
            page_id="test-page",
            save_to_file=True,
            return_base64=True,
        )

        assert result is not None
        assert result.page_id == "test-page"
        assert result.path is not None
        assert result.base64_data is not None

    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, browser_with_page):
        """Test taking a full page screenshot."""
        result = await browser_with_page.screenshot(
            session_id="test-session",
            page_id="test-page",
            full_page=True,
        )

        assert result is not None
        page = browser_with_page.get_page("test-session", "test-page")
        page.screenshot.assert_called_with(full_page=True, type="png")


class TestContentExtraction:
    """Test content extraction."""

    @pytest.fixture
    def browser_with_page(self, browser_manager):
        """Create browser manager with a session and page."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example Page")
        mock_page.content = AsyncMock(return_value="""
            <html>
            <head><title>Example Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test page.</p>
                <a href="/page1">Link 1</a>
                <a href="/page2">Link 2</a>
                <img src="/image.png" alt="Test Image">
            </body>
            </html>
        """)

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session.pages["test-page"] = mock_page
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_get_content(self, browser_with_page):
        """Test getting page content."""
        result = await browser_with_page.get_content(
            session_id="test-session",
            page_id="test-page",
        )

        assert result is not None
        assert result.title == "Example Page"
        assert "Hello World" in result.text
        assert len(result.links) == 2
        assert len(result.images) == 1


class TestJavaScriptExecution:
    """Test JavaScript execution."""

    @pytest.fixture
    def browser_with_page(self, browser_manager):
        """Create browser manager with a session and page."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=42)

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session.pages["test-page"] = mock_page
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_evaluate(self, browser_with_page):
        """Test JavaScript evaluation."""
        success, result = await browser_with_page.evaluate(
            session_id="test-session",
            page_id="test-page",
            expression="() => 40 + 2",
        )

        assert success is True
        assert result == 42


class TestCookieManagement:
    """Test cookie management."""

    @pytest.fixture
    def browser_with_session(self, browser_manager):
        """Create browser manager with a session."""
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_context.clear_cookies = AsyncMock()
        mock_context.storage_state = AsyncMock(return_value={
            "cookies": [{"name": "session", "value": "abc123"}],
            "origins": [],
        })

        session = BrowserSession(
            id="test-session",
            user_id="test-user",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        browser_manager._sessions["test-session"] = session
        return browser_manager

    @pytest.mark.asyncio
    async def test_set_cookies(self, browser_with_session):
        """Test setting cookies."""
        cookies = [
            {"name": "auth", "value": "token123", "domain": "example.com"}
        ]
        result = await browser_with_session.set_cookies("test-session", cookies)

        assert result is True
        session = browser_with_session.get_session("test-session")
        session.context.add_cookies.assert_called_once_with(cookies)

    @pytest.mark.asyncio
    async def test_clear_cookies(self, browser_with_session):
        """Test clearing cookies."""
        result = await browser_with_session.clear_cookies("test-session")

        assert result is True
        session = browser_with_session.get_session("test-session")
        session.context.clear_cookies.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_storage_state(self, browser_with_session):
        """Test getting storage state."""
        state = await browser_with_session.get_storage_state("test-session")

        assert state is not None
        assert "cookies" in state
        assert len(state["cookies"]) == 1


class TestUserIsolation:
    """Test user isolation."""

    def test_get_sessions_for_user(self, browser_manager):
        """Test getting sessions for a specific user."""
        mock_context = MagicMock()

        # Create sessions for different users
        session1 = BrowserSession(
            id="session-1",
            user_id="user-1",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session2 = BrowserSession(
            id="session-2",
            user_id="user-1",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )
        session3 = BrowserSession(
            id="session-3",
            user_id="user-2",
            browser_type=BrowserType.CHROMIUM,
            context=mock_context,
        )

        browser_manager._sessions = {
            "session-1": session1,
            "session-2": session2,
            "session-3": session3,
        }

        # Check user 1 sessions
        user1_sessions = browser_manager.get_sessions_for_user("user-1")
        assert len(user1_sessions) == 2
        assert "session-1" in user1_sessions
        assert "session-2" in user1_sessions

        # Check user 2 sessions
        user2_sessions = browser_manager.get_sessions_for_user("user-2")
        assert len(user2_sessions) == 1
        assert "session-3" in user2_sessions
