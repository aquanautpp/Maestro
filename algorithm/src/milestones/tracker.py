"""Milestone tracking and progress assessment.

Tracks developmental milestones based on conversation patterns
and provides age-appropriate expectations and activities.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from .conversation_indicators import ConversationIndicators, MilestoneIndicator


class MilestoneTracker:
    """
    Tracks developmental milestones and suggests activities.

    Links conversation patterns to developmental progress and
    recommends age-appropriate activities.
    """

    def __init__(self, content_path: Optional[Path] = None):
        """
        Initialize milestone tracker.

        Args:
            content_path: Path to harvard_cdc.json
        """
        if content_path is None:
            content_path = Path(__file__).parent.parent.parent / "content" / "harvard_cdc.json"

        self.content_path = content_path
        self._content: Optional[Dict] = None
        self.indicators = ConversationIndicators()

    @property
    def content(self) -> Dict:
        """Lazy-load content."""
        if self._content is None:
            self._content = self._load_content()
        return self._content

    def _load_content(self) -> Dict:
        """Load content from JSON."""
        if not self.content_path.exists():
            return {}

        try:
            with open(self.content_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_milestones_for_age(self, age_months: int) -> Dict[str, Any]:
        """
        Get developmental milestones for a child's age.

        Args:
            age_months: Child's age in months

        Returns:
            Milestone information with expectations
        """
        milestones = self.content.get("developmental_milestones", {})

        # Find matching age range
        age_key = self._get_age_key(age_months)

        milestone_data = milestones.get(age_key, {})

        return {
            "age_months": age_months,
            "age_key": age_key,
            "what_to_expect": milestone_data.get("what_to_expect", ""),
            "how_to_interact": milestone_data.get("how_to_interact", ""),
            "conversation_indicators": [
                i for i in self.indicators.get_indicators_for_age(age_months)
            ],
        }

    def _get_age_key(self, age_months: int) -> str:
        """Convert age in months to milestone key."""
        if age_months < 6:
            return "0-6_months"
        elif age_months < 12:
            return "6-12_months"
        elif age_months < 24:
            return "12-24_months"
        elif age_months < 36:
            return "24-36_months"
        elif age_months < 48:
            return "3-4_years"
        else:
            return "4-6_years"

    def assess_progress(
        self,
        sessions: List[Dict],
        age_months: int
    ) -> Dict[str, Any]:
        """
        Assess developmental progress based on sessions.

        Args:
            sessions: List of session dictionaries
            age_months: Child's age

        Returns:
            Progress assessment
        """
        if not sessions:
            return {
                "status": "no_data",
                "message": "Continue interagindo para ver o progresso!",
            }

        # Evaluate each session
        all_indicators = []
        for session in sessions[-10:]:  # Use last 10 sessions
            session_indicators = self.indicators.evaluate_session(session, age_months)
            all_indicators.extend(session_indicators)

        # Aggregate results
        achieved = [i for i in all_indicators if i.achieved]
        unique_achieved = list({i.milestone_id: i for i in achieved}.values())

        # Get celebration messages
        celebrations = []
        for indicator in unique_achieved[:3]:
            message = self.indicators.get_celebration_message(indicator)
            if message:
                celebrations.append({
                    "milestone": indicator.milestone_name,
                    "indicator": indicator.indicator_name,
                    "message": message,
                })

        return {
            "status": "success",
            "sessions_analyzed": len(sessions),
            "indicators_achieved": len(unique_achieved),
            "achievements": [i.to_dict() for i in unique_achieved],
            "celebrations": celebrations,
            "milestones": self.get_milestones_for_age(age_months),
        }

    def get_suggested_activities(
        self,
        age_months: int,
        focus_area: Optional[str] = None
    ) -> List[Dict]:
        """
        Get suggested activities based on age and milestones.

        Args:
            age_months: Child's age
            focus_area: Optional area to focus on

        Returns:
            List of suggested activities
        """
        activities = []

        # Get activities from content
        activities_by_area = self.content.get("activities_by_area", {})
        ef_activities = self.content.get("executive_function", {}).get("activities_by_age", {})

        # Filter by age
        for area, area_data in activities_by_area.items():
            if focus_area and area != focus_area:
                continue

            for activity in area_data.get("activities", []):
                if self._activity_matches_age(activity.get("ages", "0-6"), age_months):
                    activities.append({
                        "area": area,
                        "title": activity.get("title"),
                        "description": activity.get("description"),
                        "why": activity.get("why"),
                    })

        # Add executive function activities
        ef_key = self._get_ef_age_key(age_months)
        ef_list = ef_activities.get(ef_key, [])
        for activity in ef_list[:2]:
            activities.append({
                "area": "executive_function",
                "title": activity,
                "description": activity,
            })

        return activities[:6]  # Limit to 6 activities

    def _activity_matches_age(self, age_string: str, age_months: int) -> bool:
        """Check if activity age range matches child's age."""
        try:
            parts = age_string.split("-")
            min_years = int(parts[0])
            max_years = int(parts[1])
            age_years = age_months / 12
            return min_years <= age_years <= max_years + 0.5
        except (ValueError, IndexError):
            return True

    def _get_ef_age_key(self, age_months: int) -> str:
        """Get executive function age key."""
        if age_months < 12:
            return "0-1"
        elif age_months < 36:
            return "1-3"
        else:
            return "3-6"

    def get_complete_milestone_view(
        self,
        age_months: int,
        sessions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Get complete milestone view with progress and activities.

        Args:
            age_months: Child's age
            sessions: Optional sessions for progress assessment

        Returns:
            Complete milestone information
        """
        milestones = self.get_milestones_for_age(age_months)
        activities = self.get_suggested_activities(age_months)

        result = {
            "age_months": age_months,
            "milestones": milestones,
            "suggested_activities": activities,
        }

        if sessions:
            result["progress"] = self.assess_progress(sessions, age_months)

        return result
