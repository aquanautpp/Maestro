"""Age group definitions and configuration for age-adaptive guidance.

Children's vocal characteristics change significantly with age:
- Infants (0-1): Higher pitch, less distinct speech patterns
- Toddlers (1-3): High pitch, developing speech
- Preschoolers (3-6): Pitch gradually lowers, clearer speech

This module provides age-specific configurations for:
- Pitch detection thresholds
- Response window timing
- Content filtering
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Literal

# Age group type
AgeGroup = Literal["0-1", "1-2", "2-3", "3-4", "4-5", "5-6"]

# All valid age groups in order
AGE_GROUPS: list[AgeGroup] = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6"]


@dataclass
class AgeConfig:
    """Configuration for a specific age group."""
    age_group: AgeGroup
    pitch_threshold_hz: int
    response_window_s: float
    min_speech_duration_ms: int
    milestone_keys: list[str]
    activity_focus: list[str]
    serve_return_emphasis: list[int]  # Steps 1-5 to emphasize


# Default configurations per age group
# Based on developmental research:
# - Younger children have higher pitched voices
# - Younger children need more response time
# - Different serve-and-return steps are more relevant at different ages
DEFAULT_AGE_CONFIGS: dict[AgeGroup, AgeConfig] = {
    "0-1": AgeConfig(
        age_group="0-1",
        pitch_threshold_hz=320,  # Infants have very high pitch
        response_window_s=20.0,  # Very generous for pre-verbal responses
        min_speech_duration_ms=300,  # Shorter vocalizations count
        milestone_keys=["0-6_months", "6-12_months"],
        activity_focus=["socioemocional", "motor"],
        serve_return_emphasis=[1, 2],  # Share focus, Support
    ),
    "1-2": AgeConfig(
        age_group="1-2",
        pitch_threshold_hz=300,
        response_window_s=18.0,
        min_speech_duration_ms=400,
        milestone_keys=["12-24_months"],
        activity_focus=["linguagem", "cognitivo"],
        serve_return_emphasis=[1, 2, 3],  # Share focus, Support, Name
    ),
    "2-3": AgeConfig(
        age_group="2-3",
        pitch_threshold_hz=285,
        response_window_s=15.0,
        min_speech_duration_ms=500,
        milestone_keys=["24-36_months"],
        activity_focus=["linguagem", "cognitivo", "socioemocional"],
        serve_return_emphasis=[3, 4],  # Name, Wait
    ),
    "3-4": AgeConfig(
        age_group="3-4",
        pitch_threshold_hz=270,
        response_window_s=12.0,
        min_speech_duration_ms=500,
        milestone_keys=["3-4_years"],
        activity_focus=["linguagem", "cognitivo", "socioemocional"],
        serve_return_emphasis=[3, 4, 5],  # Name, Wait, Transitions
    ),
    "4-5": AgeConfig(
        age_group="4-5",
        pitch_threshold_hz=260,
        response_window_s=10.0,
        min_speech_duration_ms=500,
        milestone_keys=["4-6_years"],
        activity_focus=["linguagem", "cognitivo"],
        serve_return_emphasis=[4, 5],  # Wait, Transitions
    ),
    "5-6": AgeConfig(
        age_group="5-6",
        pitch_threshold_hz=250,  # Approaching adult child threshold
        response_window_s=10.0,
        min_speech_duration_ms=500,
        milestone_keys=["4-6_years"],
        activity_focus=["linguagem", "cognitivo"],
        serve_return_emphasis=[4, 5],  # Wait, Transitions
    ),
}


def calculate_age_months(birth_date: date | str) -> int:
    """
    Calculate age in months from birth date.

    Args:
        birth_date: Child's birth date (date object or ISO string)

    Returns:
        Age in months (0-72 for 0-6 years)
    """
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date.replace("Z", "")).date()

    today = date.today()
    months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)

    # Adjust if birthday hasn't occurred this month
    if today.day < birth_date.day:
        months -= 1

    return max(0, months)


def get_age_group(age_months: int) -> AgeGroup:
    """
    Determine age group from age in months.

    Args:
        age_months: Child's age in months

    Returns:
        Age group string (e.g., "2-3" for 24-35 months)
    """
    if age_months < 12:
        return "0-1"
    elif age_months < 24:
        return "1-2"
    elif age_months < 36:
        return "2-3"
    elif age_months < 48:
        return "3-4"
    elif age_months < 60:
        return "4-5"
    else:
        return "5-6"


def get_age_group_from_birth_date(birth_date: date | str) -> AgeGroup:
    """
    Determine age group from birth date.

    Args:
        birth_date: Child's birth date

    Returns:
        Age group string
    """
    age_months = calculate_age_months(birth_date)
    return get_age_group(age_months)


def get_age_config(age_group: AgeGroup) -> AgeConfig:
    """
    Get configuration for an age group.

    Args:
        age_group: Age group string (e.g., "2-3")

    Returns:
        AgeConfig with all settings for that age
    """
    return DEFAULT_AGE_CONFIGS.get(age_group, DEFAULT_AGE_CONFIGS["2-3"])


def get_age_config_for_months(age_months: int) -> AgeConfig:
    """
    Get configuration based on age in months.

    Args:
        age_months: Child's age in months

    Returns:
        AgeConfig for the appropriate age group
    """
    age_group = get_age_group(age_months)
    return get_age_config(age_group)


def get_pitch_threshold_for_age(age_months: int) -> int:
    """
    Get pitch threshold (Hz) for child classification based on age.

    Younger children have higher pitched voices, so we use higher
    thresholds to correctly classify their speech.

    Args:
        age_months: Child's age in months

    Returns:
        Pitch threshold in Hz
    """
    config = get_age_config_for_months(age_months)
    return config.pitch_threshold_hz


def get_response_window_for_age(age_months: int) -> float:
    """
    Get response window (seconds) based on age.

    Younger children need more time for pre-verbal responses
    (gestures, looks, sounds) that may not be detected by audio.

    Args:
        age_months: Child's age in months

    Returns:
        Response window in seconds
    """
    config = get_age_config_for_months(age_months)
    return config.response_window_s


def load_age_configs_from_file() -> dict[AgeGroup, AgeConfig]:
    """
    Load age configurations from JSON file if it exists.
    Falls back to defaults if file not found.

    Returns:
        Dictionary of age group to AgeConfig
    """
    config_path = Path(__file__).parent.parent.parent / "content" / "age_configs.json"

    if not config_path.exists():
        return DEFAULT_AGE_CONFIGS

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        configs = {}
        for age_group, config_data in data.items():
            if age_group in AGE_GROUPS:
                configs[age_group] = AgeConfig(
                    age_group=age_group,
                    pitch_threshold_hz=config_data.get("pitch_threshold_hz", 280),
                    response_window_s=config_data.get("response_window_s", 15.0),
                    min_speech_duration_ms=config_data.get("min_speech_duration_ms", 500),
                    milestone_keys=config_data.get("milestone_keys", []),
                    activity_focus=config_data.get("activity_focus", []),
                    serve_return_emphasis=config_data.get("serve_return_emphasis", [1, 2, 3, 4, 5]),
                )

        # Fill in any missing age groups with defaults
        for age_group in AGE_GROUPS:
            if age_group not in configs:
                configs[age_group] = DEFAULT_AGE_CONFIGS[age_group]

        return configs

    except Exception:
        return DEFAULT_AGE_CONFIGS
