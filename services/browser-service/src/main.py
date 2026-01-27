"""
JARVIS Browser Service - Main FastAPI Application

Provides browser automation with Playwright.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .browser import (
    BrowserManager,
    get_browser_manager,
    PageInfo,
    ScreenshotResult,
    ContentResult,
    ActionResult,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name}")
    browser = get_browser_manager()
    await browser.start()
    yield
    logger.info(f"Shutting down {settings.service_name}")
    await browser.stop()


app = FastAPI(
    title="JARVIS Browser Service",
    description="Browser automation with Playwright",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class CreateSessionRequest(BaseModel):
    storage_state: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None
    locale: str = "en-US"
    timezone: Optional[str] = None
    geolocation: Optional[Dict[str, float]] = None
    permissions: Optional[List[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    created_at: str


class NewPageRequest(BaseModel):
    url: Optional[str] = None
    wait_until: str = "domcontentloaded"


class PageResponse(BaseModel):
    page_id: str
    url: str
    title: str


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "domcontentloaded"
    timeout: Optional[int] = None


class ScreenshotRequest(BaseModel):
    full_page: bool = False
    selector: Optional[str] = None
    format: str = "png"
    quality: int = 90
    save_to_file: bool = True
    return_base64: bool = False


class ScreenshotResponse(BaseModel):
    page_id: str
    url: str
    path: Optional[str] = None
    base64_data: Optional[str] = None
    width: int = 0
    height: int = 0


class PdfRequest(BaseModel):
    format: str = "A4"
    landscape: bool = False
    print_background: bool = True
    margin: Optional[Dict[str, str]] = None


class ContentResponse(BaseModel):
    page_id: str
    url: str
    title: str
    html: str
    text: str
    markdown: str
    links: List[Dict[str, str]]
    images: List[Dict[str, str]]
    metadata: Dict[str, Any]


class ClickRequest(BaseModel):
    selector: str
    button: str = "left"
    click_count: int = 1
    timeout: Optional[int] = None


class FillRequest(BaseModel):
    selector: str
    value: str
    timeout: Optional[int] = None


class TypeRequest(BaseModel):
    selector: str
    text: str
    delay: int = 50
    timeout: Optional[int] = None


class PressRequest(BaseModel):
    selector: str
    key: str
    timeout: Optional[int] = None


class SelectRequest(BaseModel):
    selector: str
    value: Optional[str] = None
    label: Optional[str] = None
    index: Optional[int] = None
    timeout: Optional[int] = None


class CheckRequest(BaseModel):
    selector: str
    timeout: Optional[int] = None


class WaitRequest(BaseModel):
    selector: str
    state: str = "visible"
    timeout: Optional[int] = None


class WaitNavigationRequest(BaseModel):
    url: Optional[str] = None
    wait_until: str = "domcontentloaded"
    timeout: Optional[int] = None


class EvaluateRequest(BaseModel):
    expression: str
    arg: Optional[Any] = None


class ActionResponse(BaseModel):
    success: bool
    action: str
    element: Optional[str] = None
    value: Optional[str] = None
    error: Optional[str] = None


class FormField(BaseModel):
    selector: str
    value: str
    action: str = "fill"  # fill, type, select, check, uncheck


class FillFormRequest(BaseModel):
    fields: List[FormField]
    submit_selector: Optional[str] = None


class CookiesRequest(BaseModel):
    cookies: List[Dict[str, Any]]


# Auth dependency
async def get_current_user(request: Request) -> dict:
    """Extract user from JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return {"user_id": payload.get("userId")}
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "browser_type": settings.browser_type,
    }


# Session management
@app.post("/session", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new browser session."""
    browser = get_browser_manager()

    # Check session limit
    existing = browser.get_sessions_for_user(user["user_id"])
    if len(existing) >= settings.max_sessions_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum sessions ({settings.max_sessions_per_user}) reached"
        )

    session_id = await browser.create_session(
        user_id=user["user_id"],
        storage_state=request.storage_state,
        user_agent=request.user_agent,
        locale=request.locale,
        timezone=request.timezone,
        geolocation=request.geolocation,
        permissions=request.permissions,
    )

    return SessionResponse(
        session_id=session_id,
        created_at=datetime.utcnow().isoformat(),
    )


@app.delete("/session/{session_id}")
async def close_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Close a browser session."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await browser.close_session(session_id)
    return {"status": "closed", "session_id": session_id}


@app.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """List user's browser sessions."""
    browser = get_browser_manager()
    session_ids = browser.get_sessions_for_user(user["user_id"])

    sessions = []
    for session_id in session_ids:
        session = browser.get_session(session_id)
        if session:
            sessions.append({
                "session_id": session.id,
                "browser_type": session.browser_type.value,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "page_count": len(session.pages),
            })

    return {"sessions": sessions}


# Page management
@app.post("/session/{session_id}/page", response_model=PageResponse)
async def new_page(
    session_id: str,
    request: NewPageRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new page in the session."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    page_id = await browser.new_page(
        session_id=session_id,
        url=request.url,
        wait_until=request.wait_until,
    )

    if not page_id:
        raise HTTPException(status_code=500, detail="Failed to create page")

    page = browser.get_page(session_id, page_id)
    return PageResponse(
        page_id=page_id,
        url=page.url if page else "",
        title=await page.title() if page else "",
    )


@app.delete("/session/{session_id}/page/{page_id}")
async def close_page(
    session_id: str,
    page_id: str,
    user: dict = Depends(get_current_user),
):
    """Close a page."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await browser.close_page(session_id, page_id)
    if not success:
        raise HTTPException(status_code=404, detail="Page not found")

    return {"status": "closed", "page_id": page_id}


@app.get("/session/{session_id}/pages")
async def list_pages(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """List pages in a session."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    pages = []
    for page_id, page in session.pages.items():
        pages.append({
            "page_id": page_id,
            "url": page.url,
            "title": await page.title(),
        })

    return {"pages": pages}


# Navigation
@app.post("/session/{session_id}/page/{page_id}/navigate", response_model=PageResponse)
async def navigate(
    session_id: str,
    page_id: str,
    request: NavigateRequest,
    user: dict = Depends(get_current_user),
):
    """Navigate to a URL."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.navigate(
        session_id=session_id,
        page_id=page_id,
        url=request.url,
        wait_until=request.wait_until,
        timeout=request.timeout,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Navigation failed")

    return PageResponse(
        page_id=result.page_id,
        url=result.url,
        title=result.title,
    )


@app.post("/session/{session_id}/page/{page_id}/back", response_model=PageResponse)
async def go_back(
    session_id: str,
    page_id: str,
    user: dict = Depends(get_current_user),
):
    """Go back in history."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.go_back(session_id, page_id)
    if not result:
        raise HTTPException(status_code=500, detail="Navigation failed")

    return PageResponse(page_id=result.page_id, url=result.url, title=result.title)


@app.post("/session/{session_id}/page/{page_id}/forward", response_model=PageResponse)
async def go_forward(
    session_id: str,
    page_id: str,
    user: dict = Depends(get_current_user),
):
    """Go forward in history."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.go_forward(session_id, page_id)
    if not result:
        raise HTTPException(status_code=500, detail="Navigation failed")

    return PageResponse(page_id=result.page_id, url=result.url, title=result.title)


@app.post("/session/{session_id}/page/{page_id}/reload", response_model=PageResponse)
async def reload(
    session_id: str,
    page_id: str,
    user: dict = Depends(get_current_user),
):
    """Reload the page."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.reload(session_id, page_id)
    if not result:
        raise HTTPException(status_code=500, detail="Reload failed")

    return PageResponse(page_id=result.page_id, url=result.url, title=result.title)


# Content extraction
@app.get("/session/{session_id}/page/{page_id}/content", response_model=ContentResponse)
async def get_content(
    session_id: str,
    page_id: str,
    include_html: bool = True,
    user: dict = Depends(get_current_user),
):
    """Get page content."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.get_content(
        session_id=session_id,
        page_id=page_id,
        include_html=include_html,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Content extraction failed")

    return ContentResponse(
        page_id=result.page_id,
        url=result.url,
        title=result.title,
        html=result.html,
        text=result.text,
        markdown=result.markdown,
        links=result.links,
        images=result.images,
        metadata=result.metadata,
    )


# Screenshots & PDF
@app.post("/session/{session_id}/page/{page_id}/screenshot", response_model=ScreenshotResponse)
async def screenshot(
    session_id: str,
    page_id: str,
    request: ScreenshotRequest,
    user: dict = Depends(get_current_user),
):
    """Take a screenshot."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.screenshot(
        session_id=session_id,
        page_id=page_id,
        full_page=request.full_page,
        selector=request.selector,
        format=request.format,
        quality=request.quality,
        save_to_file=request.save_to_file,
        return_base64=request.return_base64,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Screenshot failed")

    return ScreenshotResponse(
        page_id=result.page_id,
        url=result.url,
        path=result.path,
        base64_data=result.base64_data,
        width=result.width,
        height=result.height,
    )


@app.post("/session/{session_id}/page/{page_id}/pdf")
async def generate_pdf(
    session_id: str,
    page_id: str,
    request: PdfRequest,
    user: dict = Depends(get_current_user),
):
    """Generate PDF of the page."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    path = await browser.pdf(
        session_id=session_id,
        page_id=page_id,
        format=request.format,
        landscape=request.landscape,
        print_background=request.print_background,
        margin=request.margin,
    )

    if not path:
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return {"path": path}


# Actions
@app.post("/session/{session_id}/page/{page_id}/click", response_model=ActionResponse)
async def click(
    session_id: str,
    page_id: str,
    request: ClickRequest,
    user: dict = Depends(get_current_user),
):
    """Click an element."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.click(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        button=request.button,
        click_count=request.click_count,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/fill", response_model=ActionResponse)
async def fill(
    session_id: str,
    page_id: str,
    request: FillRequest,
    user: dict = Depends(get_current_user),
):
    """Fill a text input."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.fill(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        value=request.value,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/type", response_model=ActionResponse)
async def type_text(
    session_id: str,
    page_id: str,
    request: TypeRequest,
    user: dict = Depends(get_current_user),
):
    """Type text character by character."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.type_text(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        text=request.text,
        delay=request.delay,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/press", response_model=ActionResponse)
async def press(
    session_id: str,
    page_id: str,
    request: PressRequest,
    user: dict = Depends(get_current_user),
):
    """Press a key."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.press(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        key=request.key,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/select", response_model=ActionResponse)
async def select_option(
    session_id: str,
    page_id: str,
    request: SelectRequest,
    user: dict = Depends(get_current_user),
):
    """Select an option from a dropdown."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.select_option(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        value=request.value,
        label=request.label,
        index=request.index,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/check", response_model=ActionResponse)
async def check(
    session_id: str,
    page_id: str,
    request: CheckRequest,
    user: dict = Depends(get_current_user),
):
    """Check a checkbox."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.check(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/uncheck", response_model=ActionResponse)
async def uncheck(
    session_id: str,
    page_id: str,
    request: CheckRequest,
    user: dict = Depends(get_current_user),
):
    """Uncheck a checkbox."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.uncheck(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/hover", response_model=ActionResponse)
async def hover(
    session_id: str,
    page_id: str,
    request: CheckRequest,
    user: dict = Depends(get_current_user),
):
    """Hover over an element."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.hover(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


# Form automation
@app.post("/session/{session_id}/page/{page_id}/fill-form")
async def fill_form(
    session_id: str,
    page_id: str,
    request: FillFormRequest,
    user: dict = Depends(get_current_user),
):
    """Fill out a form."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    results = []
    for field in request.fields:
        if field.action == "fill":
            result = await browser.fill(
                session_id, page_id, field.selector, field.value
            )
        elif field.action == "type":
            result = await browser.type_text(
                session_id, page_id, field.selector, field.value
            )
        elif field.action == "select":
            result = await browser.select_option(
                session_id, page_id, field.selector, value=field.value
            )
        elif field.action == "check":
            result = await browser.check(session_id, page_id, field.selector)
        elif field.action == "uncheck":
            result = await browser.uncheck(session_id, page_id, field.selector)
        else:
            result = ActionResult(
                success=False,
                action=field.action,
                error=f"Unknown action: {field.action}"
            )

        results.append(result.__dict__)

    # Submit if requested
    submit_result = None
    if request.submit_selector:
        submit_result = await browser.click(
            session_id, page_id, request.submit_selector
        )

    return {
        "results": results,
        "submit": submit_result.__dict__ if submit_result else None,
    }


# Waiting
@app.post("/session/{session_id}/page/{page_id}/wait", response_model=ActionResponse)
async def wait_for_selector(
    session_id: str,
    page_id: str,
    request: WaitRequest,
    user: dict = Depends(get_current_user),
):
    """Wait for an element."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.wait_for_selector(
        session_id=session_id,
        page_id=page_id,
        selector=request.selector,
        state=request.state,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


@app.post("/session/{session_id}/page/{page_id}/wait-navigation", response_model=ActionResponse)
async def wait_for_navigation(
    session_id: str,
    page_id: str,
    request: WaitNavigationRequest,
    user: dict = Depends(get_current_user),
):
    """Wait for navigation."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await browser.wait_for_navigation(
        session_id=session_id,
        page_id=page_id,
        url=request.url,
        wait_until=request.wait_until,
        timeout=request.timeout,
    )

    return ActionResponse(**result.__dict__)


# JavaScript execution
@app.post("/session/{session_id}/page/{page_id}/evaluate")
async def evaluate(
    session_id: str,
    page_id: str,
    request: EvaluateRequest,
    user: dict = Depends(get_current_user),
):
    """Execute JavaScript in the page."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success, result = await browser.evaluate(
        session_id=session_id,
        page_id=page_id,
        expression=request.expression,
        arg=request.arg,
    )

    return {"success": success, "result": result}


# Element queries
@app.get("/session/{session_id}/page/{page_id}/attribute")
async def get_attribute(
    session_id: str,
    page_id: str,
    selector: str,
    attribute: str,
    user: dict = Depends(get_current_user),
):
    """Get an element attribute."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    value = await browser.get_attribute(session_id, page_id, selector, attribute)
    return {"selector": selector, "attribute": attribute, "value": value}


@app.get("/session/{session_id}/page/{page_id}/text")
async def get_text(
    session_id: str,
    page_id: str,
    selector: str,
    user: dict = Depends(get_current_user),
):
    """Get element text content."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    text = await browser.get_text(session_id, page_id, selector)
    return {"selector": selector, "text": text}


@app.get("/session/{session_id}/page/{page_id}/elements")
async def query_elements(
    session_id: str,
    page_id: str,
    selector: str,
    user: dict = Depends(get_current_user),
):
    """Query all matching elements."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    elements = await browser.query_selector_all(session_id, page_id, selector)
    return {"selector": selector, "elements": elements}


# Cookie management
@app.get("/session/{session_id}/storage")
async def get_storage(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Get session storage state."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    state = await browser.get_storage_state(session_id)
    return state or {}


@app.post("/session/{session_id}/cookies")
async def set_cookies(
    session_id: str,
    request: CookiesRequest,
    user: dict = Depends(get_current_user),
):
    """Set cookies for the session."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await browser.set_cookies(session_id, request.cookies)
    return {"success": success}


@app.delete("/session/{session_id}/cookies")
async def clear_cookies(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Clear all cookies."""
    browser = get_browser_manager()

    session = browser.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await browser.clear_cookies(session_id)
    return {"success": success}


# Convenience endpoints
@app.post("/scrape")
async def scrape_url(
    url: str,
    include_html: bool = False,
    screenshot: bool = False,
    user: dict = Depends(get_current_user),
):
    """
    Convenience endpoint to scrape a URL.
    Creates a temporary session, fetches content, and returns it.
    """
    browser = get_browser_manager()

    # Create temporary session
    session_id = await browser.create_session(user["user_id"])
    try:
        # Create page and navigate
        page_id = await browser.new_page(session_id, url)

        # Get content
        content = await browser.get_content(session_id, page_id, include_html)

        result = {
            "url": url,
            "title": content.title if content else "",
            "text": content.text if content else "",
            "markdown": content.markdown if content else "",
            "links": content.links if content else [],
            "metadata": content.metadata if content else {},
        }

        # Take screenshot if requested
        if screenshot:
            ss = await browser.screenshot(
                session_id, page_id, return_base64=True, save_to_file=False
            )
            if ss:
                result["screenshot"] = ss.base64_data

        return result

    finally:
        # Clean up
        await browser.close_session(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
