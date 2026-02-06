"""Age adaptation module for personalized content and detection thresholds."""

from .age_groups import (
    AgeGroup,
    get_age_group,
    get_age_config,
    get_pitch_threshold_for_age,
    calculate_age_months,
)
from .content_filter import ContentFilter

__all__ = [
    "AgeGroup",
    "get_age_group",
    "get_age_config",
    "get_pitch_threshold_for_age",
    "calculate_age_months",
    "ContentFilter",
]
