"""Service-to-service integration module for JARVIS Conversation Service."""

import logging
import httpx
from typing import Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from functools import lru_cache

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceIntegration:
    """Base class for service integrations with retry and error handling."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        **kwargs
    ) -> dict:
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from {self.base_url}{path}: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error to {self.base_url}{path}: {e}")
                raise


class WeatherIntegration(ServiceIntegration):
    """Integration with Weather Service."""

    def __init__(self):
        super().__init__(settings.weather_service_url)

    async def get_current_weather(
        self,
        location: Optional[str] = None,
        token: Optional[str] = None
    ) -> dict:
        """Get current weather for a location."""
        params = {}
        if location:
            params["location"] = location

        return await self._request("GET", "/weather/current", token=token, params=params)

    async def get_forecast(
        self,
        location: Optional[str] = None,
        days: int = 5,
        token: Optional[str] = None
    ) -> dict:
        """Get weather forecast."""
        params = {"days": days}
        if location:
            params["location"] = location

        return await self._request("GET", "/weather/forecast", token=token, params=params)


class NewsIntegration(ServiceIntegration):
    """Integration with News Service."""

    def __init__(self):
        super().__init__(settings.news_service_url)

    async def get_headlines(
        self,
        category: Optional[str] = None,
        count: int = 5,
        token: Optional[str] = None
    ) -> dict:
        """Get top news headlines."""
        params = {"count": count}
        if category:
            params["category"] = category

        return await self._request("GET", "/news/headlines", token=token, params=params)

    async def search_news(
        self,
        query: str,
        count: int = 5,
        token: Optional[str] = None
    ) -> dict:
        """Search for news articles."""
        return await self._request(
            "GET",
            "/news/search",
            token=token,
            params={"q": query, "count": count}
        )


class CalendarIntegration(ServiceIntegration):
    """Integration with Calendar Service."""

    def __init__(self):
        super().__init__(settings.calendar_service_url)

    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        token: Optional[str] = None
    ) -> dict:
        """Get calendar events."""
        params = {}
        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()

        return await self._request("GET", "/events", token=token, params=params)

    async def get_todays_events(self, token: Optional[str] = None) -> dict:
        """Get today's calendar events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return await self.get_events(today, tomorrow, token)


class TaskIntegration(ServiceIntegration):
    """Integration with Task Execution Service."""

    def __init__(self):
        super().__init__(settings.task_execution_url)

    async def get_pending_tasks(self, token: Optional[str] = None) -> dict:
        """Get pending tasks."""
        return await self._request(
            "GET",
            "/tasks",
            token=token,
            params={"status": "pending"}
        )

    async def create_task(
        self,
        title: str,
        task_type: str = "custom",
        payload: Optional[dict] = None,
        token: Optional[str] = None
    ) -> dict:
        """Create a new task."""
        return await self._request(
            "POST",
            "/tasks",
            token=token,
            json={
                "title": title,
                "type": task_type,
                "payload": payload or {}
            }
        )

    async def create_reminder(
        self,
        message: str,
        due_date: Optional[datetime] = None,
        token: Optional[str] = None
    ) -> dict:
        """Create a reminder task."""
        data = {
            "title": message,
            "type": "reminder",
        }
        if due_date:
            data["due_date"] = due_date.isoformat()

        return await self._request("POST", "/tasks", token=token, json=data)


class BriefingIntegration(ServiceIntegration):
    """Integration with Briefing Service."""

    def __init__(self):
        super().__init__(settings.briefing_service_url)

    async def get_daily_briefing(self, token: Optional[str] = None) -> dict:
        """Get the daily briefing."""
        return await self._request("GET", "/briefing/daily", token=token)

    async def generate_briefing(self, token: Optional[str] = None) -> dict:
        """Generate a new briefing."""
        return await self._request("POST", "/briefing/generate", token=token)


class IntegrationManager:
    """Manager class for all service integrations."""

    def __init__(self):
        self.weather = WeatherIntegration()
        self.news = NewsIntegration()
        self.calendar = CalendarIntegration()
        self.tasks = TaskIntegration()
        self.briefing = BriefingIntegration()

    async def get_context_data(self, token: Optional[str] = None) -> dict:
        """Get context data from all services for conversation enrichment."""
        context = {}

        try:
            weather = await self.weather.get_current_weather(token=token)
            context["weather"] = {
                "temperature": weather.get("temperature"),
                "condition": weather.get("condition"),
                "location": weather.get("location"),
            }
        except Exception as e:
            logger.warning(f"Failed to get weather context: {e}")
            context["weather"] = None

        try:
            events = await self.calendar.get_todays_events(token=token)
            context["calendar"] = {
                "event_count": len(events.get("events", [])),
                "next_event": events.get("events", [{}])[0] if events.get("events") else None,
            }
        except Exception as e:
            logger.warning(f"Failed to get calendar context: {e}")
            context["calendar"] = None

        try:
            tasks = await self.tasks.get_pending_tasks(token=token)
            task_list = tasks if isinstance(tasks, list) else tasks.get("tasks", [])
            context["tasks"] = {
                "pending_count": len(task_list),
                "high_priority": len([t for t in task_list if t.get("priority") == "high"]),
            }
        except Exception as e:
            logger.warning(f"Failed to get tasks context: {e}")
            context["tasks"] = None

        return context

    async def handle_intent(
        self,
        intent: str,
        entities: dict,
        token: Optional[str] = None
    ) -> Optional[dict]:
        """Handle specific intents by calling appropriate services."""

        handlers = {
            "get_weather": self._handle_weather,
            "get_news": self._handle_news,
            "get_calendar": self._handle_calendar,
            "create_reminder": self._handle_reminder,
            "get_briefing": self._handle_briefing,
        }

        handler = handlers.get(intent)
        if handler:
            return await handler(entities, token)

        return None

    async def _handle_weather(self, entities: dict, token: Optional[str]) -> dict:
        location = entities.get("location")
        if entities.get("forecast"):
            return await self.weather.get_forecast(location=location, token=token)
        return await self.weather.get_current_weather(location=location, token=token)

    async def _handle_news(self, entities: dict, token: Optional[str]) -> dict:
        if entities.get("query"):
            return await self.news.search_news(entities["query"], token=token)
        return await self.news.get_headlines(
            category=entities.get("category"),
            token=token
        )

    async def _handle_calendar(self, entities: dict, token: Optional[str]) -> dict:
        return await self.calendar.get_todays_events(token=token)

    async def _handle_reminder(self, entities: dict, token: Optional[str]) -> dict:
        return await self.tasks.create_reminder(
            message=entities.get("message", "Reminder"),
            due_date=entities.get("due_date"),
            token=token
        )

    async def _handle_briefing(self, entities: dict, token: Optional[str]) -> dict:
        return await self.briefing.get_daily_briefing(token=token)


# Singleton instance
_integration_manager: Optional[IntegrationManager] = None


def get_integration_manager() -> IntegrationManager:
    """Get the singleton integration manager instance."""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = IntegrationManager()
    return _integration_manager
