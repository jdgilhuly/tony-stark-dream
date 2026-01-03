"""Advanced briefing generation with multi-source aggregation and personalization."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Any
import json

import httpx
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


@dataclass
class BriefingContext:
    """Context data for generating a briefing."""
    user_id: str
    preferred_title: str
    timezone: str
    location: Optional[str] = None
    weather_units: str = "imperial"
    news_categories: list[str] = None

    def __post_init__(self):
        if self.news_categories is None:
            self.news_categories = ["technology", "business"]


@dataclass
class AggregatedData:
    """Aggregated data from all services."""
    weather: Optional[dict] = None
    news: list[dict] = None
    calendar: list[dict] = None
    tasks: list[dict] = None
    user_profile: Optional[dict] = None

    def __post_init__(self):
        if self.news is None:
            self.news = []
        if self.calendar is None:
            self.calendar = []
        if self.tasks is None:
            self.tasks = []


class ServiceAggregator:
    """Aggregates data from multiple services concurrently."""

    def __init__(
        self,
        weather_url: str,
        news_url: str,
        calendar_url: str,
        task_url: str,
        profile_url: str,
        timeout: float = 10.0
    ):
        self.weather_url = weather_url
        self.news_url = news_url
        self.calendar_url = calendar_url
        self.task_url = task_url
        self.profile_url = profile_url
        self.timeout = timeout

    async def _fetch(self, url: str, params: dict, token: str) -> Optional[dict]:
        """Fetch data from a service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        return None

    async def aggregate(
        self,
        context: BriefingContext,
        token: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> AggregatedData:
        """Aggregate data from all services concurrently."""

        # Prepare fetch tasks
        tasks = []

        # Weather
        if lat and lon:
            tasks.append(self._fetch(
                f"{self.weather_url}/weather",
                {"lat": lat, "lon": lon, "units": context.weather_units},
                token
            ))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        # News
        tasks.append(self._fetch(
            f"{self.news_url}/personalized",
            {"categories": ",".join(context.news_categories), "page_size": 5},
            token
        ))

        # Calendar - today's events
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        tasks.append(self._fetch(
            f"{self.calendar_url}/events",
            {"start": today.isoformat(), "end": tomorrow.isoformat()},
            token
        ))

        # Tasks - pending
        tasks.append(self._fetch(
            f"{self.task_url}/tasks",
            {"status": "pending"},
            token
        ))

        # User profile
        tasks.append(self._fetch(
            f"{self.profile_url}/users/me",
            {},
            token
        ))

        # Execute all fetches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        weather = results[0] if not isinstance(results[0], Exception) else None
        news_resp = results[1] if not isinstance(results[1], Exception) else None
        calendar_resp = results[2] if not isinstance(results[2], Exception) else None
        tasks_resp = results[3] if not isinstance(results[3], Exception) else None
        profile = results[4] if not isinstance(results[4], Exception) else None

        return AggregatedData(
            weather=weather,
            news=news_resp.get("articles", []) if news_resp else [],
            calendar=calendar_resp.get("events", []) if calendar_resp else [],
            tasks=tasks_resp if isinstance(tasks_resp, list) else (tasks_resp.get("tasks", []) if tasks_resp else []),
            user_profile=profile
        )


class BriefingGenerator:
    """Generates personalized daily briefings using LLM."""

    def __init__(
        self,
        aws_region: str,
        model_id: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        self.model_id = model_id
        config = Config(
            region_name=aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )
        self.client = boto3.client(
            "bedrock-runtime",
            config=config,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    def _determine_greeting_time(self, hour: int) -> str:
        """Get appropriate greeting based on time of day."""
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"

    def _build_context_summary(self, data: AggregatedData) -> str:
        """Build a text summary of the aggregated data for the LLM."""
        parts = []

        if data.weather:
            current = data.weather.get("current", {})
            forecast = data.weather.get("daily_forecast", [{}])[0] if data.weather.get("daily_forecast") else {}
            parts.append(f"""Weather:
- Current: {current.get('temperature', 'N/A')}°, {current.get('condition', 'Unknown')}
- High: {forecast.get('temp_max', 'N/A')}°, Low: {forecast.get('temp_min', 'N/A')}°
- Humidity: {current.get('humidity', 'N/A')}%, Wind: {current.get('wind_speed', 'N/A')} mph""")

        if data.calendar:
            events = data.calendar[:5]
            event_lines = []
            for e in events:
                time_str = e.get('start_time', 'TBD')
                if isinstance(time_str, str) and 'T' in time_str:
                    try:
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        time_str = dt.strftime('%I:%M %p')
                    except:
                        pass
                event_lines.append(f"- {time_str}: {e.get('title', 'Untitled')}")
            if event_lines:
                parts.append(f"Today's Calendar:\n" + "\n".join(event_lines))

        if data.tasks:
            # Prioritize by priority level
            high_priority = [t for t in data.tasks if t.get('priority') == 'high'][:3]
            other_tasks = [t for t in data.tasks if t.get('priority') != 'high'][:2]

            task_lines = []
            for t in high_priority:
                task_lines.append(f"- [HIGH] {t.get('title', 'Untitled')}")
            for t in other_tasks:
                task_lines.append(f"- {t.get('title', 'Untitled')}")

            if task_lines:
                parts.append(f"Pending Tasks ({len(data.tasks)} total):\n" + "\n".join(task_lines))

        if data.news:
            headlines = data.news[:5]
            news_lines = [f"- {h.get('title', 'No title')} ({h.get('source', {}).get('name', 'Unknown')})"
                          for h in headlines]
            parts.append(f"Top Headlines:\n" + "\n".join(news_lines))

        return "\n\n".join(parts) if parts else "No data available for today's briefing."

    async def generate(
        self,
        context: BriefingContext,
        data: AggregatedData,
        current_time: Optional[datetime] = None
    ) -> tuple[str, str]:
        """
        Generate a personalized briefing.

        Returns:
            Tuple of (greeting, summary)
        """
        if current_time is None:
            current_time = datetime.now()

        greeting_time = self._determine_greeting_time(current_time.hour)
        data_summary = self._build_context_summary(data)

        prompt = f"""You are JARVIS, the sophisticated AI assistant from Iron Man. You have a refined British butler demeanor - professional, intelligent, and helpful with occasional subtle dry wit.

You're delivering the daily briefing to your user, whom you address as "{context.preferred_title}".

Current time: {current_time.strftime("%A, %B %d, %Y at %I:%M %p")}
Timezone: {context.timezone}

Today's information:
{data_summary}

Generate a personalized daily briefing that:
1. Begins with an appropriate greeting for the time of day
2. Provides a weather overview with any notable conditions to prepare for
3. Highlights important calendar events, especially those requiring preparation
4. Mentions high-priority tasks tactfully
5. Summarizes one or two interesting news items if relevant to the user
6. Ends with a helpful closing remark

Keep the briefing concise (3-4 short paragraphs) but informative. Use your characteristic JARVIS personality - professional yet personable, with understated wit when appropriate. Never be obsequious.

Remember phrases like "I'm afraid...", "Might I suggest...", "It appears that...", and "At your service, {context.preferred_title}."
"""

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [])
            summary = content[0].get("text", "") if content else ""

            greeting = f"{greeting_time}, {context.preferred_title}."
            return greeting, summary

        except Exception as e:
            logger.error(f"Bedrock generation error: {e}")
            # Fallback to simple briefing
            greeting = f"{greeting_time}, {context.preferred_title}."
            summary = self._generate_fallback_summary(data, context.preferred_title)
            return greeting, summary

    def _generate_fallback_summary(self, data: AggregatedData, title: str) -> str:
        """Generate a simple fallback summary when LLM is unavailable."""
        parts = [f"I have your briefing ready, {title}."]

        if data.weather:
            current = data.weather.get("current", {})
            parts.append(f"The current temperature is {current.get('temperature', 'N/A')}° with {current.get('condition', 'unknown conditions')}.")

        if data.calendar:
            count = len(data.calendar)
            parts.append(f"You have {count} event{'s' if count != 1 else ''} scheduled for today.")

        if data.tasks:
            high = len([t for t in data.tasks if t.get('priority') == 'high'])
            if high:
                parts.append(f"There {'are' if high != 1 else 'is'} {high} high-priority task{'s' if high != 1 else ''} requiring your attention.")

        return " ".join(parts)


class BriefingScheduler:
    """Schedules and manages recurring briefing generation."""

    def __init__(
        self,
        aggregator: ServiceAggregator,
        generator: BriefingGenerator
    ):
        self.aggregator = aggregator
        self.generator = generator
        self._scheduled_users: dict[str, dict] = {}

    def schedule_user_briefing(
        self,
        user_id: str,
        briefing_time: str,  # HH:MM format
        context: BriefingContext
    ):
        """Schedule daily briefing for a user."""
        self._scheduled_users[user_id] = {
            "time": briefing_time,
            "context": context
        }
        logger.info(f"Scheduled briefing for user {user_id} at {briefing_time}")

    def cancel_user_briefing(self, user_id: str):
        """Cancel scheduled briefing for a user."""
        if user_id in self._scheduled_users:
            del self._scheduled_users[user_id]
            logger.info(f"Cancelled briefing for user {user_id}")

    async def generate_for_user(
        self,
        context: BriefingContext,
        token: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> tuple[str, str, AggregatedData]:
        """Generate a complete briefing for a user."""
        # Aggregate data
        data = await self.aggregator.aggregate(context, token, lat, lon)

        # Generate briefing
        greeting, summary = await self.generator.generate(context, data)

        return greeting, summary, data
