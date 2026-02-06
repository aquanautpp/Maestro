"""Content filtering based on child's age.

Filters educational content (activities, milestones, tips) to show
only age-appropriate content to parents.
"""

import json
from pathlib import Path
from typing import Any, Optional

from .age_groups import AgeGroup, get_age_group, get_age_config, AGE_GROUPS


class ContentFilter:
    """
    Filters Harvard CDC content based on child's age.

    Ensures parents see relevant activities, milestones, and tips
    for their child's developmental stage.
    """

    def __init__(self, content_path: Optional[Path] = None):
        """
        Initialize content filter.

        Args:
            content_path: Path to harvard_cdc.json. If None, uses default location.
        """
        if content_path is None:
            content_path = Path(__file__).parent.parent.parent / "content" / "harvard_cdc.json"

        self.content_path = content_path
        self._content: Optional[dict] = None

    @property
    def content(self) -> dict:
        """Lazy-load content from JSON file."""
        if self._content is None:
            self._content = self._load_content()
        return self._content

    def _load_content(self) -> dict:
        """Load content from JSON file."""
        if not self.content_path.exists():
            return {}

        try:
            with open(self.content_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _age_range_matches(self, age_string: str, age_months: int) -> bool:
        """
        Check if an age range string includes the given age.

        Handles formats like:
        - "0-1" (years)
        - "1-3" (years)
        - "0-6" (years, full range)
        - "2-6" (years)

        Args:
            age_string: Age range string (e.g., "1-3")
            age_months: Child's age in months

        Returns:
            True if age is within range
        """
        try:
            parts = age_string.split("-")
            if len(parts) != 2:
                return True  # No range specified, include by default

            min_years = int(parts[0])
            max_years = int(parts[1])

            age_years = age_months / 12

            return min_years <= age_years < max_years + 1

        except (ValueError, IndexError):
            return True  # If parsing fails, include by default

    def filter_activities_by_area(
        self,
        area: str,
        age_months: Optional[int] = None
    ) -> list[dict]:
        """
        Get activities for a specific developmental area, optionally filtered by age.

        Args:
            area: Developmental area (linguagem, cognitivo, socioemocional, motor)
            age_months: Optional child's age in months for filtering

        Returns:
            List of activity dictionaries
        """
        activities_by_area = self.content.get("activities_by_area", {})
        area_data = activities_by_area.get(area, {})
        activities = area_data.get("activities", [])

        if age_months is None:
            return activities

        return [
            activity for activity in activities
            if self._age_range_matches(activity.get("ages", "0-6"), age_months)
        ]

    def filter_all_activities(self, age_months: int) -> dict[str, list[dict]]:
        """
        Get all activities filtered by age, organized by area.

        Args:
            age_months: Child's age in months

        Returns:
            Dictionary of area -> filtered activities
        """
        result = {}
        for area in ["linguagem", "cognitivo", "socioemocional", "motor"]:
            filtered = self.filter_activities_by_area(area, age_months)
            if filtered:
                result[area] = filtered
        return result

    def get_milestone_for_age(self, age_months: int) -> Optional[dict]:
        """
        Get developmental milestones for the child's age.

        Args:
            age_months: Child's age in months

        Returns:
            Milestone dictionary or None
        """
        milestones = self.content.get("developmental_milestones", {})
        age_group = get_age_group(age_months)
        config = get_age_config(age_group)

        # Get milestones for the relevant keys
        for key in config.milestone_keys:
            if key in milestones:
                return {
                    "key": key,
                    "age_group": age_group,
                    **milestones[key]
                }

        return None

    def get_serve_return_steps_for_age(self, age_months: int) -> list[dict]:
        """
        Get serve-and-return steps with age-appropriate examples.

        Args:
            age_months: Child's age in months

        Returns:
            List of serve-and-return steps with age-specific content
        """
        serve_return = self.content.get("serve_and_return", {})
        steps = serve_return.get("steps", [])
        age_group = get_age_group(age_months)
        config = get_age_config(age_group)

        result = []
        for step in steps:
            step_data = {
                "step": step.get("step"),
                "name": step.get("name"),
                "description": step.get("description"),
                "examples": step.get("examples", []),
                "emphasized": step.get("step") in config.serve_return_emphasis,
            }

            # Add age-specific guidance if available
            ages_data = step.get("ages", {})

            # Find the best matching age key
            age_key = self._find_best_age_key(ages_data, age_months)
            if age_key:
                step_data["age_specific_tip"] = ages_data[age_key]

            result.append(step_data)

        return result

    def _find_best_age_key(self, ages_data: dict, age_months: int) -> Optional[str]:
        """
        Find the best matching age key from ages data.

        Args:
            ages_data: Dictionary with age range keys
            age_months: Child's age in months

        Returns:
            Best matching key or None
        """
        for age_key in ages_data.keys():
            if self._age_range_matches(age_key, age_months):
                return age_key
        return None

    def get_emphasized_activities(self, age_months: int, limit: int = 3) -> list[dict]:
        """
        Get recommended activities based on age-emphasized developmental areas.

        Args:
            age_months: Child's age in months
            limit: Maximum number of activities to return

        Returns:
            List of recommended activities
        """
        age_group = get_age_group(age_months)
        config = get_age_config(age_group)

        activities = []
        for area in config.activity_focus:
            area_activities = self.filter_activities_by_area(area, age_months)
            for activity in area_activities:
                activity_with_area = {
                    "area": area,
                    **activity
                }
                activities.append(activity_with_area)
                if len(activities) >= limit:
                    return activities

        return activities

    def get_executive_function_activities(self, age_months: int) -> list[str]:
        """
        Get executive function activities for the child's age.

        Args:
            age_months: Child's age in months

        Returns:
            List of activity descriptions
        """
        ef_data = self.content.get("executive_function", {})
        activities_by_age = ef_data.get("activities_by_age", {})

        # Find matching age range
        for age_key, activities in activities_by_age.items():
            if self._age_range_matches(age_key, age_months):
                return activities

        return []

    def get_content_summary_for_age(self, age_months: int) -> dict:
        """
        Get a complete content summary filtered for the child's age.

        Args:
            age_months: Child's age in months

        Returns:
            Dictionary with all age-appropriate content
        """
        age_group = get_age_group(age_months)
        config = get_age_config(age_group)

        return {
            "age_group": age_group,
            "age_months": age_months,
            "config": {
                "pitch_threshold_hz": config.pitch_threshold_hz,
                "response_window_s": config.response_window_s,
                "activity_focus": config.activity_focus,
            },
            "milestone": self.get_milestone_for_age(age_months),
            "serve_return_steps": self.get_serve_return_steps_for_age(age_months),
            "recommended_activities": self.get_emphasized_activities(age_months),
            "executive_function_activities": self.get_executive_function_activities(age_months),
        }
