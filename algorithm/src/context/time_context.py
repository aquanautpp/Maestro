"""Time and context detection for situational awareness.

Detects time-of-day patterns and suggests appropriate contexts
for interaction (morning routine, mealtime, bedtime, play).
"""

from datetime import datetime, time
from typing import Optional, List, Dict, Any
from enum import Enum


class TimeOfDay(Enum):
    """Time of day categories."""
    EARLY_MORNING = "early_morning"  # 5-7am
    MORNING = "morning"              # 7-11am
    MIDDAY = "midday"                # 11am-1pm
    AFTERNOON = "afternoon"          # 1-5pm
    EVENING = "evening"              # 5-8pm
    NIGHT = "night"                  # 8-10pm
    LATE_NIGHT = "late_night"        # 10pm-5am


class Context(Enum):
    """Interaction context categories."""
    MORNING_ROUTINE = "morning_routine"
    MEALTIME = "mealtime"
    PLAYTIME = "playtime"
    LEARNING = "learning"
    OUTDOOR = "outdoor"
    BEDTIME_ROUTINE = "bedtime_routine"
    GENERAL = "general"


class TimeContext:
    """
    Determines current time context for tip selection.

    Uses time of day and historical patterns to suggest
    the most likely current context.
    """

    def __init__(self):
        """Initialize time context."""
        # Time ranges for contexts (hour ranges)
        self.context_times = {
            Context.MORNING_ROUTINE: [(6, 9)],
            Context.MEALTIME: [(7, 8), (11, 13), (17, 19)],
            Context.BEDTIME_ROUTINE: [(19, 21)],
            Context.LEARNING: [(9, 12), (14, 17)],
            Context.PLAYTIME: [(9, 12), (14, 18)],
            Context.OUTDOOR: [(10, 12), (15, 18)],
        }

    def get_time_of_day(self, dt: Optional[datetime] = None) -> TimeOfDay:
        """
        Get time of day category.

        Args:
            dt: Datetime to check. If None, uses current time.

        Returns:
            TimeOfDay enum value
        """
        if dt is None:
            dt = datetime.now()

        hour = dt.hour

        if 5 <= hour < 7:
            return TimeOfDay.EARLY_MORNING
        elif 7 <= hour < 11:
            return TimeOfDay.MORNING
        elif 11 <= hour < 13:
            return TimeOfDay.MIDDAY
        elif 13 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 20:
            return TimeOfDay.EVENING
        elif 20 <= hour < 22:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.LATE_NIGHT

    def get_likely_contexts(
        self,
        dt: Optional[datetime] = None
    ) -> List[Context]:
        """
        Get likely contexts for the current time.

        Args:
            dt: Datetime to check. If None, uses current time.

        Returns:
            List of likely contexts, most likely first
        """
        if dt is None:
            dt = datetime.now()

        hour = dt.hour
        is_weekend = dt.weekday() >= 5

        likely = []

        for context, time_ranges in self.context_times.items():
            for start_hour, end_hour in time_ranges:
                if start_hour <= hour < end_hour:
                    likely.append(context)
                    break

        # Add general as fallback
        if not likely:
            likely.append(Context.GENERAL)

        # Prioritize weekend contexts
        if is_weekend:
            if Context.PLAYTIME in likely:
                likely.remove(Context.PLAYTIME)
                likely.insert(0, Context.PLAYTIME)
            if Context.OUTDOOR in likely:
                likely.remove(Context.OUTDOOR)
                likely.insert(0, Context.OUTDOOR)

        return likely

    def get_primary_context(
        self,
        dt: Optional[datetime] = None
    ) -> Context:
        """
        Get the most likely current context.

        Args:
            dt: Datetime to check. If None, uses current time.

        Returns:
            Most likely Context
        """
        likely = self.get_likely_contexts(dt)
        return likely[0] if likely else Context.GENERAL

    def get_context_info(
        self,
        dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get complete context information.

        Args:
            dt: Datetime to check. If None, uses current time.

        Returns:
            Dictionary with time and context info
        """
        if dt is None:
            dt = datetime.now()

        time_of_day = self.get_time_of_day(dt)
        likely_contexts = self.get_likely_contexts(dt)
        primary = likely_contexts[0] if likely_contexts else Context.GENERAL

        return {
            "current_time": dt.isoformat(),
            "time_of_day": time_of_day.value,
            "hour": dt.hour,
            "is_weekend": dt.weekday() >= 5,
            "primary_context": primary.value,
            "likely_contexts": [c.value for c in likely_contexts],
        }

    def get_greeting(self, dt: Optional[datetime] = None) -> str:
        """
        Get appropriate greeting for time of day.

        Args:
            dt: Datetime to check

        Returns:
            Greeting string in Portuguese
        """
        time_of_day = self.get_time_of_day(dt)

        greetings = {
            TimeOfDay.EARLY_MORNING: "Bom dia! Acordando cedo?",
            TimeOfDay.MORNING: "Bom dia!",
            TimeOfDay.MIDDAY: "Boa tarde! Hora do almoco?",
            TimeOfDay.AFTERNOON: "Boa tarde!",
            TimeOfDay.EVENING: "Boa noite! Fim de dia junto?",
            TimeOfDay.NIGHT: "Boa noite! Hora de relaxar?",
            TimeOfDay.LATE_NIGHT: "Oi! Tudo bem por ai?",
        }

        return greetings.get(time_of_day, "Ola!")
