"""
Calendar Plugin (Example)
==========================
Demonstrates the plugin pattern.
Future implementation: integrate with Google Calendar / Outlook / iCal.
"""

from __future__ import annotations

from jarvis.plugins.base import JarvisPlugin, PluginContext, PluginMetadata


class CalendarPlugin(JarvisPlugin):
    """
    Calendar integration plugin.

    Tools exposed:
    - list_events(date: str) -> str
    - create_event(title: str, date: str, time: str, duration_mins: int) -> str
    - find_free_time(date: str, duration_mins: int) -> str
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="calendar",
            version="0.1.0",
            description="Calendar integration — list events, create meetings, find free time",
            author="JARVIS OS",
            required_permissions=["low"],
            tags=["calendar", "scheduling", "productivity"],
        )

    async def start(self, context: PluginContext) -> None:
        context.tool_executor.register(
            name="list_events",
            description="List calendar events for a given date",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format, or 'today'/'tomorrow'",
                }
            },
            required=["date"],
            risk_level="low",
        )(self.list_events)

        context.tool_executor.register(
            name="create_calendar_event",
            description="Create a new calendar event",
            parameters={
                "title": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "HH:MM (24h)"},
                "duration_mins": {"type": "integer", "description": "Duration in minutes"},
            },
            required=["title", "date", "time"],
            requires_confirmation=True,
            risk_level="medium",
        )(self.create_event)

    async def list_events(self, date: str) -> str:
        """List events for a date. Placeholder — wire to real calendar API."""
        return (
            f"Calendar integration not yet connected. "
            f"Future: will list events for {date}. "
            "Connect Google Calendar in Settings > Plugins > Calendar."
        )

    async def create_event(
        self,
        title: str,
        date: str,
        time: str,
        duration_mins: int = 60,
    ) -> str:
        """Create calendar event. Placeholder."""
        return (
            f"Would create: '{title}' on {date} at {time} "
            f"({duration_mins} min). "
            "Calendar not yet connected."
        )

    async def stop(self) -> None:
        pass
